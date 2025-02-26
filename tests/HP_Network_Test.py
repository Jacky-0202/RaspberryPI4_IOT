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

# =================================

if __name__ == "__main__":

    while True:

        CONFIG_DATA = Log_Manager.load_config()

        # Get Wi-Fi details from config
        wifi_ssid = CONFIG_DATA["NETWORK"].get("SSID")
        wifi_password = CONFIG_DATA["NETWORK"].get("PASW")
        wifi_priority = CONFIG_DATA["NETWORK"].get("PRIORITY", False)
        network_thres = CONFIG_DATA["NETWORK"].get("NETWORK_THRES")

        # Check if Wi-Fi details are available
        if not wifi_ssid or not wifi_password:
            Rasp_Controller.start_ap_mode()
            Wifi_Gui.run_server()
            Rasp_Controller.stop_ap_mode()
            continue
    
        # If Wi-Fi priority is enabled, switch to the specified SSID
        if wifi_priority:
            Rasp_Controller.connect_wifi_system_scope(ssid=wifi_ssid, pswd=wifi_password)
        else:
            Rasp_Controller.restart_networkmanager()

        # Wait a few seconds to check the connection status
        time.sleep(20)

        # Check if connected
        if Rasp_Controller.is_wifi_connected():
            # Get Wi-Fi details after attempting to connect
            wifi_details = Rasp_Controller.get_wifi_details()
            link_quality = wifi_details["Link Quality"]
            signal_level = wifi_details["Signal Level"]

            print(f"Link Quality : {link_quality}")
            print(f"Signal Level : {signal_level}")

            if "Link Quality" in wifi_details and link_quality < network_thres:
                print("Wi-Fi connected, but signal is weak.")
            print("Wi-Fi connection successful!")
            break
        else:
            print("Wi-Fi connection failed. Restarting AP mode for new input.")
            Rasp_Controller.start_ap_mode()
            Wifi_Gui.run_server()
            Rasp_Controller.stop_ap_mode()
            continue



    print("Uploading sensor data")
    print("Uploading photos")
