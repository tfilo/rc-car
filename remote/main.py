import struct
import asyncio
import aioble
import bluetooth
import time

from machine import ADC, Pin

# ==========================================
# BLE configuration
# ==========================================
ble_name = "rpi_joystick"
ble_svc_uuid = bluetooth.UUID(0x1812) # HID
ble_characteristic_uuid = bluetooth.UUID(0x2A4D) # REPORT
ble_appearance = 0x0340
ble_advertising_interval = 20 # 50 times per second

ble_service = aioble.Service(ble_svc_uuid)
ble_characteristic = aioble.Characteristic(
    ble_service,
    ble_characteristic_uuid,
    read=True,
    notify=True)
aioble.register_services(ble_service)

# ==========================================
# CONTROLLER configuration
# ==========================================
ADC_RANGE = 65535
AXIS_DEATH_ZONE = 5 # 5% dead zone for joystick in each direction
AXIS_RANGE = 200 + (AXIS_DEATH_ZONE * 2)# Range of axis from edge to edge, this allows to run from middle to 100% for each side
CONVERSION_FACTOR = (AXIS_RANGE ) / ADC_RANGE # Used to translate Joystick values to 0 - 100%
BUFFER_SIZE = 50 # How much values in row should be averaged
TARGET_PERIOD_US = 1000 # Target frame rate of reading values 1ms

# OnBoard LED
led = Pin("LED", Pin.OUT)
led.off()
# Throttle signal comming from Joystick
adc_throttle = ADC(27)
# Stearing Wheel signal comming from Joystick
adc_steering = ADC(26)
# Push buttons that goes to ground when pressed
pin_btn_right = Pin(15, Pin.IN, Pin.PULL_UP)
pin_btn_left = Pin(14, Pin.IN, Pin.PULL_UP)
# Default values
throttle = 0
steering = 0
state_btn_r = 0
state_btn_l = 0

# BLE Status
connected = False

# ==========================================
# Calculate steering or throttle state
# ==========================================
def calculate_percentage(samples):
    average = sum(samples) / len(samples)
    percentage_raw = int(round(average * CONVERSION_FACTOR))
    clamped = max(0, min(AXIS_RANGE, percentage_raw))
    
    centered = clamped - int(AXIS_RANGE / 2)
    if abs(centered) < (AXIS_DEATH_ZONE):
        return 0
    if (centered > 0):
        return centered - AXIS_DEATH_ZONE
    else:
        return centered + AXIS_DEATH_ZONE

# ==========================================
# Calculate button state
# ==========================================
def calculate_button(samles):
    return 0 if sum(samles) >= (len(samles) / 2) else 1

# ==========================================
# Encode values
# ==========================================
def encode_values(throttle: int, steering: int, btn_l: int, btn_r: int):
    return struct.pack("<hhBB", throttle, steering, btn_l, btn_r)

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
# BLE task
# ==========================================
async def ble_task():
    global connected
    while True:
        connected = False
        async with await aioble.advertise(
            ble_advertising_interval,
            name=ble_name,
            services=[ble_svc_uuid],
            appearance=ble_appearance
        ) as connection:
            print("Connection from", connection.device)
            connected = True
            await connection.disconnected()
            
# ==========================================
# Reading values task
# ==========================================
async def input_task():
    throttle_samples = []
    steering_samples = []
    btn_right_samples = []
    btn_left_samples = []
    
    loop_counter = 0
    
    while True:
        start_time = time.ticks_us()
        
        if not connected:
            if len(throttle_samples) > 0:
                throttle_samples.clear()
                steering_samples.clear()
                btn_left_samples.clear()
                btn_right_samples.clear()
            elapsed_us = time.ticks_diff(time.ticks_us(), start_time)
            time_to_sleep_us = max(0, TARGET_PERIOD_US - elapsed_us)
            await asyncio.sleep_ms(time_to_sleep_us // 1000)
            continue

        # Read values from pins
        throttle_samples.append(adc_throttle.read_u16())
        steering_samples.append(adc_steering.read_u16())
        btn_left_samples.append(pin_btn_left.value())
        btn_right_samples.append(pin_btn_right.value())

        # Remove oldest value if buffer is full
        if len(throttle_samples) > BUFFER_SIZE:
            throttle_samples.pop(0)
        if len(steering_samples) > BUFFER_SIZE:
            steering_samples.pop(0)
        if len(btn_left_samples) > BUFFER_SIZE:
            btn_left_samples.pop(0)
        if len(btn_right_samples) > BUFFER_SIZE:
            btn_right_samples.pop(0)

        loop_counter += 1
        if loop_counter >= 20:
            loop_counter = 0
            throttle = calculate_percentage(throttle_samples)
            steering = calculate_percentage(steering_samples)
            state_btn_l = calculate_button(btn_left_samples)
            state_btn_r = calculate_button(btn_right_samples)
            
            ble_characteristic.write(encode_values(throttle, steering, state_btn_l, state_btn_r))
        elapsed_us = time.ticks_diff(time.ticks_us(), start_time)
        time_to_sleep_us = max(0, TARGET_PERIOD_US - elapsed_us)
        await asyncio.sleep_ms(time_to_sleep_us // 1000)

# ==========================================
# Main Loop
# ==========================================
async def main():
    task1 = asyncio.create_task(ble_task())
    task2 = asyncio.create_task(input_task())
    task3 = asyncio.create_task(led_task())
    await asyncio.gather(task1, task2)
            
asyncio.run(main())