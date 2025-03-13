"""
File: main.py
Author: Jacky
Date: 2025/2/14
Version: PDS_V1
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

# wait for 10 seconds 
print("wait for 10 seconds ")
time.sleep(10)

# ================================
# Initialize controllers
# ================================

# Log manager and configuration handler
Log_Manager = LogManager()
Yaml = YAML()

# Directory for storing upload files
UPLOAD_DIR = "upload_files"

# Load configuration file
CONFIG_DATA = Log_Manager.load_config()
PDS_ID = CONFIG_DATA["CONFIG"].get("PDS_ID")
PDS_MODE = CONFIG_DATA["CONFIG"].get("PDS_MODE")
EXECUTION_HOURS = CONFIG_DATA["RPI"].get("EXECUTION_HOURS")
NETWORK_THRES = CONFIG_DATA["NETWORK"].get("NETWORK_THRES")

# Network and system controllers
Rasp_Controller = RaspController()
Wifi_Gui = WifiConfigGui()

# Camera and sensor controllers
Rasp_Camera = CameraController()
Sensor_Reader = SensorReader()

# Initialize the data uploader with the device ID
Data_Uploader = DataUploader(location=PDS_ID,SensorReader=SensorReader)

# ================================
# Wi-Fi Configuration & Connection
# ================================


if __name__ == "__main__":

    while PDS_MODE == "WIFI":
        # Reload configuration data before each attempt
        CONFIG_DATA = Log_Manager.load_config()

        print("Entering network parameter input phase")
        Log_Manager.log_message("info", "M00", "Entering network parameter input phase")

        # Retrieve Wi-Fi details from configuration file
        wifi_ssid = CONFIG_DATA["NETWORK"].get("SSID")
        wifi_password = CONFIG_DATA["NETWORK"].get("PASW")
        wifi_priority = CONFIG_DATA["NETWORK"].get("PRIORITY", False)

        # Check if Wi-Fi credentials not exist
        if not wifi_ssid or not wifi_password:
            Log_Manager.log_message("info", "M00", "No SSID or password recorded")
            Rasp_Controller.start_ap_mode()
            Wifi_Gui.run_server()
            Rasp_Controller.stop_ap_mode()
            continue  # Restart loop after user input

        # If Wi-Fi priority is enabled, attempt to connect to the specified SSID
        if wifi_priority:
            Rasp_Controller.connect_wifi_system_scope(ssid=wifi_ssid, pswd=wifi_password)
            Log_Manager.log_message("info", "M00", "Enabling network priority")
        else:
            Rasp_Controller.restart_networkmanager()
            Log_Manager.log_message("info", "M00", "Automatically searching for available networks")

        # Wait for 20 seconds to ensure network stability
        time.sleep(20)

        # Check if the system is successfully connected to Wi-Fi
        if Rasp_Controller.is_wifi_connected():
            Log_Manager.log_message("info", "M00", "Network connection successful")
            break  # Exit loop when successfully connected
        else:
            Log_Manager.log_message("error", "E00", "Unable to connect to the Internet")
            Rasp_Controller.start_ap_mode()
            Wifi_Gui.run_server()
            Rasp_Controller.stop_ap_mode()
            continue  # Restart the loop for user input

# # ================================
# # Camera Initialization & Image Capture
# # ================================

    if Rasp_Controller.is_wifi_connected():

        current_hour = datetime.now().hour

        Log_Manager.log_message("info", "M00", "Network connection successful")

        if current_hour in EXECUTION_HOURS and Rasp_Camera.picam2 is not None:
            try:
                # Start camera in default (low) mode
                Rasp_Camera.start()
                print("Camera started successfully")
                Log_Manager.log_message("info", "M00", "Camera started successfully")

                # Retrieve saved focus position or perform auto-focus
                lens_position = CONFIG_DATA["CAMERA"].get("FOCUS_POSITION")
                if lens_position is not None:
                    Rasp_Camera.set_focus_position(lens_position)
                    Log_Manager.log_message("info", "M00", f"Using saved camera focus position: {lens_position}")
                    print(f"Using saved focus position: {lens_position}")
                else:
                    # Define focus region (center 40%)
                    Rasp_Camera.set_focus_window(0.3, 0.3, 0.7, 0.7)
                    lens_position = Rasp_Camera.auto_focus()
                    CONFIG_DATA["CAMERA"]["FOCUS_POSITION"] = lens_position
                    Log_Manager.log_message("info", "M00", f"Saving camera focus distance parameter {lens_position}")
                    print(f"Auto-focus complete. Current Lens Position: {lens_position}")

                # Retrieve saved white balance gains or perform auto white balance
                awb_gain_r = CONFIG_DATA["CAMERA"].get("AWB_R")
                awb_gain_b = CONFIG_DATA["CAMERA"].get("AWB_B")
                if awb_gain_r is not None and awb_gain_b is not None:
                    Rasp_Camera.set_awb_gains(awb_gain_r, awb_gain_b)
                    Log_Manager.log_message("info", "M00", f"Using saved white balance parameters R={awb_gain_r}, B={awb_gain_b}")
                    print(f"Using saved AWB: R={awb_gain_r}, B={awb_gain_b}")
                else:
                    result = Rasp_Camera.auto_white_balance()
                    if result:
                        awb_gain_r, awb_gain_b = result
                        CONFIG_DATA["CAMERA"]["AWB_R"] = awb_gain_r
                        CONFIG_DATA["CAMERA"]["AWB_B"] = awb_gain_b
                        Log_Manager.log_message("info", "C05", f"Saving white balance parameters R={awb_gain_r}, B={awb_gain_b}")
                        print(f"White balance set. AWB Gains: R={awb_gain_r}, B={awb_gain_b}")

                    else:
                        print("Failed to get AWB gains.")
                        Log_Manager.log_message("error", "C09", "Failed to get AWB gains.")

                # Adjust exposure based on configured target brightness
                target_brightness = CONFIG_DATA["CAMERA"].get("BRIGHTNESS")
                Rasp_Camera.auto_adjust_exposure(target_brightness=target_brightness)
                Log_Manager.log_message("info", "M00", "Auto exposure adjustment completed")
                print(f"Adjusting exposure to brightness: {target_brightness}")

                # Capture and save an image
                save_success_flag = Rasp_Camera.save_image()
                if save_success_flag:
                    Log_Manager.log_message("info", "M00", "Image successfully saved")
                else:
                    Log_Manager.log_message("error", "E00", "Image save error")

                
            finally:
                # Save the updated configuration back to the file
                Log_Manager.save_config(CONFIG_DATA)
                Log_Manager.log_message("info", "M00", "Configuration file saved")

                # Close the camera
                Rasp_Camera.close()
                Log_Manager.log_message("info", "M00", "Camera closed")
                
        else:
            Log_Manager.log_message("error", "M00", "Camera can't open")




# ================================
# Sensor Data Collection & Image(.zip) Upload
# ================================

        # Define WI-FI Object
        wifi_details = None

        if PDS_MODE == "WIFI":
            # Retrieve updated Wi-Fi details
            wifi_details = Rasp_Controller.get_network_details("wlan0")
            link_quality = wifi_details["Link Quality"]

            # If the signal strength is below the configured threshold, notify the user
            if "Link Quality" in wifi_details and link_quality < NETWORK_THRES:
                print("Network detected, but signal is unstable")
                Log_Manager.log_message("info", "M00", f"Network detected, but signal is unstable. Link Quality : {link_quality} ")
                

        else:
            # Retrieve updated Wi-Fi details
            wifi_details = Rasp_Controller.get_network_details("eth0")

        try:
            # Collect sensor data
            temperatures, humidities, lux_values = Sensor_Reader.continuous_read(num_reads=10, interval=0.1)

            if temperatures == 0 or humidities == 0:
                Log_Manager.log_message("error", "E00", "Failed to record temperature or humidity data")

            if lux_values == 0:
                Log_Manager.log_message("error", "E00", "Failed to record lux data")

            if temperatures != 0 and humidities != 0 and lux_values != 0:
                Log_Manager.log_message("info", "M00", "Successfully recorded sensor data")
            
            Log_Manager.log_message("info", "M00", "Reading network signal strength")

            # Upload sensor data to the server
            Data_Uploader.upload_sensor_data(temperatures, humidities, lux_values, wifi_details)
            Log_Manager.log_message("info", "M00", "Already upload sensor data")

            # Compress all files in the upload directory
            Data_Uploader.compress_each_file_in_directory(UPLOAD_DIR)
            Log_Manager.log_message("info", "M00", "Compressing files for upload (.zip)")

            # wait for record log
            time.sleep(1)

            # Upload all `.zip` files from the directory
            full_dir = Path(__file__).parent / UPLOAD_DIR
            for zip_file in full_dir.glob("*.zip"):
                response = Data_Uploader.upload_zip_file(zip_file)
                print(f"Upload result for {zip_file.name}: {response}")
            Log_Manager.log_message("info", "M00", "Successfully uploaded compressed file")
                
            Data_Uploader.clean_upload_files(full_dir)
            print("Already clean zip and image")
            Log_Manager.log_message("info", "M00", "Already clean zip and image")
                

        finally:
            # Close sensors and network connections
            Sensor_Reader.close_sensors()
            Log_Manager.log_message("info", "M00", "Sensor function disabled")
            Data_Uploader.close()
            Log_Manager.log_message("info", "M00", "Upload function disabled")

            # Set RTC (synchronize time)
            Log_Manager.sync_rtc()

    else:
        print("Unable to connect to the Internet")
        Log_Manager.log_message("error", "E00", "Unable to connect to the Internet")

# ================================
# Shutdown PDS
# ================================

    print("Wait for 180 second...") 
    time.sleep(180)
    os.system("sudo shutdown -h now")