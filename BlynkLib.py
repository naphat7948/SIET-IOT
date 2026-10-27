import socket
import struct
import time

HDR_LEN = 5
HDR_FMT = "!BHH"

MAX_MSG_PER_SEC = 20

MSG_RSP = 0
MSG_LOGIN = 2
MSG_PING = 6
MSG_TWEET = 12
MSG_EMAIL = 13
MSG_NOTIFY = 14
MSG_BRIDGE = 15
MSG_HW_SYNC = 16
MSG_INTERNAL = 17
MSG_PROPERTY = 19
MSG_HW = 20
MSG_HW_LOGIN = 29
MSG_EVENT_LOG = 64

STA_SUCCESS = 200

class Blynk:
    def __init__(self, token, server='blynk.cloud', port=80, connect=True, ssl=False):
        self.token = token
        self.server = server
        self.port = port
        self.ssl = ssl
        self.handlers = {}
        self.state = 0
        self.msg_id = 1
        self.conn = None
        self.last_send = 0
        self.last_recv = 0
        self.last_ping = 0
        if connect:
            self.connect()

    def connect(self):
        print(f"Connecting to Blynk server {self.server}:{self.port}...")
        self.conn = socket.socket()
        addr = socket.getaddrinfo(self.server, self.port)[0][-1]
        self.conn.connect(addr)
        if self.ssl:
            import ussl
            self.conn = ussl.wrap_socket(self.conn)
        self.conn.settimeout(0.05)
        # Login
        self.send(MSG_LOGIN, self.token)
        self.state = 1
        print("Blynk connected!")

    def send(self, msg_type, *args):
        data = ("\0".join(map(str, args))).encode('utf-8')
        self.msg_id = (self.msg_id + 1) & 0x7FFF
        hdr = struct.pack(HDR_FMT, msg_type, self.msg_id, len(data))
        self.conn.send(hdr + data)
        self.last_send = time.ticks_ms()

    def on(self, event):
        def decorator(func):
            self.handlers[event] = func
            return func
        return decorator

    def virtual_write(self, pin, *val):
        self.send(MSG_HW, 'vw', pin, *val)

    def run(self):
        if not self.conn:
            return
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_send) > 2000:
            self.send(MSG_PING)
        try:
            hdr = self.conn.recv(HDR_LEN)
            if not hdr:
                return
            msg_type, msg_id, length = struct.unpack(HDR_FMT, hdr)
            data = b""
            while len(data) < length:
                chunk = self.conn.recv(length - len(data))
                if not chunk:
                    break
                data += chunk

            if msg_type == MSG_RSP:
                pass
            elif msg_type == MSG_HW or msg_type == MSG_BRIDGE:
                parts = data.decode('utf-8').split("\0")
                cmd = parts[0]
                if cmd == 'vw':
                    pin = parts[1]
                    val = parts[2:]
                    key = f"V{pin}"
                    if key in self.handlers:
                        self.handlers[key](val)
        except OSError:
            pass