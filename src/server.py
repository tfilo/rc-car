from ure import search
from time import sleep_ms
import network
import rp2
import socket
import hashlib
import binascii

# ====== WIFI ACCESS POINT CONSTANTS ======
AP_SSID = "RcCar"
AP_PASSWORD = "12345678"  # min 8 znakov
WIFI_COUNTRY = "SK"
WIFI_CHANNEL = 11


# ====== LOAD STATIC FILE ======
def load_file(path):
    with open(path, "r") as f:
        return f.read()


index_html = load_file("index.html")
style_css = load_file("style.css")
control_js = load_file("control.js")

STATIC_INDEX_RESPONSE = (
    "HTTP/1.1 200 OK\r\n" "Content-Type: text/html\r\n\r\n" + index_html
)

STATIC_STYLE_RESPONSE = (
    "HTTP/1.1 200 OK\r\n" "Content-Type: text/css\r\n\r\n" + style_css
)

STATIC_CONTROL_RESPONSE = (
    "HTTP/1.1 200 OK\r\n" "Content-Type: application/javascript\r\n\r\n" + control_js
)

STATIC_NOT_FOUND_RESPONSE = "HTTP/1.1 404 Not Found\r\n\r\n"


class Server:

    def __init__(self):
        # ====== CREATING AP ======
        rp2.country(WIFI_COUNTRY)
        wlan = network.WLAN(network.AP_IF)
        wlan.config(essid=AP_SSID, password=AP_PASSWORD, channel=WIFI_CHANNEL)
        wlan.active(True)

        while not wlan.active():
            sleep_ms(100)

        print("AP ready:", wlan.ifconfig())
        print("AP SSID:", wlan.config("ssid"))
        print("AP channel:", wlan.config("channel"))

        # ====== HTTP SERVER ======
        address = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(address)
        self.s.listen(1)
        print("HTTP server running")
        self.client_socket = None  #

    def __generate_ws_accept(self, key):
        # WebSocket handshake requires a magic string
        GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        resp_key = hashlib.sha1((key + GUID).encode()).digest()
        return binascii.b2a_base64(resp_key).decode().strip()

    def __handle_handshake(self, client, request):
        # Search Sec-WebSocket-Key
        lines = request.split("\r\n")
        key = ""
        for line in lines:
            if "Sec-WebSocket-Key:" in line:
                key = line.split(":")[1].strip()
                break

        if key:
            accept_key = self.__generate_ws_accept(key)
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                "Sec-WebSocket-Accept: " + accept_key + "\r\n\r\n"
            )
            client.send(response)
            return True
        return False

    def __receive_ws_frame(self, client):
        """Very simplified reading of a WebSocket frame (text only)"""
        try:
            data = client.recv(64)
            if not data:
                return None

            # MicroPython masking implementation (the browser always masks client-to-server data)
            payload_len = data[1] & 127
            masks = data[2:6]
            payload = data[6 : 6 + payload_len]

            decoded = bytes([payload[i] ^ masks[i % 4] for i in range(len(payload))])
            return decoded.decode()
        except Exception:
            return None

    def __handle_http(self, client, request):
        """Processes classic GET requests for files"""
        if request.startswith("GET / "):
            response = STATIC_INDEX_RESPONSE
        elif request.startswith("GET /style.css "):
            response = STATIC_STYLE_RESPONSE
        elif request.startswith("GET /control.js "):
            response = STATIC_CONTROL_RESPONSE
        else:
            response = STATIC_NOT_FOUND_RESPONSE

        client.send(response)
        client.close()

    def send_ws_frame(self, payload):
        if self.client_socket is None:
            return

        try:
            # payload is a string
            payload_bytes = payload.encode("utf-8")
            length = len(payload_bytes)

            # Header construction:
            # 0x81 = 10000001 (FIN bit set, opcode 1 = text)
            header = bytearray([0x81])

            if length <= 125:
                header.append(length)
            else:
                # For messages 126 - 65535 bytes, the format is more complex
                # For simplicity, we only handle short messages here
                header.append(126)
                header.extend(length.to_bytes(2, "big"))

            self.client_socket.send(header + payload_bytes)
        except Exception as e:
            print("Error while sending frame:", e)
            self.client_socket.close()
            self.client_socket = None

    def listen_for_commands(self):
        """Main loop that handles either a new HTTP request or an existing WS"""
        if self.client_socket is None:
            # Waiting for a new connection
            client, addr = self.s.accept()
            request = client.recv(1024).decode()

            if "Upgrade: websocket" in request:
                if self.__handle_handshake(client, request):
                    print("WebSocket connected!")
                    self.client_socket = client
                    # We do not close the socket!
            else:
                # Classic HTTP (GET / etc.)
                self.__handle_http(client, request)
        else:
            # We have an active WebSocket, reading data
            msg = self.__receive_ws_frame(self.client_socket)
            if msg:
                print("WS received:", msg)
                # Here you process JSON or the string "steering,drive,horn,light"
                match = search(
                    r"steering=([-0-9]+)&drive=([-0-9]+)&horn=([-0-9]+)&light=([-0-9]+)",
                    msg,
                )
                if match:
                    result = (
                        int(match.group(1)),
                        int(match.group(2)),
                        bool(int(match.group(3))),
                        bool(int(match.group(4))),
                    )
                    return result
            else:
                self.client_socket.close()
                self.client_socket = None
        return None
