import os
import sys
from pathlib import Path

# Add the "modules" directory to the module search path
sys.path.append(str(Path(__file__).parent.parent / "modules"))

from HP_Network import RaspController, WifiConfigGui
from HP_UploadServer import DataUploader
from HP_Sensor import SensorReader

# Initialize controllers
Wifi_Gui = WifiConfigGui()
sensor_reader = SensorReader()
Rasp_Controller = RaspController()
Data_Uploader = DataUploader(location="PDS249291")

UPLOAD_DIR = "upload_files"

if __name__ == "__main__":
    try:
        temperatures, humidities, lux_values = sensor_reader.continuous_read(num_reads=10, interval=0.1)
    finally:
        sensor_reader.close_sensors()

    # Check if connected
    if Rasp_Controller.is_wifi_connected():
        # Get Wi-Fi details after attempting to connect
        wifi_details = Rasp_Controller.get_wifi_details()
        Data_Uploader.upload_sensor_data(temperatures,humidities,lux_values,wifi_details)
        Data_Uploader.compress_each_file_in_directory(UPLOAD_DIR)
        
        full_dir = Path(__file__).parent / UPLOAD_DIR
        for zip_file in full_dir.glob("*.zip"):
            response = Data_Uploader.upload_zip_file(zip_file)
            print(f"Upload result for {zip_file.name}: {response}")

    # Close the UDP socket when done
    Data_Uploader.close()
