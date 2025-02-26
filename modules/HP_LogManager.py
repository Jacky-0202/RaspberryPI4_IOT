import os
import serial
import logging
from ruamel.yaml import YAML
from datetime import datetime

class LogManager:
    """
    A class for managing log directories, loggers, and logging operations.
    """

    def __init__(self, log_dir="./upload_files/LOG"):
        """
        Initialize the LogManager by creating the log directory (if not exists)
        and setting up the handlers for 'messages.log' and 'errors.log'.
        
        :param log_dir(str): Path to the directory where log files will be stored.
        """
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

        # Paths for different log files
        self.messages_log_path = os.path.join(self.log_dir, "messages.log")
        self.errors_log_path = os.path.join(self.log_dir, "errors.log")

        # Set up messages logger
        self.messages_logger = logging.getLogger("messages_logger")
        self.messages_logger.setLevel(logging.INFO)
        messages_handler = logging.FileHandler(self.messages_log_path)
        messages_handler.setFormatter(logging.Formatter('%(message)s'))
        self.messages_logger.addHandler(messages_handler)

        # Set up errors logger
        self.errors_logger = logging.getLogger("errors_logger")
        self.errors_logger.setLevel(logging.ERROR)
        errors_handler = logging.FileHandler(self.errors_log_path)
        errors_handler.setFormatter(logging.Formatter('%(message)s'))
        self.errors_logger.addHandler(errors_handler)

        # Serial communication with the control board
        self.serial_port = serial.Serial('/dev/serial0', 115200, timeout=1)
        self.serial_port.reset_input_buffer()

    def load_config(self, config_file = "config.yaml"):
        """
        Loads a YAML configuration file using ruamel.yaml.

        :param config_file(str): The path to the YAML configuration file.
        :return: The parsed YAML data as a Python object (dict or list).
        :raises FileNotFoundError: If the config file is not found.
        """
        yaml = YAML()
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.load(f)

    def log_message(self, level, code, description):
        """
        Logs a message to the appropriate file (messages.log or errors.log),
        following a specific format: [CODE] YYYY-MM-DD DESCRIPTION
        
        :param level(str): The log level ('info' or 'error').
        :param description(str): The log description or message.
        :raises ValueError: If the code or level is invalid.
        """

        # Get current date
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Format the log entry
        log_entry = f"[{code}] {current_date} {description}"

        # Route to the correct logger based on level
        level = level.lower()
        if level == "info":
            self.messages_logger.info(log_entry)
        elif level == "error":
            self.errors_logger.error(log_entry)
        else:
            raise ValueError("Invalid log level. Use 'info' or 'error'.")

    def get_messages_log_path(self):
        """
        :return: The path to 'messages.log'.
        """
        return self.messages_log_path

    def get_errors_log_path(self) -> str:
        """
        :return: The path to 'errors.log'.
        """
        return self.errors_log_path
    
    def sync_rtc(self):
        """Synchronize RTC with Raspberry Pi time."""
        try:
            # Retrieve RTC time from control board
            self.serial_port.write(b"GET_RTC \r\n")
            rtc_time = self.serial_port.readline().decode().strip()
            
            if rtc_time.startswith("REPLY_RTC"):
                self.log_message("info", "D03", f"RTC time received: {rtc_time}")
            else:
                self.log_message("error", "D04", "Failed to retrieve RTC time from control board.")
                return

            # Set RTC to Raspberry Pi's current time
            current_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            command = f"SET_RTC {current_time}\r\n"
            self.serial_port.write(command.encode())
            rtc_time = self.serial_port.readline().decode().strip()
            
            if rtc_time.startswith("SET_RTC"):
                parsed_time = rtc_time.split(" ", 1)[1]
                self.log_message("info", "D05", f"RTC successfully synchronized. Current RTC time: {parsed_time}")
            else:
                self.log_message("error", "D100", f"Failed to set RTC time on control board. Response: {rtc_time}")
        except Exception as e:
            self.log_message("error", "D101", f"RTC synchronization error: {e}")
