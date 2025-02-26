import sys
from pathlib import Path
from ruamel.yaml import YAML

sys.path.append(str(Path(__file__).parent.parent / "modules"))
from HP_LogManager import LogManager
from HP_Camera import CameraController

# Initialize components
Yaml = YAML()
log_manager = LogManager()
camera = CameraController()

# Load configuration data
CONFIG_DATA = log_manager.load_config()

if __name__ == "__main__":
    try:
        # Start in default (low) mode
        camera.start()

        lens_position = CONFIG_DATA["CAMERA"].get("FOCUS_POSITION")
        if lens_position is not None:
            camera.set_focus_position(lens_position)
            print(f"Using saved focus position: {lens_position}")
        else:
            camera.set_focus_window(0.3, 0.3, 0.7, 0.7)
            lens_position = camera.auto_focus()
            CONFIG_DATA["CAMERA"]["FOCUS_POSITION"] = lens_position
            print(f"Auto-focus complete. Current Lens Position: {lens_position}")

        awb_gain_r = CONFIG_DATA["CAMERA"].get("AWB_R", None)
        awb_gain_b = CONFIG_DATA["CAMERA"].get("AWB_B", None)
        if awb_gain_r is not None and awb_gain_b is not None:
            camera.set_awb_gains(awb_gain_r, awb_gain_b)
            print(f"Using saved AWB: R={awb_gain_r}, B={awb_gain_b}")
        else:
            awb_gain_r,awb_gain_b = camera.auto_white_balance()
            print(f"Auto white balance set. AWB Gains: R={awb_gain_r}, B={awb_gain_b}")

        # Automatically adjust exposure to achieve a target brightness of 128
        target_brightness = CONFIG_DATA["CAMERA"].get("BRIGHTNESS")
        camera.auto_adjust_exposure(target_brightness=target_brightness)
        print(f"Adjusting exposure to brightness: {target_brightness}")

        # save image in high mode
        camera.save_image()

    finally:
        config_path = Path(__file__).parent / "config.yaml"
        with config_path.open("w", encoding="utf-8") as file:
            Yaml.dump(CONFIG_DATA, file)

        camera.close()



