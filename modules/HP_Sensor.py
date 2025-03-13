"""
SensorReader Module: Reads temperature, humidity, and light intensity.
"""

import time
import numpy as np
import smbus2 as smbus

# Constants for SHT20
SHT20_I2C_ADDR = 0x40               # Temp & Hum Address
LIGHT_SENSOR_ADDRESS = 0x4A
TRIGGER_TEMP_MEASURE_HOLD = 0xE3
TRIGGER_HUMD_MEASURE_HOLD = 0xE5

class SensorReader:
    """
    SensorReader: Reads temperature, humidity, and light intensity using I2C.
    """
    def __init__(self, light_bus_number=0, temphum_bus_number=1):
        """
        Initialize the temperature/humidity sensor and light sensor.
        """
        self.light_bus_number = light_bus_number
        self.temphum_bus_number = temphum_bus_number

        # Initialize I2C buses
        self.temphum_detector = smbus.SMBus(self.temphum_bus_number)
        self.lux_detector = smbus.SMBus(self.light_bus_number)

    def close_sensors(self):
        """
        Close all resources used by the sensors.
        """
        self.temphum_detector.close()
        self.lux_detector.close()

    def read_temperature(self):
        """
        Read temperature data from the SHT20 sensor.
        :return: Temperature in Celsius. Returns 0 if reading fails.
        """
        try:
            data = self.read_i2c_data(self.temphum_detector, SHT20_I2C_ADDR, TRIGGER_TEMP_MEASURE_HOLD, 2)
            if not data or len(data) < 2:  # Check if data is empty or insufficient
                return 0
            temperature = ((data[0] << 8) | data[1]) * (175.72 / 65536.0) - 46.85
            return temperature
        except:
            print("read temperature error")
            return 0

    def read_humidity(self):
        """
        Read humidity data from the SHT20 sensor.
        :return: Humidity in percentage. Returns 0 if reading fails.
        """
        try:
            data = self.read_i2c_data(self.temphum_detector, SHT20_I2C_ADDR, TRIGGER_HUMD_MEASURE_HOLD, 2)
            if not data or len(data) < 2:  # Check if data is empty or insufficient
                return 0
            humidity = ((data[0] << 8) | data[1]) * (125.0 / 65536.0) - 6.0
            return humidity
        except:
            print("read humidity error")
            return 0

    def read_light(self):
        """
        Read light intensity (lux) from the light sensor.
        :return: Light intensity in lux. Returns 0 if reading fails.
        """
        try:
            data = self.read_i2c_data(self.lux_detector, LIGHT_SENSOR_ADDRESS, 0, 4)
            if not data or len(data) < 4:  # Check if data is empty or insufficient
                return 0
            lux_value = (data[3] << 24) | (data[2] << 16) | (data[1] << 8) | data[0]
            lux = lux_value * 1.4 / 1000  # Convert raw value to lux
            return lux
        except:
            print("read light error")
            return 0


    def continuous_read(self, num_reads=10, interval=0.1):
        """
        Continuously read temperature, humidity, and light intensity.
        :param num_reads: Number of readings to take.
        :param interval: Interval between readings in seconds.
        :return: A tuple of lists (temperatures, humidities, lux_values).
        """
        temperatures = []
        humidities = []
        lux_values = []

        for _ in range(num_reads):
            temperatures.append(self.read_temperature())
            humidities.append(self.read_humidity())
            lux_values.append(self.read_light())
            time.sleep(interval)

        filtered_temp = self.filter_outliers(temperatures)
        filtered_hum = self.filter_outliers(humidities)
        filtered_lux = self.filter_outliers(lux_values)

        # Calculate average values rounded to 2 decimal places
        avg_temp = self.calculate_average(filtered_temp)
        avg_hum = self.calculate_average(filtered_hum)
        avg_lux = self.calculate_average(filtered_lux)

        # Return both filtered lists and their averages
        return avg_temp, avg_hum, avg_lux

    def filter_outliers(self, data, threshold=1.5):
        """
        Filter out outliers using the IQR method.
        :param data: List of numerical values.
        :param threshold: Multiplier for the IQR to define outlier range (default: 1.5).
        :return: Filtered list with outliers removed.
        """
        if len(data) < 4:
            print("Dataset too small for reliable outlier detection.")
            return data

        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        return [x for x in data if lower_bound <= x <= upper_bound]

    def read_i2c_data(self, bus, address, register, length):
        """
        Helper function to read I2C data.
        :param bus: SMBus instance.
        :param address: I2C address of the device.
        :param register: Register address to read from.
        :param length: Number of bytes to read.
        :return: List of read bytes.
        """
        return bus.read_i2c_block_data(address, register, length)
    
    def calculate_average(self, data):
        """
        Calculate the average of a list. If the list has one value, return that value.

        :param data: List of numerical values.
        :return: Average of the list or 0 if the list is empty.
        """
        if not data:
            return 0
        elif len(data) == 1:
            return round(data[0], 2)
        else:
            return round(sum(data) / len(data), 2)
