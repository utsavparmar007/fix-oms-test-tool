# FIX OMS Test Automation Tool

Connects to your OMS as a FIX 4.4 client, sends messages automatically,
and validates every response tag by tag. No UI. Pure terminal output.

---

## Project Structure

```
FIX TEST/
├── test.py                           ← Entry point
├── requirements.txt
├── config/
│   ├── client.cfg                    ← FIX session config
│   └── spec/FIX44.xml                ← FIX 4.4 data dictionary
├── fix_client/
│   ├── application.py                ← QuickFIX app (session + response capture)
│   └── builder.py                    ← Builds FIX messages from tag dicts
├── runner/
│   ├── test_runner.py                ← Sends messages, waits for response
│   ├── validator.py                  ← Tag-by-tag comparison
│   └── reporter.py                   ← Prints results in exact format
└── tests/
    ├── 01_new_order.json             ← New Order (35=D) test cases
    ├── 02_cancel.json                ← Cancel (35=F) / Cancel-Replace (35=G)
    ├── 03_cancel_active_order.json   ← Cancel against a live resting order
    ├── 04_replace_active_order.json  ← Replace (35=G) on an active order
    ├── 05_fill_scenarios.json        ← Full and partial fill scenarios
    ├── 06_position_request.json      ← Position request messages
    ├── 07_fok_ioc_experiment.json    ← FOK / IOC order type tests
    ├── 08_algo_order.json            ← Algo / algorithmic order tests
    └── 09_mass_cancel.json          ← Mass Cancel (35=q) / Report (35=r)
```

---

## Setup

```bash
# 1. Make sure OMS is running first


# 2. Install dependency
cd FIX TEST
pip install quickfix==1.15.1
# OR use your existing .whl:
pip install ../claude2/quickfix-1.15.1-cp39-cp39-win_amd64.whl

# 3. Run all tests
python test.py

# 4. Run a single test file
python test.py --tests tests/01_new_order.json

# 5. Run as CLIENT2
python test.py --sender CLIENT2

# 6. Increase response timeout to 10s
python test.py --timeout 10
```

---

## Output Format

```
══════════════════════════════════════════
 FIX OMS TEST AUTOMATION - RESULTS
══════════════════════════════════════════

[TEST 1] New Order - Valid Buy Limit
  ✅ Tag 35 = "8"    (MsgType)
  ✅ Tag 39 = "0"    (OrdStatus)
  ✅ Tag 55 = "AAPL"    (Symbol)
  ❌ Tag 54 expected "1" got "2"    (Side)
  RESULT: FAILED

[TEST 2] Cancel - Unknown ClOrdID
  ✅ Tag 35 = "9"    (MsgType)
  ✅ Tag 58 = "Unknown Order"    (Text)
  RESULT: PASSED

══════════════════════════════════════════
TOTAL: 2 tests | PASSED: 1 | FAILED: 1
══════════════════════════════════════════
```

---

## Writing Test Cases (JSON)

Each test case has 3 parts:

```json
{
  "name": "test name",
  "send": {
    "35": "D",       ← FIX tag number : value to send
    "55": "AAPL",
    "54": "1",
    "38": "100",
    "44": "150.00",
    "40": "2",
    "21": "1"
  },
  "expect": {
    "35": "8",       ← FIX tag number : expected value in OMS response
    "39": "0",
    "55": "AAPL",
    "54": "1"
  },
  "delay_after": 0.3,  ← optional seconds to wait AFTER this test
  "delay_before": 0.5  ← optional seconds to wait BEFORE sending this test
}
```

Put multiple test cases in one file as a JSON array `[{...}, {...}]`.
Files in `tests/` are loaded alphabetically — prefix with `01_`, `02_` to control order.

---

## Repeating Groups in JSON

To send a FIX repeating group (e.g. `NoParties` / Tag 453), use a nested list under the group count tag:

```json
{
  "name": "New Order with Parties",
  "send": {
    "35": "D",
    "55": "AAPL",
    "54": "1",
    "38": "100",
    "44": "150.00",
    "40": "2",
    "453": [
      {"448": "DESK1", "447": "D", "452": "76"},
      {"448": "FIRM1", "447": "D", "452": "1"}
    ]
  },
  "expect": {
    "35": "8",
    "39": "0"
  }
}
```

| Tag | Name           | Role |
|-----|----------------|------|
| 453 | NoParties      | Count of party entries in the group |
| 448 | PartyID        | Party identifier string |
| 447 | PartyIDSource  | `D` = Proprietary / Custom |
| 452 | PartyRole      | `1` = ExecutingFirm, `76` = TradingDesk |

---

## FOK and IOC Orders

Use Tag 59 (`TimeInForce`) to control order execution behaviour:

| Value | Name | Behaviour |
|-------|------|-----------|
| `0`   | Day  | Active for the trading day |
| `1`   | GTC  | Good Till Cancelled |
| `3`   | IOC  | Immediate Or Cancel — fill what you can, cancel the rest |
| `4`   | FOK  | Fill Or Kill — fully fill or reject entirely |

```json
{
  "name": "FOK Order - full fill expected",
  "send": {
    "35": "D",
    "55": "AAPL",
    "54": "1",
    "38": "100",
    "44": "150.00",
    "40": "2",
    "59": "4"
  },
  "expect": {
    "35": "8",
    "39": "2"
  }
}
```

---

## Mass Cancel (35=q / 35=r)

Send a `OrderMassCancelRequest` (35=q) to cancel all resting orders at once.
The OMS responds with an `OrderMassCancelReport` (35=r).

```json
{
  "name": "Mass Cancel - All Orders",
  "send": {
    "35": "q",
    "530": "7"
  },
  "expect": {
    "35": "r",
    "531": "7"
  },
  "delay_before": 0.5
}
```

| Tag | Name                    | Values |
|-----|-------------------------|--------|
| 530 | MassCancelRequestType   | `7` = Cancel All Orders |
| 531 | MassCancelResponse      | `7` = All Orders Canceled, `0` = Cancel Request Rejected |

---

## Common FIX Tags Reference

| Tag | Name                  | Common Values |
|-----|-----------------------|---------------|
| 35  | MsgType               | D=New, F=Cancel, G=Replace, q=MassCancel, 8=ExecReport, 9=CancelReject, r=MassCancelReport |
| 54  | Side                  | 1=Buy, 2=Sell |
| 38  | OrderQty              | integer |
| 44  | Price                 | decimal |
| 40  | OrdType               | 1=Market, 2=Limit |
| 59  | TimeInForce           | 0=Day, 1=GTC, 3=IOC, 4=FOK |
| 39  | OrdStatus             | 0=New, 1=PartFill, 2=Filled, 4=Canceled, 8=Rejected |
| 150 | ExecType              | 0=New, 1=PartFill, 2=Fill, 4=Canceled, 8=Rejected |
| 55  | Symbol                | e.g. AAPL |
| 58  | Text                  | Free text / reject reason |
| 11  | ClOrdID               | auto-generated if not provided |
| 41  | OrigClOrdID           | required for Cancel (35=F) and Replace (35=G) |
| 14  | CumQty                | Total quantity filled so far |
| 151 | LeavesQty             | Remaining open quantity |
| 453 | NoParties             | Repeating group: number of party entries |
| 448 | PartyID               | Party identifier string |
| 447 | PartyIDSource         | D=Proprietary/Custom |
| 452 | PartyRole             | 1=ExecutingFirm, 76=TradingDesk |
| 530 | MassCancelRequestType | 7=Cancel All Orders |
| 531 | MassCancelResponse    | 7=All Orders Canceled, 0=Rejected |
