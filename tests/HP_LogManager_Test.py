import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "modules"))
from HP_LogManager import LogManager

# Example usage:
if __name__ == "__main__":
    # Initialize LogManager
    log_manager = LogManager()

    # Log some test messages
    log_manager.log_message("info", "P01", "System started successfully.")
    log_manager.log_message("error", "E02", "Failed to shut down properly.")
    log_manager.log_message("info", "P03", "Entering sleep mode.")

    # Set RTC (synchronize time)
    log_manager.sync_rtc()

    print(f"Messages log saved to: {log_manager.get_messages_log_path()}")
    print(f"Errors log saved to: {log_manager.get_errors_log_path()}")