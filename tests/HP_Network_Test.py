import sys
import time
from pathlib import Path
from ruamel.yaml import YAML

sys.path.append(str(Path(__file__).parent.parent / "modules"))
from HP_Network import RaspController, WifiConfigGui
from HP_LogManager import LogManager

# =================================

# Initialize controllers
Rasp_Controller = RaspController()
Wifi_Gui = WifiConfigGui()
Log_Manager = LogManager()
Yaml = YAML()

# Load configuration file
CONFIG_DATA = Log_Manager.load_config()
PDS_ID = CONFIG_DATA["CONFIG"].get("PDS_ID")
PDS_MODE = CONFIG_DATA["CONFIG"].get("PDS_MODE")
EXECUTION_HOURS = CONFIG_DATA["RPI"].get("EXECUTION_HOURS")
NETWORK_THRES = CONFIG_DATA["NETWORK"].get("NETWORK_THRES")

# =================================

# ================================
# Wi-Fi Configuration & Connection
# ================================


if __name__ == "__main__":

    while PDS_MODE == "WIFI":
        # Reload configuration data before each attempt
        CONFIG_DATA = Log_Manager.load_config()

        print("Entering network parameter input phase")

        # Retrieve Wi-Fi details from configuration file
        wifi_ssid = CONFIG_DATA["NETWORK"].get("SSID")
        wifi_password = CONFIG_DATA["NETWORK"].get("PASW")
        wifi_priority = CONFIG_DATA["NETWORK"].get("PRIORITY", False)

        # Check if Wi-Fi credentials not exist
        if not wifi_ssid or not wifi_password:
            Rasp_Controller.start_ap_mode()
            Wifi_Gui.run_server()
            Rasp_Controller.stop_ap_mode()
            continue  # Restart loop after user input

        # If Wi-Fi priority is enabled, attempt to connect to the specified SSID
        if wifi_priority:
            Rasp_Controller.connect_wifi_system_scope(ssid=wifi_ssid, pswd=wifi_password)
        else:
            Rasp_Controller.restart_networkmanager()

        # Wait for 20 seconds to ensure network stability
        time.sleep(20)

        # Check if the system is successfully connected to Wi-Fi
        if Rasp_Controller.is_wifi_connected():
            break  # Exit loop when successfully connected
        else:
            Rasp_Controller.start_ap_mode()
            Wifi_Gui.run_server()
            Rasp_Controller.stop_ap_mode()
            continue  # Restart the loop for user input
