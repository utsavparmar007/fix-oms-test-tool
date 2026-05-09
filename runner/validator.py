from dataclasses import dataclass
from typing import List


TAG_NAMES = {
    "6":   "AvgPx",
    "8":   "BeginString",
    "9":   "BodyLength",
    "11":  "ClOrdID",
    "14":  "CumQty",
    "17":  "ExecID",
    "20":  "ExecTransType",
    "21":  "HandlInst",
    "31":  "LastPx",
    "32":  "LastQty",
    "35":  "MsgType",
    "37":  "OrderID",
    "38":  "OrderQty",
    "39":  "OrdStatus",
    "41":  "OrigClOrdID",
    "44":  "Price",
    "49":  "SenderCompID",
    "54":  "Side",
    "55":  "Symbol",
    "56":  "TargetCompID",
    "58":  "Text",
    "60":  "TransactTime",
    "102": "CxlRejReason",
    "150": "ExecType",
    "151": "LeavesQty",
}


@dataclass
class TagResult:
    tag: str
    expected: str
    actual: str
    passed: bool
    missing: bool


def validate_tags(expected, actual):
    results = []
    for tag, exp_val in expected.items():
        tag = str(tag)
        exp_val = str(exp_val)
        if tag not in actual:
            results.append(TagResult(tag=tag, expected=exp_val, actual="", passed=False, missing=True))
        else:
            act_val = str(actual[tag])
            results.append(TagResult(tag=tag, expected=exp_val, actual=act_val, passed=(act_val == exp_val), missing=False))
    return results


def tag_name(tag):
    return TAG_NAMES.get(str(tag), "")
