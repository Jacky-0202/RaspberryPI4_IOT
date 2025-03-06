import os
import time
import socket
import shutil
import zipfile
import requests
import datetime
from pathlib import Path
from gpiozero import CPUTemperature

class DataUploader:
    def __init__(self, 
                 version_name="PDS_V1",
                 location="Hipoint_GH",
                 SensorReader=None):
        """
        Initialize SensorUploader.

        :param version_name: Version identifier.
        :param location: Device location.
        """
        self.version_name = version_name
        self.location = location

        # Server and upload settings
        self.server_ip = "59.125.195.194"
        self.base_url = "http://59.125.195.194:80"
        self.server_udp_port = 8000

        # CPU temperature and sensor reader
        self.cpu_manager = CPUTemperature()
        self.sensor_reader = SensorReader()

        # Reusable UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def get_disk_space(self):
        """
        Retrieve available disk space from the '/' mount point.

        :return: Available disk space as a string.
        """
        df = os.popen("df -h /")
        lines = df.readlines()
        return lines[1].split()[3] if len(lines) > 1 else "N/A"

    def upload_sensor_data(self,temp,hum,lux,wifi_details):
        """
        Upload sensor data (temperature, humidity, and light intensity) to the server via UDP.
        Wi-Fi and network details are optionally retrieved from the WifiInfo instance.
        """
        link_quality = wifi_details.get("Link Quality", 0)
        signal_level = wifi_details.get("Signal Level", 0)

        cpu_temp = round(self.cpu_manager.temperature, 2)
        disk_space = self.get_disk_space()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")

        packets = [
            f"PD:ENVI:{timestamp}:1:T:{temp}:{self.location}_GH:0:{link_quality}:{signal_level}:{cpu_temp}:{disk_space}:",
            f"PD:ENVI:{timestamp}:1:H:{hum}:{self.location}_GH:0:{link_quality}:{signal_level}:{cpu_temp}:{disk_space}:",
            f"PD:ENVI:{timestamp}:1:L:{lux}:{self.location}_GH:0:{link_quality}:{signal_level}:{cpu_temp}:{disk_space}:",
        ]

        try:
            for packet in packets:
                self.sock.sendto(packet.encode(), (self.server_ip, self.server_udp_port))
                time.sleep(0.2)
            print("[UDP] Successfully sent sensor data:")
            for packet in packets:
                print(f"Sent: {packet}")
        except Exception as e:
            print(f"[UDP] Error sending sensor data: {e}")

    def compress_each_file_in_directory(self, upload_dir):
        """
        Read all files and folders inside `upload_dir` and compress each into a separate .zip file.
        Removes the file extension from the zip file name.
        :param upload_dir: The directory containing files and folders to compress.
        """
        # Ensure the directory exists
        if not os.path.exists(upload_dir):
            print("The specified directory does not exist!")
            return

        # Get all files and folders inside `upload_dir`
        items = os.listdir(upload_dir)

        for item in items:
            item_path = os.path.join(upload_dir, item)  # Get the full path of the item
            item_name_without_ext = os.path.splitext(item)[0]  # Remove file extension
            
            zip_filename = os.path.join(upload_dir, f"{item_name_without_ext}.zip")  # Name for the .zip file

            if os.path.isdir(item_path):  
                # Compress directories
                shutil.make_archive(zip_filename[:-4], 'zip', item_path)
                print(f"Compressed folder: {item_path} -> {zip_filename}")

            elif os.path.isfile(item_path):  
                # Compress individual files correctly
                with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(item_path, arcname=item)  # Store file inside .zip with its original name
                print(f"Compressed file: {item_path} -> {zip_filename}")

    def upload_zip_file(self, file_path, timeout=300):
        """
        Upload a ZIP file (e.g., image archive) to the server using HTTP multipart/form-data.

        :param image_path: Path to the ZIP file.
        :param timeout: Timeout for the HTTP request (in seconds).
        :return: Server response text or an error message.
        """
        url = f"{self.base_url}/ipm_web/PEST_IMAGES/RX_IMG.php?node=1&location={self.location}_GH_1"

        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return "ERROR: File not found"

        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(url, files=files, timeout=timeout)

            if response.status_code == 200:
                print(f"[HTTP] Image upload response: {response.text}")
                return response.text
            else:
                return f"ERROR: Status {response.status_code}"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def clean_upload_files(self, upload_dir):
        """
        Deletes all files and directories in the upload directory except the "LOG" folder.
        
        :param upload_dir: The path to the upload directory (e.g., "upload_files").
        """
        for item in os.listdir(upload_dir):
            item_path = os.path.join(upload_dir, item)

            # Skip the "LOG" directory (do not delete it)
            if os.path.isdir(item_path) and item == "LOG":
                print(f"Skipping LOG directory: {item_path}")
                continue

            # If it's a file, delete it
            if os.path.isfile(item_path):
                os.remove(item_path)
                print(f"Deleted file: {item_path}")

            # If it's a directory (excluding "LOG"), delete it
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                print(f"Deleted directory: {item_path}")


    def close(self):
        """
        Close the UDP socket.
        """
        self.sock.close()
        print("[UDP] Socket closed.")
