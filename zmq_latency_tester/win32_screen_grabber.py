# zmq_latency_tester/win32_screen_grabber.py
import win32gui
import win32ui
import win32con
import numpy as np
import time
from screeninfo import get_monitors

class MockRuntimeSettings:
    def __init__(self, screenshot_size=180, offset_x=0, offset_y=0, enable_cv_display=False):
        class SystemSettings:
            def __init__(self):
                self.screenshotSize = screenshot_size
                self.screenshotOffsetCenterX = offset_x
                self.screenshotOffsetCenterY = offset_y
        class DebugSettings:
            def __init__(self):
                self.enableLogs = False
                self.enableDisplayCvFrames = enable_cv_display

        self.system = SystemSettings()
        self.debug = DebugSettings()

class MockFPSLogger:
    def start(self): pass
    def increment_frame_count(self, capture_time=0): pass
    def stop(self): pass
    def get_average_fps(self): return 0
    def get_current_fps(self): return 0

class Win32ScreenGrabber:
    def __init__(self, runtimeSettings=None, screenshot_size=180):
        if runtimeSettings is None:
            self.runtimeSettings = MockRuntimeSettings(screenshot_size=screenshot_size)
        else:
            self.runtimeSettings = runtimeSettings

        self.center_x, self.center_y = self._calculate_center()
        self.capture_area = self._calculate_capture_area()
        self.fps_logger = MockFPSLogger()
        self.fps_logger.start()

    def _calculate_center(self):
        try:
            primary_monitor = next(m for m in get_monitors() if m.is_primary)
            center_x = (primary_monitor.width // 2) + self.runtimeSettings.system.screenshotOffsetCenterX
            center_y = (primary_monitor.height // 2) + self.runtimeSettings.system.screenshotOffsetCenterY
        except StopIteration:
            print("Warning: No primary monitor found by screeninfo. Using default 0,0 center.")
            center_x = self.runtimeSettings.system.screenshotOffsetCenterX
            center_y = self.runtimeSettings.system.screenshotOffsetCenterY
        except Exception as e:
            print(f"Error calculating center: {e}. Using 0,0 as fallback.")
            center_x = 0
            center_y = 0
        return center_x, center_y

    def _calculate_capture_area(self):
        ss_size = max(1, self.runtimeSettings.system.screenshotSize)
        x = self.center_x - (ss_size // 2)
        y = self.center_y - (ss_size // 2)
        capture_area = {
            'left': x,
            'top': y,
            'width': ss_size,
            'height': ss_size
        }
        return capture_area

    def screen_grab_BGR(self):
        hwin = win32gui.GetDesktopWindow()
        if not hwin:
            print("Error: Could not get desktop window handle.")
            return np.zeros((self.runtimeSettings.system.screenshotSize, self.runtimeSettings.system.screenshotSize, 3), dtype=np.uint8)
        
        hwindc = None
        srcdc = None
        memdc = None
        bmp = None

        try:
            hwindc = win32gui.GetWindowDC(hwin)
            if not hwindc:
                print("Error: Could not get window device context.")
                return np.zeros((self.runtimeSettings.system.screenshotSize, self.runtimeSettings.system.screenshotSize, 3), dtype=np.uint8)

            srcdc = win32ui.CreateDCFromHandle(hwindc)
            memdc = srcdc.CreateCompatibleDC()

            x, y, width, height = (self.capture_area['left'], self.capture_area['top'],
                                   self.capture_area['width'], self.capture_area['height'])

            if width <= 0 or height <= 0:
                print(f"Error: Invalid capture dimensions: w={width}, h={height}. Capture area: {self.capture_area}")
                return np.zeros((self.runtimeSettings.system.screenshotSize, self.runtimeSettings.system.screenshotSize, 3), dtype=np.uint8)

            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(srcdc, width, height)
            memdc.SelectObject(bmp)
            memdc.BitBlt((0, 0), (width, height), srcdc, (x, y), win32con.SRCCOPY)

            bmpstr = bmp.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype='uint8')
            img.shape = (height, width, 4)

            bgr_frame = img[:, :, :3]
        except Exception as e:
            print(f"Error during screen grab: {e}")
            return np.zeros((self.runtimeSettings.system.screenshotSize, self.runtimeSettings.system.screenshotSize, 3), dtype=np.uint8)
        finally:
            # Cleanup GDI objects
            if memdc: memdc.DeleteDC()
            if srcdc: srcdc.DeleteDC()
            if hwin and hwindc: win32gui.ReleaseDC(hwin, hwindc)
            if bmp and bmp.GetHandle(): win32gui.DeleteObject(bmp.GetHandle())

        self.fps_logger.increment_frame_count()
        return bgr_frame

    @staticmethod
    def generate_mock_frame(size=180):
        return np.random.randint(0, 256, (size, size, 3), dtype=np.uint8)