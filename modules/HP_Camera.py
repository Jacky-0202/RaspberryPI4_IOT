import os
import time
import cv2
from datetime import datetime
from picamera2 import Picamera2

class CameraController:
    """
    A camera controller class that allows switching between low and high quality modes,
    including resolution and JPEG compression. Also provides basic white balance adjustment.
    """

    def __init__(self, imgs_dir="upload_files"):
        """Initialize the camera, directories, and default settings."""
        self.imgs_dir = imgs_dir
        self.picam2 = Picamera2()
        
        # Define resolutions
        self.current_resolution = (4608, 2596)
        
        # Default JPEG qualities
        self.current_jpeg_quality = 90
        
        # Current configuration
        self.started = False

        self.initial_configure_camera()  # Default to low resolution

    def initial_configure_camera(self):
        """
        Internal method to configure the camera with the current resolution and RGB888 format.
        This uses self.current_resolution and sets the camera for still capture.
        """
        config = self.picam2.create_still_configuration(
            main={
                "size": self.current_resolution,
                "format": "RGB888"
            }
        )
        self.picam2.configure(config)

    def start(self):
        """Start the camera if not already running."""
        if not self.started:
            self.picam2.start()
            self.started = True

    def close(self):
        """Stop the camera and release resources."""
        if self.started:
            self.picam2.stop()
            self.started = False
            print("Camera stopped.")
        # cv2.destroyAllWindows()
        print("Resources released.")

    def capture_frame(self):
        """
        Capture a frame and return it as a NumPy array (RGB888 format), rotated 180 degrees.
        """
        frame = self.picam2.capture_array()

        # Rotate correctly using OpenCV
        rotated_frame = cv2.rotate(frame, cv2.ROTATE_180)
        
        return rotated_frame

    def set_focus_window(self, x1, y1, x2, y2):
        """
        Set a custom AfWindows (Auto Focus Window) for precise focusing.
        Values should be in normalized coordinates (0.0 to 1.0).
        """
        if not (0.0 <= x1 < x2 <= 1.0 and 0.0 <= y1 < y2 <= 1.0):
            raise ValueError("AFWindow coordinates must be between 0.0 and 1.0")

        # Convert normalized (0.0-1.0) coordinates to absolute pixel coordinates
        width, height = self.current_resolution
        af_window_pixels = [(int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height))]

        # Check if 'AfWindows' is supported and set controls correctly
        self.picam2.set_controls({"AfWindows": af_window_pixels})
        print(f"Auto Focus Window set to: {af_window_pixels}")

    def auto_focus(self):
        """Perform an autofocus cycle."""
        try:
            self.picam2.set_controls({"AfMode": 1})
            success = self.picam2.autofocus_cycle()

            if success:
                metadata = self.picam2.capture_metadata()
                lens_position = metadata.get("LensPosition", None)
                return lens_position if lens_position is not None else "LensPosition not available in metadata."
            else:
                return "Auto-focus failed."
        except Exception as e:
            print(f"Error during auto-focus: {e}")

    def set_focus_position(self, lens_position):
        """
        Manually set the focus by specifying a lens position value.
        """
        try:
            # Disable auto-focus mode
            self.picam2.set_controls({"AfMode": 0})
            
            # Set lens position manually
            self.picam2.set_controls({"LensPosition": lens_position})
            print(f"LensPosition set to {lens_position}")
        except Exception as e:
            print(f"Error setting manual focus: {e}")


    def save_image(self, filename="NODE1"):
        """
        Capture an image using the current resolution and save it with the configured JPEG quality.
        """
        # Ensure camera is started
        if not self.started:
            self.start()

        for i in range(5):
            frame = self.capture_frame()
            time.sleep(0.3)
        
        # Generate timestamped file name
        timestamp = time.strftime("%Y_%m_%d %H_%M_%S")
        full_filename = f"{filename}_{timestamp}.jpg"
        filepath = os.path.join(self.imgs_dir, full_filename)
        
        # Create directory if needed
        os.makedirs(self.imgs_dir, exist_ok=True)

        # Convert from RGB to BGR
        # frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        print(self.get_gray_card_avg_rgb(frame))

        # Save with current JPEG quality
        success = cv2.imwrite(filepath, frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.current_jpeg_quality])
        if success:
            print(f"Image saved: {filepath} (resolution={self.current_resolution}, quality={self.current_jpeg_quality})")
            return True
        else:
            return False

    def get_gray_card_avg_rgb(self, frame, roi_size=100):
        """
        Compute the average R, G, B value over a small ROI (e.g., 100x100) around the center of the frame.
        """
        height, width, _ = frame.shape

        # Determine the half-size to offset from the center.
        half_roi = roi_size // 2
        
        # Take the integer part of the quotient
        cy, cx = (height * 6) // 7, width // 2
        
        # Compute boundaries of the ROI, making sure we don't go out of frame
        y1 = max(0, cy - half_roi)
        y2 = min(height, cy + half_roi)
        x1 = max(0, cx - half_roi)
        x2 = min(width, cx + half_roi)
        
        # Extract the ROI from the original frame
        roi = frame[y1:y2, x1:x2]  # shape: (roi_height, roi_width, 3) in RGB
        
        # Compute mean values for each channel
        # roi[..., 0] -> R channel, roi[..., 1] -> G channel, roi[..., 2] -> B channel
        r_mean = int(roi[..., 0].mean())
        g_mean = int(roi[..., 1].mean())
        b_mean = int(roi[..., 2].mean())

        return (r_mean, g_mean, b_mean)

    def auto_white_balance(self):
        """
        Enable auto white balance (AWB).
        Once enabled, the camera will handle white balance automatically.

        Returns:
            dict: Contains 'AwbGainR' and 'AwbGainB' values.
        """
        try:
            # Enable Auto White Balance
            self.picam2.set_controls({"AwbEnable": 1})
            print("Auto White Balance is now enabled.")

            # Current AwbGainR AwbGainB
            metadata = self.picam2.capture_metadata()
            awb_gain_r, awb_gain_b= metadata.get("ColourGains")

            if awb_gain_r is not None and awb_gain_b is not None:
                return awb_gain_r, awb_gain_b
            else:
                print("Failed to retrieve AWB gains.")
                return None
        except Exception as e:
            print(f"Error enabling auto white balance: {e}")
            return None

    def set_awb_from_gray_card(self):
        self.start()
        print("Capturing the gray card region for white balance calibration...")

        # Close auto AWB
        self.picam2.set_controls({"AwbEnable": 0})
        time.sleep(1)

        frame = self.capture_frame()

        # calculate ROI
        r_mean, g_mean, b_mean = self.get_gray_card_avg_rgb(frame)
        if r_mean == 0 or b_mean == 0:
            print("Error: invalid ROI or no valid color data.")
            return

        awb_gain_r = g_mean / r_mean
        awb_gain_b = g_mean / b_mean

        # manl
        self.picam2.set_controls({"ColourGains": (awb_gain_r, awb_gain_b)})

        print(f"Manual WB Gains set: R={awb_gain_r:.3f}, B={awb_gain_b:.3f}")
        return awb_gain_r, awb_gain_b


    def set_awb_gains(self, awb_gain_r, awb_gain_b):
        """
        Perform white balance calibration based on the gray card region.
        """
        # Apply manual white balance settings
        self.picam2.set_controls({"ColourGains": (awb_gain_r, awb_gain_b)})

    def auto_adjust_exposure(self, target_brightness=128, tolerance=5, max_iterations=20):
        """
        Automatically adjust the exposure time and analogue gain to achieve the target brightness.
        The brightness is determined by the average (R, G, B) within a center ROI (gray card).
        """
        # Initial values
        exposure_time = 50000  # Start with a default exposure time (microseconds)
        analogue_gain = 1.0    # Start with a default analogue gain
        iteration = 0

        # initialize exposure time and analogue gain
        self.picam2.set_controls({
            "ExposureTime": exposure_time,
            "AnalogueGain": analogue_gain
            })

        while iteration < max_iterations:

            # Capture a new frame
            frame = self.capture_frame()
            
            # Extract the average R, G, B in the center ROI
            b_mean, g_mean, r_mean = self.get_gray_card_avg_rgb(frame)
            # Calculate brightness as the average of R, G, B
            brightness = (r_mean + g_mean + b_mean) / 3.0
            
            print(f"Iteration {iteration+1} | "
                f"ROI (R,G,B)=({r_mean},{g_mean},{b_mean}) => Brightness={brightness:.1f} | "
                f"ExposureTime={exposure_time}")

            # Check if we are within the desired brightness range
            if abs(brightness - target_brightness) <= tolerance:
                print("Target brightness achieved.")
                break
            
            # Adjust exposure time or gain based on brightness
            if brightness < target_brightness:
                # Too dark: increase exposure time or gain
                if exposure_time < 1000000:  # up to 1 second
                    exposure_time = int(exposure_time * 1.075)  # increase by 7.5%
                else:
                    print("Cannot increase brightness further. Maximum settings reached.")
                    break
            else:
                # Too bright: decrease exposure time or gain
                if exposure_time > 1000:   # down to 1ms
                    exposure_time = int(exposure_time / 1.075)  # decrease by 7.5%
                else:
                    print("Cannot decrease brightness further. Minimum settings reached.")
                    break
            
            # Clamp the values to valid ranges
            exposure_time = max(1000, min(exposure_time, 1000000))

            # Set the current exposure time and analogue gain
            self.picam2.set_controls({
                "ExposureTime": exposure_time,
                "AnalogueGain": analogue_gain
                })

            iteration += 1
            # Small delay to allow the camera settings to take effect
            time.sleep(0.2)

        if iteration == max_iterations:
            print("Maximum iterations reached. Target brightness may not have been achieved.")