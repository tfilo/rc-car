import struct
import asyncio
import aioble
import bluetooth
import time

from math import floor
from servo import Servo
from machine import PWM, Pin

# ==========================================
# BLE configuration
# ==========================================
ble_name = "rpi_joystick"
ble_svc_uuid = bluetooth.UUID(0x1812) # HID
ble_characteristic_uuid = bluetooth.UUID(0x2A4D) # REPORT
ble_scan_length = 5000
ble_interval = 30000
ble_window = 30000
TARGET_PERIOD_US = 20000 # Target frame rate of reading values 20ms

# ==========================================
# CAR configuration
# ==========================================
HORN_FREQUENCY_HZ = 400
HORN_DUTY_CYCLE = 5000
HORN_DUTY_CYCLE_OFF = 0
STEERING_SERVO_MIN, STEERING_SERVO_MAX = 0, 116
STEERING_SERVO_MID = floor(STEERING_SERVO_MAX / 2)
STEERING_MIN = -100
STEERING_MAX = 100
MOTOR_FREQ_HZ = 20000
MOTOR_ZERO_DUTY_CYCLE = 0
THROTTLE_MIN = -100
THROTTLE_MAX = 100

# Motor pins
motor1a = PWM(Pin(14, Pin.OUT))
motor1b = PWM(Pin(15, Pin.OUT))
motor1a.freq(MOTOR_FREQ_HZ)
motor1b.freq(MOTOR_FREQ_HZ)
motor1a.duty_u16(MOTOR_ZERO_DUTY_CYCLE)
motor1b.duty_u16(MOTOR_ZERO_DUTY_CYCLE)
# Steering servo pin
servo = Servo(pin_id=0)
servo.write(STEERING_SERVO_MID)
# Led light pin
light_led = Pin(1, Pin.OUT)
light_led.on()
# Buzzer variable
buzzer = None

time.sleep_ms(500)

# Status LED
led = Pin("LED", Pin.OUT)
led.off()

# BLE Status
connected = False

# ==========================================
# Calculate duty cycle from percentage
# ==========================================
def get_duty_cycle_from_percentage(input_percent: int) -> int:
    abs_percentage = abs(input_percent)
    # Boundary checks
    if abs_percentage <= 1:
        return 42000
    if abs_percentage >= 100:
        return 65535

    # Map 1..100 input range to original 1..4 scale
    x = 1.0 + ((abs_percentage - 1.0) / 99.0) * 3.0

    # Control points and smooth tangents
    y = [42000, 45000, 52000, 65535]
    m = [2500, 5000, 10000, 13535]

    # Find active curve segment
    i = min(int(x) - 1, 2)
    t = x - (i + 1)

    # Cubic Hermite basis functions
    h00 = 2 * (t**3) - 3 * (t**2) + 1
    h10 = (t**3) - 2 * (t**2) + t
    h01 = -2 * (t**3) + 3 * (t**2)
    h11 = (t**3) - (t**2)

    # Calculate smooth PWM value
    pwm = h00 * y[i] + h10 * m[i] + h01 * y[i + 1] + h11 * m[i + 1]
    return round(pwm)

# ==========================================
# Map range function
# ==========================================
def map_range(x, in_min, in_max, out_min, out_max):
    # Clamp input to ensure it stays within expected bounds
    x = max(in_min, min(x, in_max))
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

# ==========================================
# Turn buzzer on
# ==========================================
def horn_on():
    global buzzer
    if buzzer is None:
        buzzer = PWM(Pin(16, Pin.OUT))
        buzzer.duty_u16(HORN_DUTY_CYCLE)
        buzzer.freq(HORN_FREQUENCY_HZ)

# ==========================================
# Turn buzzer off
# ==========================================
def horn_off():
    global buzzer
    if buzzer is not None:
        buzzer.duty_u16(HORN_DUTY_CYCLE_OFF)
        buzzer.deinit()
        Pin(16, Pin.IN)
        buzzer = None

