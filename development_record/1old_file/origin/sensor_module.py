import os
import sys
import board
import busio
import glob
import time
import math
import random
import pandas as pd
import numpy as np
import time
from collections import deque
from adafruit_ina219 import INA219

latest_soh = 0.0
last_soh_update = 0

i2c = busio.I2C(board.SCL, board.SDA)

ina219 = INA219(i2c)

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

sensor_data = {
    "temp": 0.0,
    "volt": 0.0,
    "curr": 0.0,
    "percent": 0,
    "health":0,
}


def initialize_ina219():
    """Initialize INA219 sensor."""
    i2c = busio.I2C(board.SCL, board.SDA)
    try:
        sensor = INA219(i2c)
        print("INA219 Initialized Successfully!")
        return sensor
    except Exception as e:
        print(f"INA219 Initialization Error: {e}")
        return None  # Return None if initialization fails


def update_battery_percentage(voltage, prev_percent):
    """Smooth battery percentage calculation"""
    estimated_percent = estimate_battery_percentage(voltage)
    
    smoothed_percent = (prev_percent * 0.9) + (estimated_percent * 0.1)

    return round(smoothed_percent)


def read_temp_raw():
    with open(device_file, 'r') as f:
        return f.readlines()

def read_temp_c():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c
    return None


def estimate_battery_percentage(voltage):
    if voltage >= 4.2:
        return 100
    elif voltage >= 3.8:
        return round(80 + ((voltage - 3.8) * 20 / 0.4))  # 3.8V~4.2V -> 80~100%
    elif voltage >= 3.5:
        return round(50 + ((voltage - 3.5) * 30 / 0.3))  # 3.5V~3.8V -> 50~80%
    elif voltage >= 3.3:
        return round(20 + ((voltage - 3.3) * 30 / 0.2))  # 3.3V~3.5V -> 20~50%
    else:
        return max(0, round((voltage - 3.0) * 20 / 0.3))  # 3.0V~3.3V -> 0~20%


def save_sensor_data_to_csv(sensor_data, file_path="realtime_sensor_log.csv"):
    if not os.path.exists(file_path):
        sensor_data.to_csv(file_path, index=False)
    else:
        sensor_data.to_csv(file_path, mode='a', header=False, index=False)


class SOHFilter:
    def __init__(self, max_history=5, max_change=3.0):
        self.history = deque(maxlen=max_history)
        self.prev_soh = None
        self.max_change = max_change

    def update(self, soh_value):
        if self.prev_soh is not None:
            if abs(soh_value - self.prev_soh) > self.max_change:
                soh_value = self.prev_soh

        self.history.append(soh_value)
        smoothed_soh = sum(self.history) / len(self.history)
        self.prev_soh = smoothed_soh

        return smoothed_soh

def run_realtime_soh_monitoring(voltage, current, temperature):
    base_data = pd.read_csv("Battery_Data.csv")
    battery_47 = base_data[base_data['battery_id'] == 47].copy()
    battery_47.dropna(inplace=True)
    Rct_0 = battery_47['Rct'].iloc[0]
    Re_0 = battery_47['Re'].iloc[0]

    soh_filter = SOHFilter(max_history=5, max_change=3.0)

    if current == 0:
        current = 0.001

    Re_now = voltage / current
    Rct_now = (voltage - 3.0) / current

    soh_re = Re_0 / Re_now
    soh_rct = Rct_0 / Rct_now
    soh_est = 0.5 * (soh_re + soh_rct) * 100
    soh_est = max(min(soh_est, 100), 0)

    filtered_soh = soh_filter.update(soh_est)

    soh_data = pd.DataFrame([{
        "ambient_temperature": temperature,
        "Re": Re_now,
        "Rct": Rct_now,
        "SOH": filtered_soh
    }])

    save_sensor_data_to_csv(soh_data)
    return filtered_soh


def read_sensor_data():
    global latest_soh, last_soh_update
    
    try:
        voltage = ina219.bus_voltage + (ina219.shunt_voltage / 1000)
        current = ina219.current
        temperature = read_temp_c()
        percent = estimate_battery_percentage(voltage)
        
        now = time.time()
        if now - last_soh_update >= 5:
            latest_soh = run_realtime_soh_monitoring(voltage, current, temperature)
            last_soh_update = now

        sensor_data["volt"] = voltage
        sensor_data["curr"] = current
        sensor_data["temp"] = temperature
        sensor_data["percent"] = percent
        sensor_data["health"] = latest_soh
        
    except Exception as e:
        print("reading error:", e)

    return sensor_data

def get_sensor_data():
    return sensor_data
