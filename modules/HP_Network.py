import re
import time
import requests
import subprocess

class RaspController:
    def __init__(self):
        """
        Initializes the RaspController.
        Assumes usage of NetworkManager and hostapd for managing AP mode
        on a Linux environment (e.g., Raspberry Pi).
        """
        print("RaspAPController initialized")

    def start_ap_mode(self):
        """
        Stops NetworkManager, assigns a static IP to wlan0,
        and restarts hostapd to enable AP (Access Point) mode.
        
        Steps performed:
        1. systemctl stop NetworkManager
        2. ifconfig wlan0 10.3.141.1 netmask 255.255.255.0 up
        3. systemctl restart hostapd
        4. auto display html on other divice
        """
        subprocess.run(["sudo", "systemctl", "stop", "NetworkManager"], check=True)
        subprocess.run(
            ["sudo", "ifconfig", "wlan0", "10.3.141.1", "netmask", "255.255.255.0", "up"],
            check=True
        )
        subprocess.run(["sudo", "systemctl", "restart", "hostapd"], check=True)

        self.enable_captive_portal()

    def stop_ap_mode(self):
        """
        Stops hostapd (AP mode) and restarts NetworkManager.
        
        Steps performed:
        1. systemctl stop hostapd
        2. systemctl restart NetworkManager
        """
        subprocess.run(["sudo", "systemctl", "stop", "hostapd"], check=True)
        subprocess.run(["sudo", "systemctl", "start", "NetworkManager"], check=True)

    def restart_networkmanager(self):
        """
        Restarts the NetworkManager service.
        This re-initializes network interfaces and connections.
        
        Step performed:
        1. systemctl restart NetworkManager
        """
        subprocess.run(["sudo", "systemctl", "restart", "NetworkManager"], check=True)

    def connect_wifi_system_scope(self, ssid, pswd, conn_name="mywifi"):
        """
        Create or update a system-scoped Wi-Fi connection for the specified SSID
        (via nmcli) without triggering any desktop pop-ups.
        """
        try:
            # 1) Remove old connection if it exists (avoid conflicts)
            subprocess.run(["sudo", "systemctl", "start", "NetworkManager"], check=True)
            subprocess.run(["nmcli", "connection", "delete", conn_name], check=False)

            # 2) Create a new system-scoped Wi-Fi connection
            subprocess.run([
                "nmcli", "connection", "add",
                "type", "wifi",
                "ifname", "wlan0",
                "con-name", conn_name,
                "ssid", ssid,
                "802-11-wireless-security.key-mgmt", "wpa-psk",
                "wifi-sec.psk", pswd
            ], check=True)

            # 3) Bring up the connection
            subprocess.run(["nmcli", "connection", "up", "mywifi"], check=True)

        except subprocess.CalledProcessError as e:
            print(f"Failed to connect to {ssid}. Error: {e}")

    def enable_captive_portal(self):
        # restart dnsmasq
        subprocess.run(["sudo", "systemctl", "restart", "dnsmasq"], check=True)
        # IP 
        subprocess.run(["sudo", "sh", "-c", "echo 1 > /proc/sys/net/ipv4/ip_forward"], check=True)
        # NAT
        subprocess.run(["sudo", "iptables", "-t", "nat", "-F"], check=True)  # 清空舊規則
        subprocess.run([
            "sudo", "iptables", "-t", "nat", "-A", "PREROUTING",
            "-p", "tcp", "--dport", "80",
            "-j", "DNAT", "--to-destination", "10.3.141.1:8000"
        ], check=True)
        subprocess.run(["sudo", "iptables", "-t", "nat", "-A", "POSTROUTING", "-j", "MASQUERADE"], check=True)
        print("Captive portal NAT & DNS setup complete.")

    def get_wifi_details(self):
        """
        Obtains Wi-Fi details (Link Quality and Signal Level) from iwconfig for wlan0.
        Returns a dictionary containing:
            {
                "Link Quality": <int>,
                "Signal Level": <int>
            }
        or None if the information cannot be parsed.
        """
        try:
            result = subprocess.run(
                ["iwconfig", "wlan0"],
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout

            # Parse Link Quality
            match_quality = re.search(r"Link Quality=(\d+)/(\d+)", output)
            # Parse Signal Level
            match_signal = re.search(r"Signal level=(-?\d+) dBm", output)

            if match_quality and match_signal:
                # e.g., "Link Quality=54/70" => link_quality=54
                link_quality = int(match_quality.group(1))
                # e.g., "Signal level=-45 dBm" => signal_level=-45
                signal_level = int(match_signal.group(1))
                return {
                    "Link Quality": link_quality,
                    "Signal Level": signal_level
                }
            return None

        except subprocess.CalledProcessError:
            return None

    def is_wifi_connected(self, test_url="http://google.com"):
        """Check Wi-Fi connectivity by attempting to reach a known URL."""
        try:
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            self.log("error", "Wi-Fi connection failed.")
        return False


import os
import sys
import time
import signal
import uvicorn
from ruamel.yaml import YAML
from fastapi import FastAPI, Form, BackgroundTasks
from fastapi.responses import HTMLResponse

class WifiConfigGui:
    def __init__(self, host: str = "10.3.141.1"):
        """
        Initialize the FastAPI app and set up the API routes.
        """
        self.host = host
        self.app = FastAPI()
        self.setup_routes()
        self.html_content = self.load_html()

    def load_html(self):
        """
        Read an external 'main.html' file for the returned HTML content.
        Adjust the path to match your directory structure.
        """
        html_file_path = os.path.join(os.path.dirname(__file__), "main.html")
        with open(html_file_path, "r", encoding="utf-8") as f:
            return f.read()
        
    def setup_routes(self):
        """
        Set up FastAPI routes for rendering the Wi-Fi form and handling submission.
        """
        @self.app.get("/", response_class=HTMLResponse)
        async def read_root():
            return self.html_content

        @self.app.post("/configure_wifi/")
        async def configure_wifi(
            ssid: str = Form(...),
            password: str = Form(...),
            background_tasks: BackgroundTasks = None
        ):
            result = self.update_network_config(ssid, password)
            # If the update is successful, schedule a background task to shut down Uvicorn
            if result.get("message") == "Network parameters sent successfully!":
                if background_tasks:
                    background_tasks.add_task(self.shutdown_server)
            return result

        #
        # NEW ROUTE #1: Return the current PRIORITY state
        #
        @self.app.get("/get_priority")
        async def get_priority():
            """
            Reads config.yaml and returns the current PRIORITY (true/false).
            """
            yaml_obj = YAML()
            yaml_obj.default_flow_style = False

            try:
                with open("config.yaml", "r", encoding="utf-8") as f:
                    config = yaml_obj.load(f)
            except FileNotFoundError:
                return {"PRIORITY": False, "error": "config.yaml not found"}

            # Safely handle if 'PRIORITY' doesn't exist
            priority_state = config.get("NETWORK", {}).get("PRIORITY", False)
            return {"PRIORITY": priority_state}

        #
        # NEW ROUTE #2: Toggle the PRIORITY state
        #
        @self.app.post("/toggle_priority")
        async def toggle_priority():
            """
            Reads config.yaml, flips the 'PRIORITY' boolean,
            writes it back, and returns the new state.
            """
            yaml_obj = YAML()
            yaml_obj.default_flow_style = False
            
            try:
                with open("config.yaml", "r", encoding="utf-8") as f:
                    config = yaml_obj.load(f)
            except FileNotFoundError:
                return {"PRIORITY": False, "error": "config.yaml not found"}

            if "NETWORK" not in config:
                config["NETWORK"] = {}

            current_value = config["NETWORK"].get("PRIORITY", False)
            # Flip the boolean
            new_value = not current_value
            config["NETWORK"]["PRIORITY"] = new_value

            # Write back to config.yaml
            try:
                with open("config.yaml", "w", encoding="utf-8") as f:
                    yaml_obj.dump(config, f)
            except Exception as e:
                return {"PRIORITY": current_value, "error": str(e)}

            return {"PRIORITY": new_value}

        @self.app.get("/generate_204", response_class=HTMLResponse)
        async def generate_204_page():
            return self.html_content

    def update_network_config(self, new_ssid, new_password, config_file="config.yaml"):
        """
        Updates the 'SSID' and 'PASW' fields in the 'NETWORK' section
        of config.yaml using ruamel.yaml. Preserves original order and formatting.
        
        :param new_ssid: The new Wi-Fi SSID to be saved.
        :param new_password: The new Wi-Fi password to be saved.
        :param config_file: Path to the YAML config file (defaults to 'config.yaml').
        :return: A dict with either {"message": "..."} or {"error": "..."}.
        """
        yaml_obj = YAML()
        yaml_obj.default_flow_style = False  # More human-readable style

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml_obj.load(f)
        except FileNotFoundError:
            print("'config.yaml' does not exist.")
            return {"error": "'config.yaml' not found."}

        if "NETWORK" not in config:
            print("'NETWORK' section not found in config.yaml.")
            return {"error": "'NETWORK' section not found in config.yaml."}

        # Override SSID and password
        config["NETWORK"]["SSID"] = new_ssid
        config["NETWORK"]["PASW"] = new_password

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                yaml_obj.dump(config, f)
            print("Network parameters updated successfully!")
            return {"message": "Network parameters sent successfully!"}
        except Exception as e:
            print(f"Error writing to config.yaml: {e}")
            return {"error": f"Failed to update network config: {e}"}

    def run_server(self):
        """
        Start the FastAPI service on port 8000 (default).
        """
        uvicorn.run(self.app, host=self.host, port=8000)

    def shutdown_server(self):
        """
        Background task that:
          1) Waits 3 seconds to allow the HTTP response to reach the user
          2) Restarts NetworkManager
          3) Sends an interrupt signal to stop the Uvicorn server (instead of sys.exit())
        """
        time.sleep(3)
        try:
            # Send SIGINT to self process to stop uvicorn.run()
            os.kill(os.getpid(), signal.SIGINT)  # Simulates Ctrl+C
        except subprocess.CalledProcessError as e:
            print(f"Failed to restart NetworkManager: {e}")
