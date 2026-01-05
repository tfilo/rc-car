from time import sleep_ms
from rc_car import RcCar
from battery import Battery
from server import Server
import os
import sys

try:
    # Backup old log file if exists
    logfile = open("log.txt", "r")
    oldlog = open("log.old.txt", "w")
    oldlog.write(logfile.read())
    oldlog.close()
    logfile.close()
except Exception as e:
    pass

# Redirect stdout and stderr to log file
logfile = open("log.txt", "w+")
os.dupterm(logfile)

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
voltage_history = [0] * 10
for i in range(10):
    sleep_ms(10)
    voltage_history[i] = battery.read_voltage()

while True:
    try:
        counter += 1

        if counter > 100:
            counter = 0
            # Update voltage history
            voltage_history.pop(0)
            voltage_history.append(battery.read_voltage())
            # Calculate average
            voltage = sum(voltage_history) / len(voltage_history)
            server.send_ws_frame(str(voltage))

        request = server.listen_for_commands()
        if request is not None:
            rc_car.update(request[0], request[1], request[2], request[3])

    except KeyboardInterrupt:
        raise
    except Exception as e:
        print("--- WARN: wifi/server thread restart ---")
        sys.print_exception(e)
        print("-------------")

    logfile.flush()
    sleep_ms(10)
