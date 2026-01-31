from machine import ADC

# ====== CONFIGURATION ======
BATTERY_PIN = 26


class Battery:
    def __init__(self):
        self.adc = ADC(BATTERY_PIN)

    def read_voltage(self):
        raw_value = self.adc.read_u16()
        voltage = raw_value * (3.3 / 65535) * 2
        return voltage
