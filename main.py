from servo import Servo
from machine import Pin, PWM, ADC
from time import sleep_ms, ticks_ms, ticks_diff
from math import floor
from network import country, WLAN, AP_IF
from socket import socket, getaddrinfo
from ure import search
from _thread import start_new_thread

# ====== WIFI ACCESS POINT CONSTANTS ======
AP_SSID = "RcCar"
AP_PASSWORD = "12345678"  # min 8 znakov
WIFI_COUNTRY = "SK"
WIFI_CHANNEL = 11

# ====== CONFIGURATION ======
STEERING_MIN, STEERING_MAX = 0, 116
STEERING_MID = floor(STEERING_MAX / 2)
MOTOR_MAX_DUTY_CYCLE = 65535
MOTOR_MIN_DUTY_CYCLE = 48000
MOTOR_ZERO_DUTY_CYCLE = 0

motor1a = PWM(Pin(14, Pin.OUT))
motor1b = PWM(Pin(15, Pin.OUT))
servo = Servo(pin_id=0)

motor1a.freq(20000)
motor1b.freq(20000)

# ====== ADC BATTERY MEASUREMENT =====

battery_input = ADC(26)


def get_battery_voltage():
    battery_value = battery_input.read_u16()
    return battery_value * (3.3 / 65535) * 2


voltage = get_battery_voltage()

# ====== GLOBAL STATE ======
steering = STEERING_MID
drive = 0
horn = 0
last_action_time = ticks_ms()


# ====== CONTROL FUNCTIONS ======
def map_range(x, in_min, in_max, out_min, out_max):
    # Clamp input to ensure it stays within expected bounds
    x = max(in_min, min(x, in_max))
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)


def forward(duty_cycle):
    motor1a.duty_u16(duty_cycle)
    motor1b.duty_u16(MOTOR_ZERO_DUTY_CYCLE)


def backward():
    motor1a.duty_u16(MOTOR_ZERO_DUTY_CYCLE)
    motor1b.duty_u16(MOTOR_MIN_DUTY_CYCLE)


def stop():
    motor1a.duty_u16(MOTOR_ZERO_DUTY_CYCLE)
    motor1b.duty_u16(MOTOR_ZERO_DUTY_CYCLE)


# ====== PREVENTIVE STOP AND RESET OF STEERING ======
stop()
servo.write(STEERING_MID)


def servo_control_thread():
    counter = 0
    horn_prev = 0
    buzzer = None
    while True:
        try:
            counter += 1
            elapsed_ms = ticks_diff(ticks_ms(), last_action_time)
            if elapsed_ms > 500:
                global steering, drive
                steering = STEERING_MID
                drive = 0

            if counter > 1000:
                counter = 0
                global voltage
                voltage = get_battery_voltage()

            servo.write(steering)
            if drive == -1:
                backward()
            elif drive == 0:
                stop()
            else:
                forward(drive)

            if horn == 1 and horn_prev == 0:
                horn_prev = 1
                buzzer = PWM(Pin(16))
                buzzer.duty_u16(10000)
                buzzer.freq(300)
            elif horn == 0 and horn_prev == 1:
                horn_prev = 0
                buzzer.duty_u16(0)
                sleep_ms(10)
                buzzer.deinit()
                Pin(16, Pin.IN)

        except Exception:
            pass
        sleep_ms(20)


start_new_thread(servo_control_thread, ())

# ====== CREATING AP ======
country(WIFI_COUNTRY)
ap = WLAN(AP_IF)
ap.config(essid=AP_SSID, password=AP_PASSWORD, channel=WIFI_CHANNEL)
ap.active(True)

while not ap.active():
    sleep_ms(100)

print("AP ready:", ap.ifconfig())
print("AP SSID:", ap.config("ssid"))
print("AP channel:", ap.config("channel"))


# ====== LOAD STATIC FILE ======
def load_file(path):
    with open(path, "r") as f:
        return f.read()


index_html = load_file("index.html")

# ====== HTTP SERVER ======
addr = getaddrinfo("0.0.0.0", 80)[0][-1]
sock = socket()
sock.bind(addr)
sock.listen(1)

print("HTTP server running")

while True:
    try:
        cl, addr = sock.accept()
        request = cl.recv(1024).decode()

        if request.startswith("GET / "):
            response = (
                "HTTP/1.1 200 OK\r\n" "Content-Type: text/html\r\n\r\n" + index_html
            )

        elif request.startswith("POST /control"):
            match = search(
                r"steering=([-0-9]+)&drive=([-0-9]+)&horn=([-0-9]+)", request
            )
            if match:
                steering_val = int(match.group(1))
                # Map steering with clamping
                steering = map_range(steering_val, 0, 100, STEERING_MIN, STEERING_MAX)
                drive_val = int(match.group(2))
                if drive_val == -1:
                    drive = -1
                elif drive_val == 0:
                    drive = 0
                else:
                    drive = map_range(
                        drive_val, 1, 3, MOTOR_MIN_DUTY_CYCLE, MOTOR_MAX_DUTY_CYCLE
                    )
                horn = int(match.group(3))

                last_action_time = ticks_ms()
                print("STEERING:", steering, "DRIVE:", drive, "HORN:", horn)

            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n\r\n"
                '{"status":"ok", "battery":"' + str(voltage) + '"}'
            )

        else:
            response = "HTTP/1.1 404 Not Found\r\n\r\n"

        cl.send(response)
    except Exception as e:
        print("WARN: wifi/server thread restart", e)
        pass
    finally:
        try:
            if cl:
                cl.close()
        except Exception:
            pass
    sleep_ms(10)
