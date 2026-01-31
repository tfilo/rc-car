import network
import rp2
from time import sleep_ms

class AP:

    def __init__(self, AP_SSID = "RcCar", AP_PASSWORD = "12345678", WIFI_COUNTRY = "SK", WIFI_CHANNEL = 11):
        # ====== CREATING AP ======
        rp2.country(WIFI_COUNTRY)
        ap = network.WLAN(network.AP_IF)
        ap.config(essid=AP_SSID, password=AP_PASSWORD, channel=WIFI_CHANNEL)
        ap.active(True)

        while not ap.active():
            sleep_ms(100)

        print("AP ready:", ap.ifconfig())
        print("AP SSID:", ap.config("essid"))
        print("AP channel:", ap.config("channel"))
