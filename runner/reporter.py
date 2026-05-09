from runner.validator import TagResult, tag_name
from typing import List

LINE = "══════════════════════════════════════════"


def print_header():
    print(LINE)
    print(" FIX OMS TEST AUTOMATION - RESULTS")
    print(LINE)


def print_test_result(index, test_name, tag_results, error=""):
    print(f"\n[TEST {index}] {test_name}")

    if error:
        print(f"  ❌ ERROR: {error}")
        print("  RESULT: ERROR")
        return

    for r in tag_results:
        _print_tag_row(r, indent=2)

    print(f"  RESULT: {'PASSED' if all(r.passed for r in tag_results) else 'FAILED'}")


def print_sequence_result(index, test_name, seq_results, error=""):
    print(f"\n[TEST {index}] {test_name}")

    if error:
        print(f"  ❌ ERROR: {error}")
        print("  RESULT: ERROR")
        return

    overall_passed = True
    for label, tag_results in seq_results:
        print(f"  ── {label}")
        for r in tag_results:
            _print_tag_row(r, indent=4)
        if not all(r.passed for r in tag_results):
            overall_passed = False

    print(f"  RESULT: {'PASSED' if overall_passed else 'FAILED'}")


def print_summary(total, passed, failed, errors):
    print(f"\n{LINE}")
    parts = [f"TOTAL: {total} tests", f"PASSED: {passed}", f"FAILED: {failed}"]
    if errors:
        parts.append(f"ERRORS: {errors}")
    print(" | ".join(parts))
    print(LINE)


def _print_tag_row(r, indent):
    pad = " " * indent
    name = tag_name(r.tag)
    suffix = f"    ({name})" if name else ""

    if r.passed:
        print(f'{pad}✅ Tag {r.tag} = "{r.expected}"{suffix}')
    elif r.missing:
        print(f'{pad}❌ Tag {r.tag} expected "{r.expected}" — tag not in response{suffix}')
    else:
        print(f'{pad}❌ Tag {r.tag} expected "{r.expected}" got "{r.actual}"{suffix}')


def format_session_reject(response):
    """Extract human-readable info from a 35=3 session reject."""
    ref_tag  = response.get("371", "?")   # RefTagID - which tag caused the reject
    ref_msg  = response.get("372", "?")   # RefMsgType - which message was rejected
    reason   = response.get("373", "?")   # SessionRejectReason code
    text     = response.get("58",  "")    # Text description

    reason_map = {
        "0": "InvalidTag", "1": "RequiredTagMissing", "2": "TagNotDefinedForMsg",
        "3": "UndefinedTag", "4": "TagWithoutValue", "5": "ValueError",
        "6": "IncorrectDataFormat", "7": "DecryptionProblem", "8": "SignatureProblem",
        "9": "CompIDProblem", "10": "SendingTimeAccuracyProblem", "11": "InvalidMsgType",
    }
    reason_str = reason_map.get(str(reason), reason)

    return (f"SESSION REJECT (35=3): RefTag={ref_tag} | "
            f"RefMsg={ref_msg} | Reason={reason_str} | {text}")
