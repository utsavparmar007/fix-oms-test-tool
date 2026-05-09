import quickfix as fix
import threading
import queue


class FIXTestApplication(fix.Application):

    def __init__(self):
        super().__init__()
        self._session_id = None
        self._connected = False
        self._lock = threading.Lock()
        self.response_queue = queue.Queue()

    def onCreate(self, sessionID):
        with self._lock:
            self._session_id = sessionID

    def onLogon(self, sessionID):
        with self._lock:
            self._session_id = sessionID
            self._connected = True

    def onLogout(self, sessionID):
        with self._lock:
            self._connected = False

    def toAdmin(self, message, sessionID):
        pass

    def fromAdmin(self, message, sessionID):
        # Capture session-level rejects (35=3) so tests see them instead of timing out
        try:
            msg_type = fix.MsgType()
            message.getHeader().getField(msg_type)
            if msg_type.getValue() == "3":
                tags = self._parse_message(message)
                tags["_session_reject"] = True
                self.response_queue.put(tags)
        except Exception:
            pass

    def toApp(self, message, sessionID):
        pass

    def fromApp(self, message, sessionID):
        try:
            tags = self._parse_message(message)
            self.response_queue.put(tags)
        except Exception as e:
            self.response_queue.put({"_error": str(e)})

    def _parse_message(self, message):
        tags = {}

        header = message.getHeader()
        begin = fix.BeginString()
        header.getField(begin)
        tags["8"] = begin.getValue()

        for tag in [35, 49, 56, 34, 52]:
            try:
                f = fix.StringField(tag)
                header.getField(f)
                tags[str(tag)] = f.getValue()
            except Exception:
                pass

        for part in message.toString().split('\x01'):
            if '=' in part:
                tag_num, val = part.split('=', 1)
                if tag_num.strip().isdigit():
                    tags[tag_num.strip()] = val

        return tags

    @property
    def is_connected(self):
        with self._lock:
            return self._connected

    @property
    def session_id(self):
        with self._lock:
            return self._session_id

    def send(self, message):
        try:
            fix.Session.sendToTarget(message, self.session_id)
            return True
        except Exception:
            return False
