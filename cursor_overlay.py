import tkinter as tk
import ctypes
from pynput import mouse
import time

# Constants for hiding the Windows cursor
OCR_NORMAL = 32512
SPI_SETCURSORS = 0x0057

class CursorOverlay:
    def __init__(self, root, config):
        self.config = config
        self.root = getattr(root, 'tk', root) # allow passing a TopLevel or Tk root
        self.window = tk.Toplevel(root)
        self.window.withdraw() # Hide immediately upon creation
        self.window.overrideredirect(True)
        self.window.wm_attributes("-topmost", True)
        self.window.wm_attributes("-transparentcolor", "black")
        
        # Make the window click-through (Windows specific)
        # WS_EX_TRANSPARENT = 0x00000020
        # WS_EX_LAYERED = 0x00080000
        hwnd = ctypes.windll.user32.GetParent(self.window.winfo_id())
        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex_style | 0x00080000 | 0x00000020)
        
        self.width = float(self.config.get("rect_width", 20.0))
        self.height = float(self.config.get("rect_height", 20.0))
        
        self.canvas = tk.Canvas(self.window, width=self.width, height=self.height, bg="black", highlightthickness=0)
        self.canvas.pack()
        self.rect = self.canvas.create_rectangle(0, 0, self.width-1, self.height-1, outline="red", width=2)
        
        self.mouse_controller = mouse.Controller()
        
        self.cursor_hidden = False
        
        self.running = False

    def update_config(self, config):
        self.config = config
        new_width = float(self.config.get("rect_width", 20.0))
        new_height = float(self.config.get("rect_height", 20.0))
        
        if new_width != self.width or new_height != self.height:
            self.width = new_width
            self.height = new_height
            self.canvas.config(width=self.width, height=self.height)
            self.canvas.coords(self.rect, 0, 0, self.width-1, self.height-1)
            
    def start(self):
        if not self.running:
            self.running = True
            if self.config.get("show_rect_cursor", True):
                self._hide_system_cursor()
            self._update_loop()

    def _update_loop(self):
        if not self.running:
            if self.window.winfo_viewable():
                self.window.withdraw()
            return
            
        if self.config.get("show_rect_cursor", True):
            if not self.window.winfo_viewable():
                self.window.deiconify()
                self._hide_system_cursor()
                
            x, y = self.mouse_controller.position
            # Center the rectangle on the cursor
            win_x = int(x - self.width / 2)
            win_y = int(y - self.height / 2)
            self.window.geometry(f"{int(self.width)}x{int(self.height)}+{win_x}+{win_y}")
            # Ensure topmost
            self.window.lift()
        else:
            if self.window.winfo_viewable():
                self.window.withdraw()
                self._restore_system_cursor()
                
        self.window.after(16, self._update_loop) # ~60 FPS

    def _hide_system_cursor(self):
        if not self.cursor_hidden:
            AND_mask = bytearray([0xFF] * 128)
            XOR_mask = bytearray([0x00] * 128)
            hCursor = ctypes.windll.user32.CreateCursor(0, 0, 0, 32, 32, bytes(AND_mask), bytes(XOR_mask))
            ctypes.windll.user32.SetSystemCursor(hCursor, OCR_NORMAL)
            self.cursor_hidden = True

    def _restore_system_cursor(self):
        if self.cursor_hidden:
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
            self.cursor_hidden = False

    def stop(self):
        self.running = False
        self._restore_system_cursor()
        if self.window.winfo_exists():
            self.window.withdraw()
