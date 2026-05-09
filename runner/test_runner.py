import json
import os
import re
import time
import queue
import glob
from typing import Optional, List, Dict

from fix_client.builder import build_message_from_tags
from runner.validator import validate_tags
from runner import reporter


class TestRunner:

    def __init__(self, app, timeout=5.0):
        self._app = app
        self._timeout = timeout
        self._vars: Dict[str, str] = {}

    def load_tests_from_file(self, filepath):
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return [data] if isinstance(data, dict) else data

    def load_tests_from_dir(self, dirpath):
        cases = []
        for filepath in sorted(glob.glob(os.path.join(dirpath, "*.json"))):
            cases.extend(self.load_tests_from_file(filepath))
        return cases

    def run_all(self, test_cases):
        reporter.print_header()
        total, passed, failed, errors = len(test_cases), 0, 0, 0

        for i, case in enumerate(test_cases, start=1):
            name = case.get("name", f"Test {i}")
            send = self._interpolate(case.get("send", {}))
            expect = case.get("expect", {})
            expect_seq = case.get("expect_sequence", [])
            capture = case.get("capture", {})
            delay = float(case.get("delay_after", 0))
            drain = bool(case.get("drain_after", False))

            try:
                msg = build_message_from_tags(send)
                if not self._app.send(msg):
                    reporter.print_test_result(i, name, [], error="Send failed — OMS not connected")
                    errors += 1
                    continue
            except Exception as e:
                reporter.print_test_result(i, name, [], error=f"Build/send error: {e}")
                errors += 1
                continue

            if expect_seq:
                all_passed, seq_results, err = self._run_sequence(expect_seq)
                reporter.print_sequence_result(i, name, seq_results, err)
                if err:
                    errors += 1
                elif all_passed:
                    passed += 1
                else:
                    failed += 1
            else:
                response = self._wait_for_response()
                if response is None:
                    reporter.print_test_result(i, name, [], error=f"No response from OMS within {self._timeout}s")
                    errors += 1
                    if delay > 0:
                        time.sleep(delay)
                    continue

                if "_error" in response:
                    reporter.print_test_result(i, name, [], error=response["_error"])
                    errors += 1
                    continue

                if "_session_reject" in response:
                    reporter.print_test_result(i, name, [], error=reporter.format_session_reject(response))
                    errors += 1
                    continue

                self._capture(capture, response)
                tag_results = validate_tags(expect, response)
                reporter.print_test_result(i, name, tag_results)

                if all(r.passed for r in tag_results):
                    passed += 1
                else:
                    failed += 1

            if drain:
                self._drain()
            if delay > 0:
                time.sleep(delay)

        reporter.print_summary(total, passed, failed, errors)

    def _run_sequence(self, expect_seq):
        seq_results = []
        all_passed = True

        for idx, expected in enumerate(expect_seq, start=1):
            label = expected.pop("_label", f"Response {idx}")
            response = self._wait_for_response()

            if response is None:
                return False, seq_results, f"Response {idx} not received within {self._timeout}s"
            if "_error" in response:
                return False, seq_results, response["_error"]

            if "_session_reject" in response:
                return False, seq_results, reporter.format_session_reject(response)

            tag_results = validate_tags(expected, response)
            seq_results.append((label, tag_results))

            if not all(r.passed for r in tag_results):
                all_passed = False

        return all_passed, seq_results, ""

    def _capture(self, capture, response):
        for var_name, tag_str in capture.items():
            if str(tag_str) in response:
                self._vars[var_name] = response[str(tag_str)]

    def _interpolate(self, send):
        result = {}
        for tag, val in send.items():
            # Preserve the groups dict as-is — builder handles it directly
            if tag == "groups":
                result["groups"] = val
                continue
            val_str = str(val)
            for var in re.findall(r"\{\{(\w+)\}\}", val_str):
                if var in self._vars:
                    val_str = val_str.replace("{{" + var + "}}", self._vars[var])
            result[str(tag)] = val_str
        return result

    def _wait_for_response(self):
        deadline = time.time() + self._timeout
        while time.time() < deadline:
            try:
                return self._app.response_queue.get(timeout=min(deadline - time.time(), 0.5))
            except queue.Empty:
                continue
        return None

    def _drain(self):
        deadline = time.time() + 0.5
        while time.time() < deadline:
            try:
                self._app.response_queue.get(timeout=0.1)
            except queue.Empty:
                break
