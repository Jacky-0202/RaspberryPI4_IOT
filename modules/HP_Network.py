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
        """
        subprocess.run(["sudo", "systemctl", "stop", "hostapd"], check=True)
        subprocess.run(["sudo", "systemctl", "start", "NetworkManager"], check=True)

    def restart_networkmanager(self):
        """
        Restarts the NetworkManager service.
        This re-initializes network interfaces and connections.
        """
        subprocess.run(["sudo", "systemctl", "restart", "NetworkManager"], check=True)

    def connect_wifi_system_scope(self, ssid, pswd):
        """
        :param ssid: Target Wi-Fi network name (SSID).
        :param pswd: Wi-Fi password.
        """
        try:
            # 1.Ensure NetworkManager is running
            subprocess.run(["sudo", "systemctl", "start", "NetworkManager"], check=True)

            # 2.Get all saved Wi-Fi connection names
            result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
                capture_output=True, text=True, check=True
            )

            # Parse the output and filter Wi-Fi connection names
            connections = result.stdout.strip().split("\n")
            wifi_connections = [line.split(":")[0] for line in connections if "wifi" in line]

            # 3.Delete all existing Wi-Fi connections (but keep SSID passwords intact)
            for conn in wifi_connections:
                subprocess.run(["nmcli", "connection", "delete", conn], check=False)
                print(f"Deleted Wi-Fi connection: {conn}")

            # 4.Set a fixed Wi-Fi connection name (ensuring only one exists)
            conn_name = "mywifi"

            # 5.Create a new Wi-Fi connection with the specified SSID and password
            subprocess.run([
                "nmcli", "connection", "add",
                "type", "wifi",
                "ifname", "wlan0",
                "con-name", conn_name,
                "ssid", ssid,
                "802-11-wireless-security.key-mgmt", "wpa-psk",
                "wifi-sec.psk", pswd
            ], check=True)

            # 6.Activate the newly created Wi-Fi connection
            subprocess.run(["nmcli", "connection", "up", conn_name], check=True)

            print(f"Successfully connected to Wi-Fi: {ssid} (Connection Name: {conn_name})")

        except subprocess.CalledProcessError as e:
            print(f"Failed to connect to {ssid}. Error: {e}")

    def enable_captive_portal(self):
        # restart dnsmasq
        subprocess.run(["sudo", "systemctl", "restart", "dnsmasq"], check=True)
        # IP 
        subprocess.run(["sudo", "sh", "-c", "echo 1 > /proc/sys/net/ipv4/ip_forward"], check=True)
        # NAT
        subprocess.run(["sudo", "iptables", "-t", "nat", "-F"], check=True)  # clean old rule
        subprocess.run([
            "sudo", "iptables", "-t", "nat", "-A", "PREROUTING",
            "-p", "tcp", "--dport", "80",
            "-j", "DNAT", "--to-destination", "10.3.141.1:8000"
        ], check=True)
        subprocess.run(["sudo", "iptables", "-t", "nat", "-A", "POSTROUTING", "-j", "MASQUERADE"], check=True)
        print("Captive portal NAT & DNS setup complete.")

    def get_network_details(self, interface="wlan0"):
        """
        Obtains network details based on the interface type.
        - If it's a Wi-Fi interface (wlan0), it retrieves Link Quality and Signal Level using iwconfig.
        - If it's a wired Ethernet interface (eth0), it retrieves Link Detected and Speed using ethtool.
        
        Returns a dictionary:
            For Wi-Fi (wlan0):
            {
                "Interface": <str>,
                "Link Quality": <int>,
                "Signal Level": <int>
            }
            
            For Ethernet (eth0):
            {
                "Interface": <str>,
                "Link Detected": <bool>,
                "Speed": <int> (in Mbps)
            }
        
        Returns None if the interface is invalid or data cannot be retrieved.
        """
        try:
            if interface.startswith("wlan"):  # Wi-Fi interface
                result = subprocess.run(
                    ["iwconfig", interface],
                    capture_output=True,
                    text=True,
                    check=True
                )
                output = result.stdout

                # Analyzing link quality and signal levels
                match_quality = re.search(r"Link Quality=(\d+)/(\d+)", output)
                match_signal = re.search(r"Signal level=(-?\d+) dBm", output)

                if match_quality and match_signal:
                    link_quality = int(match_quality.group(1))  # Numerator (70)
                    max_quality = int(match_quality.group(2))  #  Denominator (70)
                    quality_percent = int((link_quality / max_quality) * 100)
                    signal_level = int(match_signal.group(1))

                    return {
                        "Interface": interface,
                        "Link Quality": quality_percent,
                        "Signal Level": signal_level
                    }
            
            elif interface.startswith("eth"):  # Wired network interface
                result = subprocess.run(
                    ["ethtool", interface],
                    capture_output=True,
                    text=True,
                    check=True
                )
                output = result.stdout

                # Analysis Link Detected
                match_link = re.search(r"Link detected:\s+(yes|no)", output, re.IGNORECASE)
                # Analysis Speed
                match_speed = re.search(r"Speed:\s+(\d+)Mb/s", output)

                if match_link:
                    link_detected = match_link.group(1).lower() == "yes"
                else:
                    link_detected = None

                if match_speed:
                    speed = int(match_speed.group(1))
                else:
                    speed = None

                return {
                    "Interface": interface,
                    "Link Detected": link_detected,
                    "Speed": speed
                }
            
            else:
                return None  # Unknown interface

        except subprocess.CalledProcessError:
            return None  # Unable to execute command
    
    def is_wifi_connected(self, test_url="http://google.com"):
        """Check Wi-Fi connectivity by attempting to reach a known URL."""
        try:
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            print("error", "Wi-Fi connection failed.")
        return False


import os
import signal
import uvicorn
import threading
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

        self.ap_timeout = 240
        self.start_time = None
        self.running = False

    def load_html(self):
        """
        Read an external 'main.html' file for the returned HTML content.
        Adjust the path to match your directory structure.
        """
        html_file_path = "main.html"
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
        self.running = True
        self.start_time = time.time()

        threading.Thread(target=self.monitor_timeout, daemon=True).start()

        uvicorn.run(self.app, host=self.host, port=8000)

    def monitor_timeout(self):
        """
        Continuously monitor whether AP mode has timed out
        """
        while self.running:
            elapsed_time = time.time() - self.start_time
            if elapsed_time > self.ap_timeout:
                print("AP mode times out rpi will be automatically shut down...")
                self.shutdown_server()
                time.sleep(10)
                os.system("sudo shutdown -h now") 
                break
            time.sleep(5)
            

    def shutdown_server(self):
        """
        Background task that:
          1) Waits 3 seconds to allow the HTTP response to reach the user
          2) Restarts NetworkManager
          3) Sends an interrupt signal to stop the Uvicorn server (instead of sys.exit())
        """
        self.running = False
        time.sleep(3)
        try:
            # Send SIGINT to self process to stop uvicorn.run()
            os.kill(os.getpid(), signal.SIGINT)  # Simulates Ctrl+C
        except subprocess.CalledProcessError as e:
            print(f"Failed to restart NetworkManager: {e}")

