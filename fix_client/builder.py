import quickfix as fix
import uuid
from datetime import datetime


_HEADER_TAGS = {"8", "35", "49", "56", "34", "52", "115", "116", "128", "129"}

# Maps group count tag → (delimiter tag, [field_order])
# Add more here if you need other repeating groups in future
_GROUP_DEFINITIONS = {
    "453": (448, [448, 447, 452, 802, 0]),   # NoParties → PartyID
}

# Message types that require a ClOrdID (Tag 11) auto-generated if not provided.
# Non-order messages like AN (RequestForPositions) must NOT receive Tag 11 —
# QuickFIX will session-reject them with TagNotDefinedForMsg.
_MSG_TYPES_REQUIRING_CL_ORD_ID = {
    "D",   # NewOrderSingle
    "F",   # OrderCancelRequest
    "G",   # OrderCancelReplaceRequest
    "H",   # OrderStatusRequest
    "V",   # MarketDataRequest
    "q",   # OrderMassCancelRequest
}


def gen_cl_ord_id():
    ts = datetime.now().strftime("%H%M%S")
    uid = str(uuid.uuid4()).replace("-", "")[:5].upper()
    return f"TEST-{ts}-{uid}"


def build_message_from_tags(tags):
    new_tags = {}
    for k, v in tags.items():
        if k == "groups":
            new_tags[k] = v
        else:
            new_tags[str(k)] = str(v)
    tags = new_tags

    msg_type = tags.get("35", "D")

    # Only auto-generate ClOrdID (Tag 11) for message types that define it.
    # Injecting Tag 11 into messages like AN (RequestForPositions) causes a
    # FIX session-level reject: "Tag not defined for this message type".
    if "11" not in tags and msg_type in _MSG_TYPES_REQUIRING_CL_ORD_ID:
        tags["11"] = gen_cl_ord_id()
    msg = fix.Message()
    msg.getHeader().setField(fix.MsgType(msg_type))

    # Pull out any repeating group definitions before processing flat tags
    groups = _extract_groups(tags)

    for tag_str, value in tags.items():
        if tag_str in _HEADER_TAGS:
            continue
        if tag_str == "60":
            msg.setField(fix.TransactTime())
            continue
        # Skip group count tags — QuickFIX sets these automatically via addGroup
        if tag_str in _GROUP_DEFINITIONS:
            continue
        try:
            msg.setField(fix.StringField(int(tag_str), value))
        except Exception:
            pass

    # Attach repeating groups
    for count_tag, entries in groups.items():
        if count_tag not in _GROUP_DEFINITIONS:
            continue
        delimiter_tag, field_order = _GROUP_DEFINITIONS[count_tag]
        
        arr = fix.IntArray(len(field_order))
        for i, f_tag in enumerate(field_order):
            arr[i] = int(f_tag)
            
        for entry in entries:
            grp = fix.Group(int(count_tag), int(delimiter_tag), arr)
            for t, v in entry.items():
                try:
                    grp.setField(fix.StringField(int(t), str(v)))
                except Exception:
                    pass
            msg.addGroup(grp)

    if not msg.isSetField(fix.TransactTime()):
        msg.setField(fix.TransactTime())

    return msg


def _extract_groups(tags):
    """
    Reads 'groups' key from tags if present and returns structured group data.

    Expected format in the send dict:
        "groups": {
            "453": [
                {"448": "BROKER01", "447": "D", "452": "1"},
                {"448": "TRADER_JK", "447": "D", "452": "36"}
            ]
        }

    Returns: {"453": [{"448": "BROKER01", ...}, ...]}
    """
    raw = tags.pop("groups", None)
    if not raw:
        return {}

    # tags values are all strings at this point, so groups arrives as a string
    # if it came from JSON via the normal path — but test_runner passes dicts
    # directly, so we handle both
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except Exception:
            return {}

    return {str(k): v for k, v in raw.items()}