from ure import search
from time import sleep_ms
from rc_car import RcCar
from battery import Battery
from server import (
    Server,
    STATIC_INDEX_RESPONSE,
    STATIC_STYLE_RESPONSE,
    STATIC_CONTROL_RESPONSE,
    STATIC_NOT_FOUND_RESPONSE,
)

# import os

# logfile = open("log.txt", "a")
# os.dupterm(logfile)

# ====== ADC BATTERY =====

battery = Battery()

# ====== CAR CONTROLS ======
rc_car = RcCar(
    motor_a_pin=14,
    motor_b_pin=15,
    steer_servo_pin=0,
    light_pin=1,
    horn_pin=16,
)

# ====== SERVER ======
server = Server()


while True:
    client = None
    counter = 0
    voltage = battery.read_voltage()
    try:
        counter += 1
        client, address = server.accept_client()
        request = client.recv(2048).decode()

        if counter > 1000:
            voltage = battery.read_voltage()
            counter = 0
        
        response = None
        if request.startswith("POST /control"):
            match = search(
                r"steering=([-0-9]+)&drive=([-0-9]+)&horn=([-0-9]+)&light=([-0-9]+)",
                request,
            )
            if match:
                rc_car.update(
                    int(match.group(1)),
                    int(match.group(2)),
                    bool(int(match.group(3))),
                    bool(int(match.group(4))),
                )

            response = server.success_response(voltage)

        elif request.startswith("GET / "):
            response = STATIC_INDEX_RESPONSE

        elif request.startswith("GET /style.css "):
            response = STATIC_STYLE_RESPONSE

        elif request.startswith("GET /control.js "):
            response = STATIC_CONTROL_RESPONSE

        else:
            response = STATIC_NOT_FOUND_RESPONSE

        client.send(response)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print("WARN: wifi/server thread restart:", e)
    finally:
        try:
            if client:
                client.close()
        except Exception as e:
            print("WARN: wifi/server client.close() error:", e)
    sleep_ms(10)
