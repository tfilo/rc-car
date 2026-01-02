from time import sleep_ms
from rc_car import RcCar
from battery import Battery
from server import Server
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

counter = 0
voltage = battery.read_voltage()

while True:
    try:
        counter += 1

        if counter > 1000:
            counter = 0
            voltage = battery.read_voltage()

        request = server.listen_for_commands()
        if request is not None:
            rc_car.update(request[0], request[1], request[2], request[3])
        server.send_ws_frame(str(voltage))

    except KeyboardInterrupt:
        raise
    except Exception as e:
        print("WARN: wifi/server thread restart:", e)

    sleep_ms(10)

