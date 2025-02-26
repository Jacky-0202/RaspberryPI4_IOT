"""
File: main.py
Author: Jacky
Date: 2025/2/14
Version: PDS_WIFI_V1
"""

# ================================
# Import required modules
# ================================

import os
import time
from pathlib import Path
from ruamel.yaml import YAML
from datetime import datetime

from modules.HP_Network import RaspController, WifiConfigGui
from modules.HP_LogManager import LogManager
from modules.HP_Camera import CameraController
from modules.HP_Sensor import SensorReader
from modules.HP_UploadServer import DataUploader

# wait for 90 seconds 
time.sleep(90)

# ================================
# Initialize controllers
# ================================

# Network and system controllers
Rasp_Controller = RaspController()
Wifi_Gui = WifiConfigGui()

# Camera and sensor controllers
Rasp_Camera = CameraController()
Sensor_Reader = SensorReader()

# Log manager and configuration handler
Log_Manager = LogManager()
Yaml = YAML()

# Directory for storing upload files
UPLOAD_DIR = "upload_files"

# Load configuration file
CONFIG_DATA = Log_Manager.load_config()
PDS_ID = CONFIG_DATA["CONFIG"].get("PDS_ID")

# Initialize the data uploader with the device ID
Data_Uploader = DataUploader(location=PDS_ID,SensorReader=SensorReader)

# Set the execution time
EXECUTION_HOURS = CONFIG_DATA["RPI"]["EXECUTION_HOURS"]
PDS_MODE = CONFIG_DATA["CONFIG"]["PDS_MODE"]


# ================================
# Wi-Fi Configuration & Connection
# ================================

if __name__ == "__main__":

    while PDS_MODE == "WIFI":
        # Reload configuration data before each attempt
        CONFIG_DATA = Log_Manager.load_config()

        Log_Manager.log_message("info", "N01", "Entering network parameter input phase")
        print("Entering network parameter input phase")

        # Retrieve Wi-Fi details from configuration file
        wifi_ssid = CONFIG_DATA["NETWORK"].get("SSID")
        wifi_password = CONFIG_DATA["NETWORK"].get("PASW")
        wifi_priority = CONFIG_DATA["NETWORK"].get("PRIORITY", False)
        network_thres = CONFIG_DATA["NETWORK"].get("NETWORK_THRES")

        # Check if Wi-Fi credentials exist
        if not wifi_ssid or not wifi_password:
            Log_Manager.log_message("info", "N02", "No SSID or password recorded")
            Rasp_Controller.start_ap_mode()
            Wifi_Gui.run_server()
            Rasp_Controller.stop_ap_mode()
            continue  # Restart loop after user input

        # If Wi-Fi priority is enabled, attempt to connect to the specified SSID
        if wifi_priority:
            Rasp_Controller.connect_wifi_system_scope(ssid=wifi_ssid, pswd=wifi_password)
            Log_Manager.log_message("info", "N03", "Enabling network priority")
        else:
            Rasp_Controller.restart_networkmanager()
            Log_Manager.log_message("info", "N04", "Automatically searching for available networks")

        # Wait for 20 seconds to ensure network stability
        time.sleep(20)

        # Check if the system is successfully connected to Wi-Fi
        if Rasp_Controller.is_wifi_connected():
            # Retrieve updated Wi-Fi details
            wifi_details = Rasp_Controller.get_wifi_details()
            link_quality = wifi_details["Link Quality"]
            signal_level = wifi_details["Signal Level"]

            # If the signal strength is below the configured threshold, notify the user
            if "Link Quality" in wifi_details and link_quality < network_thres:
                Log_Manager.log_message("info", "N05", "Network detected, but signal is unstable")
                print("Network detected, but signal is unstable")

            Log_Manager.log_message("info", "N06", "Network connection successful")
            break  # Exit loop when successfully connected
        else:
            Log_Manager.log_message("error", "N100", "Unable to connect to the Internet")
            Rasp_Controller.start_ap_mode()
            Wifi_Gui.run_server()
            Rasp_Controller.stop_ap_mode()
            continue  # Restart the loop for user input