# ==========================================
# Set steering to angle
# ==========================================
def steer(angle):
    # angle can be from -100 to 100, (0 is straight)
    steering = map_range(
        angle, STEERING_MIN, STEERING_MAX, STEERING_SERVO_MIN, STEERING_SERVO_MAX
    )
    if servo.read() != steering:
        servo.write(steering)

# ==========================================
# Set motor throttle
# ==========================================
def drive(throttle):
    global motor1a
    global motor1b
    # throttle can be from -100 to 100, (0 is stop)
    
    if throttle == 0:
        motor1a.duty_u16(MOTOR_ZERO_DUTY_CYCLE)
        motor1b.duty_u16(MOTOR_ZERO_DUTY_CYCLE)
    
    if throttle > 0:
        duty_cycle = get_duty_cycle_from_percentage(throttle)
        motor1a.duty_u16(duty_cycle)
        motor1b.duty_u16(MOTOR_ZERO_DUTY_CYCLE)
        
    if throttle < 0:
        duty_cycle = get_duty_cycle_from_percentage(throttle)
        motor1a.duty_u16(MOTOR_ZERO_DUTY_CYCLE)
        motor1b.duty_u16(duty_cycle)

# ==========================================
# Decode values
# ==========================================
def decode_values(data: bytes):
    throttle, steering, btn_l, btn_r = struct.unpack("<hhBB", data)
    return throttle, steering, btn_l, btn_r

# ==========================================
# LED task
# ==========================================
async def led_task():
    while True:
        if connected:
            led.on()
        else:
            led.toggle()
        await asyncio.sleep_ms(500)

# ==========================================
# BLE scan
# ==========================================
async def ble_scan():
    print(f"Scanning for BLE controller named", ble_name, "...")
    async with aioble.scan(
        ble_scan_length,
        interval_us=ble_interval,
        window_us=ble_window,
        active=True
    ) as scanner:
        async for result in scanner:
            if result.name() == ble_name and ble_svc_uuid in result.services():
                return result.device
    return None

# ==========================================
# Car controll Loop
# ==========================================
async def car_control():
    global connected
    last_packet_time = time.ticks_ms()
    failsafe_timeout = 250  # Stop motors if no data received for 250ms
    prev_light = 0;

    while True:
        connected = False
        drive(0)
        horn_off()
        light_led.off()
        steer(0)
        device = await ble_scan()
        if not device:
            print("BLE controller not found.")
            continue
        try:
            print("Connecting to", device)
            connection = await device.connect()
        except asyncio.TimeoutError:
            print("Connection timed out.")
            continue

        async with connection:
            try:
                ble_service = await connection.service(ble_svc_uuid)
                ble_characteristic = await ble_service.characteristic(ble_characteristic_uuid)
                connected = True
            except (asyncio.TimeoutError, AttributeError):
                print("Timeout discovering services/characteristics.")
                connected = False
                continue
        
            while True:
                start_time = time.ticks_us()
                if time.ticks_diff(time.ticks_ms(), last_packet_time) > failsafe_timeout:
                    drive(0)
                    horn_off()
                    light_led.off()
                    steer(0)

                try:
                    throttle, steering, light, horn = decode_values(await ble_characteristic.read())
                except Exception:
                    print("Connection lost.")
                    break

                last_packet_time = time.ticks_ms()
                steer(steering)
                drive(throttle)

                if horn == 1:
                    horn_on()
                else:
                    horn_off()
                        
                # One press to turn on, second press to turn off
                if prev_light == 0 and light == 1:
                    light_led.toggle()
                prev_light = light
            
                elapsed_us = time.ticks_diff(time.ticks_us(), start_time)
                time_to_sleep_us = max(0, TARGET_PERIOD_US - elapsed_us)
                await asyncio.sleep_ms(time_to_sleep_us // 1000)

# ==========================================
# Main Loop
# ==========================================
async def main():
    task1 = asyncio.create_task(car_control())
    task2 = asyncio.create_task(led_task())
    await asyncio.gather(task1, task2)
            
asyncio.run(main())
