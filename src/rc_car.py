import _thread
from time import sleep_ms, ticks_ms, ticks_diff
from math import floor
from servo import Servo
from machine import Pin, PWM

# ====== CONFIGURATION OF HARDWARE VALUES RANGE ======
STEERING_SERVO_MIN, STEERING_SERVO_MAX = 0, 116
STEERING_SERVO_MID = floor(STEERING_SERVO_MAX / 2)

MOTOR_MAX_DUTY_CYCLE = 65535
MOTOR_MIN_DUTY_CYCLE = 48000
MOTOR_ZERO_DUTY_CYCLE = 0
MOTOR_FREQ_HZ = 20000

LED_OFF = 0
LED_ON = 1

HORN_FREQUENCY_HZ = 300
HORN_DUTY_CYCLE = 20000
HORN_DUTY_CYCLE_OFF = 0

# ====== CONFIGURATION OF CONTROL VALUES RANGE ======
DRIVE_MIN_SPEED = 1
DRIVE_MAX_SPEED = 3
STEERING_MIN = 0
STEERING_MAX = 100

# ====== GLOBAL VARIABLES ======
EMERGENCY_STOP_TIMEOUT_MS = 500
BATTERY_MEASURE_EVERY_N_CYCLES = 1500

# ====== INITIAL STATES ======
INIT_STEERING = int(STEERING_MAX / 2)
INIT_DRIVE = 0
INIT_HORN = False
INIT_LIGHT = False


def map_range(x, in_min, in_max, out_min, out_max):
    # Clamp input to ensure it stays within expected bounds
    x = max(in_min, min(x, in_max))
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)


class RcCar:
    steering = INIT_STEERING
    drive = INIT_DRIVE
    horn = INIT_HORN
    light = INIT_LIGHT
    last_action_time = ticks_ms()

    def __init__(self, motor_a_pin, motor_b_pin, steer_servo_pin, light_pin, horn_pin):
        self.pins = {
            "motor_a_pin": motor_a_pin,
            "motor_b_pin": motor_b_pin,
            "steer_servo_pin": steer_servo_pin,
            "light_pin": light_pin,
            "horn_pin": horn_pin,
        }

        self.motor1a = PWM(Pin(self.pins["motor_a_pin"], Pin.OUT))
        self.motor1b = PWM(Pin(self.pins["motor_b_pin"], Pin.OUT))
        self.servo = Servo(pin_id=self.pins["steer_servo_pin"])
        self.servo.write(STEERING_SERVO_MID)
        self.motor1a.freq(MOTOR_FREQ_HZ)
        self.motor1b.freq(MOTOR_FREQ_HZ)
        self.motor1a.duty_u16(MOTOR_ZERO_DUTY_CYCLE)
        self.motor1b.duty_u16(MOTOR_ZERO_DUTY_CYCLE)
        self.light_led = Pin(self.pins["light_pin"], Pin.OUT)
        self.light_led.value(LED_OFF)
        _thread.start_new_thread(self.__servo_control_thread, ())

    def update(self, steering, drive, horn, light):
        self.steering = steering
        self.drive = drive
        self.horn = horn
        self.light = light
        self.last_action_time = ticks_ms()

    def __steer(self, angle):
        # angle can be from 0 to 100, (50 is straight)
        steering = map_range(
            angle, STEERING_MIN, STEERING_MAX, STEERING_SERVO_MIN, STEERING_SERVO_MAX
        )
        self.servo.write(steering)

    def __forward(self, speed):
        # speed can be 1, 2, or 3
        duty_cycle = map_range(
            speed,
            DRIVE_MIN_SPEED,
            DRIVE_MAX_SPEED,
            MOTOR_MIN_DUTY_CYCLE,
            MOTOR_MAX_DUTY_CYCLE,
        )
        self.motor1a.duty_u16(duty_cycle)
        self.motor1b.duty_u16(MOTOR_ZERO_DUTY_CYCLE)

    def __backward(self):
        self.motor1a.duty_u16(MOTOR_ZERO_DUTY_CYCLE)
        self.motor1b.duty_u16(MOTOR_MIN_DUTY_CYCLE)

    def __stop(self):
        self.motor1a.duty_u16(MOTOR_ZERO_DUTY_CYCLE)
        self.motor1b.duty_u16(MOTOR_ZERO_DUTY_CYCLE)

    def __light_on(self):
        self.light_led.value(LED_ON)

    def __light_off(self):
        self.light_led.value(LED_OFF)

    def __horn_on(self):
        self.buzzer = PWM(Pin(self.pins["horn_pin"], Pin.OUT))
        self.buzzer.duty_u16(HORN_DUTY_CYCLE)
        self.buzzer.freq(HORN_FREQUENCY_HZ)

    def __horn_off(self):
        self.buzzer.duty_u16(HORN_DUTY_CYCLE_OFF)
        self.buzzer.deinit()
        Pin(self.pins["horn_pin"], Pin.IN)

    def __reset(self):
        self.drive = INIT_DRIVE
        self.steering = INIT_STEERING
        self.horn = INIT_HORN
        self.light = INIT_LIGHT

    def __servo_control_thread(self):
        horn_prev = False
        while True:
            try:
                elapsed_ms = ticks_diff(ticks_ms(), self.last_action_time)
                if elapsed_ms > EMERGENCY_STOP_TIMEOUT_MS:
                    self.__reset()

                self.__steer(self.steering)

                if self.drive == -1:
                    self.__backward()
                elif self.drive == 0:
                    self.__stop()
                else:
                    self.__forward(self.drive)
                if self.horn == True and horn_prev == False:
                    horn_prev = True
                    self.__horn_on()
                elif self.horn == False and horn_prev == True:
                    horn_prev = False
                    self.__horn_off()

                if self.light == True:
                    self.__light_on()
                else:
                    self.__light_off()

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print("WARN: servo_control_thread error:", e)
            sleep_ms(10)