# ================================
# Camera Initialization & Image Capture
# ================================

    if Rasp_Controller.is_wifi_connected():
        # Set RTC (synchronize time)
        Log_Manager.sync_rtc()
        current_hour = datetime.now().hour

        if current_hour in EXECUTION_HOURS:
            try:
                # Start camera in default (low) mode
                Rasp_Camera.start()
                Log_Manager.log_message("info", "C01", "Camera started successfully")
                print("Camera started successfully")

                # Retrieve saved focus position or perform auto-focus
                lens_position = CONFIG_DATA["CAMERA"].get("FOCUS_POSITION")
                if lens_position is not None:
                    Rasp_Camera.set_focus_position(lens_position)
                    Log_Manager.log_message("info", "C02", "Using saved camera focus distance parameter")
                    print(f"Using saved focus position: {lens_position}")
                else:
                    # Define focus region (center 40%)
                    Rasp_Camera.set_focus_window(0.3, 0.3, 0.7, 0.7)
                    lens_position = Rasp_Camera.auto_focus()
                    CONFIG_DATA["CAMERA"]["FOCUS_POSITION"] = lens_position
                    Log_Manager.log_message("info", "C03", f"Saving camera focus distance parameter {lens_position}")
                    print(f"Auto-focus complete. Current Lens Position: {lens_position}")

                # Retrieve saved white balance gains or perform auto white balance
                awb_gain_r = CONFIG_DATA["CAMERA"].get("AWB_R")
                awb_gain_b = CONFIG_DATA["CAMERA"].get("AWB_B")
                if awb_gain_r is not None and awb_gain_b is not None:
                    Rasp_Camera.set_awb_gains(awb_gain_r, awb_gain_b)
                    Log_Manager.log_message("info", "C04", "Using saved white balance parameters")
                    print(f"Using saved AWB: R={awb_gain_r}, B={awb_gain_b}")
                else:
                    result = Rasp_Camera.auto_white_balance()
                    if result:
                        awb_gain_r, awb_gain_b = result
                        CONFIG_DATA["CAMERA"]["AWB_R"] = awb_gain_r
                        CONFIG_DATA["CAMERA"]["AWB_B"] = awb_gain_b
                        Log_Manager.log_message("info", "C05", "Saving white balance parameters")
                        print(f"Auto white balance set. AWB Gains: R={awb_gain_r}, B={awb_gain_b}")

                    else:
                        print("Failed to get AWB gains.")
                        Log_Manager.log_message("error", "C09", "Failed to get AWB gains.")

                # Adjust exposure based on configured target brightness
                target_brightness = CONFIG_DATA["CAMERA"].get("BRIGHTNESS")
                Rasp_Camera.auto_adjust_exposure(target_brightness=target_brightness)
                Log_Manager.log_message("info", "C06", "Auto exposure adjustment completed")
                print(f"Adjusting exposure to brightness: {target_brightness}")

                # Capture and save an image
                Rasp_Camera.save_image()
                Log_Manager.log_message("info", "C07", "Image successfully saved")

            finally:
                # Save the updated configuration back to the file
                config_path = Path(__file__).parent / "config.yaml"
                with config_path.open("w", encoding="utf-8") as file:
                    Yaml.dump(CONFIG_DATA, file)
                Log_Manager.log_message("info", "D01", "Configuration file saved")

                # Close the camera
                Rasp_Camera.close()
                Log_Manager.log_message("info", "C08", "Camera closed")

# ================================
# Sensor Data Collection & Image(.zip) Upload
# ================================

        try:
            # Collect sensor data
            temperatures, humidities, lux_values = Sensor_Reader.continuous_read(num_reads=10, interval=0.1)
            Log_Manager.log_message("info", "S01", "Successfully recorded sensor data")
            print("Successfully recorded sensor data")

            # Retrieve updated Wi-Fi details
            wifi_details = Rasp_Controller.get_wifi_details()
            Log_Manager.log_message("info", "N08", "Reading network signal strength")

            # Upload sensor data to the server
            Data_Uploader.upload_sensor_data(temperatures, humidities, lux_values, wifi_details)
            Log_Manager.log_message("info", "S02", "Using saved camera focus distance parameter")

            # Compress all files in the upload directory
            Data_Uploader.compress_each_file_in_directory(UPLOAD_DIR)
            Log_Manager.log_message("info", "D02", "Compressing files for upload (.zip)")

            # Upload all `.zip` files from the directory
            full_dir = Path(__file__).parent / UPLOAD_DIR
            for zip_file in full_dir.glob("*.zip"):
                response = Data_Uploader.upload_zip_file(zip_file)
                print(f"Upload result for {zip_file.name}: {response}")
            Log_Manager.log_message("info", "N09", "Successfully uploaded compressed file")
                
            Data_Uploader.clean_upload_files(full_dir)
            print("Already clean zip and image")
            Log_Manager.log_message("info", "D02", "Already clean zip and image")
                

        finally:
            # Close sensors and network connections
            Sensor_Reader.close_sensors()
            Log_Manager.log_message("info", "S03", "Sensor function disabled")
            Data_Uploader.close()
            Log_Manager.log_message("info", "N10", "Upload function disabled")

    else:
        print("Unable to connect to the Internet")
        Log_Manager.log_message("error", "N100", "Unable to connect to the Internet")
# ================================
# Shutdown PDS
# ================================

    print("Wait for 180 second...") 
    time.sleep(180)
    os.system("sudo shutdown -h now")
