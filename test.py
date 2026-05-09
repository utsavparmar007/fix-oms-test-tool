import sys
import os
import time
import argparse
import tempfile

import quickfix as fix

from fix_client.application import FIXTestApplication
from runner.test_runner import TestRunner


def parse_args():
    parser = argparse.ArgumentParser(description="FIX OMS Test Automation Tool")
    parser.add_argument("--config",  default="config/client.cfg")
    parser.add_argument("--tests",   default="tests/")
    parser.add_argument("--timeout", default=5.0, type=float)
    parser.add_argument("--sender",  default=None)
    parser.add_argument("--host",    default=None)
    parser.add_argument("--port",    default=None, type=int)
    return parser.parse_args()


def load_settings(config_path, args):
    if not (args.sender or args.host or args.port):
        return fix.SessionSettings(config_path)

    with open(config_path, "r") as f:
        lines = f.readlines()

    patched = []
    for line in lines:
        s = line.strip()
        if args.sender and s.startswith("SenderCompID"):
            line = f"SenderCompID={args.sender}\n"
        if args.host and s.startswith("SocketConnectHost"):
            line = f"SocketConnectHost={args.host}\n"
        if args.port and s.startswith("SocketConnectPort"):
            line = f"SocketConnectPort={args.port}\n"
        patched.append(line)

    # getSessions() is not iterable in QuickFIX 1.15.x, so we patch the
    # config as plain text and reload from a temp file instead
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False, encoding="utf-8")
    tmp.writelines(patched)
    tmp.flush()
    tmp.close()

    try:
        return fix.SessionSettings(tmp.name)
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def main():
    args = parse_args()

    if not os.path.exists(args.config):
        print(f"\nConfig file not found: '{args.config}'")
        print("Run this script from the fix_test_tool directory.\n")
        sys.exit(1)

    try:
        settings = load_settings(args.config, args)
    except fix.ConfigError as e:
        print(f"\nConfig Error: {e}\n")
        sys.exit(1)

    app = FIXTestApplication()

    try:
        initiator = fix.SocketInitiator(app, fix.FileStoreFactory(settings), settings, fix.FileLogFactory(settings))
        initiator.start()
    except fix.ConfigError as e:
        print(f"\nInitiator Error: {e}\n")
        sys.exit(1)

    print("\nConnecting to OMS", end="", flush=True)
    deadline = time.time() + 10
    while time.time() < deadline:
        if app.is_connected:
            print(" connected\n")
            break
        print(".", end="", flush=True)
        time.sleep(0.5)
    else:
        print(" FAILED")
        print("Could not connect to OMS within 10 seconds.")
        print("Make sure the OMS is running.\n")
        initiator.stop()
        sys.exit(1)

    runner = TestRunner(app, timeout=args.timeout)

    try:
        if os.path.isdir(args.tests):
            test_cases = runner.load_tests_from_dir(args.tests)
        else:
            test_cases = runner.load_tests_from_file(args.tests)
    except Exception as e:
        print(f"\nFailed to load tests: {e}\n")
        initiator.stop()
        sys.exit(1)

    if not test_cases:
        print("\nNo test cases found.\n")
        initiator.stop()
        sys.exit(0)

    try:
        runner.run_all(test_cases)
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
    finally:
        initiator.stop()


if __name__ == "__main__":
    main()
