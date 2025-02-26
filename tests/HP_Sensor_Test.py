import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "modules"))
from HP_Sensor import SensorReader

try:
    # Initialize SensorReader
    sensor_reader = SensorReader()
except Exception as e:
    print(f"Failed to initialize SensorReader: {e}")
    sys.exit(1)

if __name__ == "__main__":
    try:
        temperatures, humidities, lux_values = sensor_reader.continuous_read(num_reads=10, interval=0.1)
        print("Temperatures:", temperatures)
        print("Humidities:", humidities)
        print("Lux Values:", lux_values)
    finally:
        sensor_reader.close_sensors()
