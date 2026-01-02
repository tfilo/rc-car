from ure import search
from time import sleep_ms
import network
import rp2
import socket

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
        self.s = socket.socket()
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(address)
        self.s.listen(1)
        print("HTTP server running")

    def accept_client(self, voltage):
        client = self.s.accept()[0]

        request = client.recv(2048).decode()
        result = None

        if request.startswith("POST /control"):
            response = self.__success_response(voltage)
            match = search(
                r"steering=([-0-9]+)&drive=([-0-9]+)&horn=([-0-9]+)&light=([-0-9]+)",
                request,
            )
            if match:
                result = (
                    int(match.group(1)),
                    int(match.group(2)),
                    bool(int(match.group(3))),
                    bool(int(match.group(4))),
                )

        elif request.startswith("GET / "):
            response = STATIC_INDEX_RESPONSE

        elif request.startswith("GET /style.css "):
            response = STATIC_STYLE_RESPONSE

        elif request.startswith("GET /control.js "):
            response = STATIC_CONTROL_RESPONSE

        else:
            response = STATIC_NOT_FOUND_RESPONSE

        client.send(response)
        try:
            client.close()
        except Exception as e:
            print("WARN: wifi/server client.close() error:", e)

        return result

    def __success_response(self, voltage):
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n\r\n"
            '{"status":"ok", "battery":"' + str(voltage) + '"}'
        )
        return response
