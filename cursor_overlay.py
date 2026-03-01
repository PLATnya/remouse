import tkinter as tk
import ctypes
from pynput import mouse
import time
import threading
import sys
import os
import pytesseract

if sys.platform == "win32":
    tess_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tess_path):
        pytesseract.pytesseract.tesseract_cmd = tess_path
        
from PIL import Image, ImageGrab

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
        
        self.detected_rects = []
        self.drawn_rects = []
        
        self.ocr_thread = None
        #self.sct = mss.mss() if mss else None

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
            
            # Start OCR Thread
            #if pytesseract and self.sct:
            self.ocr_thread = threading.Thread(target=self._ocr_loop, daemon=True)
            self.ocr_thread.start()
                
            self._update_loop()
            
    def _ocr_loop(self):
        while self.running:
            if not self.config.get("show_rect_cursor", True):
                time.sleep(0.1)
                continue
                
            x, y = self.mouse_controller.position
            win_x = int(x - self.width / 2)
            win_y = int(y - self.height / 2)
            
            monitor = {"top": win_y, "left": win_x, "width": int(self.width), "height": int(self.height)}
            
            try:
                # Capture the region
                #sct_img = self.sct.grab(monitor)
                #img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                

                img = ImageGrab.grab(bbox=(win_x, win_y, win_x + int(self.width), win_y + int(self.height)))
                # Analyze OCR
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                
                new_rects = []
                for i in range(len(data['text'])):
                    text = data['text'][i].strip()
                    conf = int(data['conf'][i])
                    
                    if text and conf > 30:
                        tx, ty, tw, th = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                        # Discard if outside main area boundaries
                        if tx >= 0 and ty >= 0 and (tx + tw) <= self.width and (ty + th) <= self.height:
                            print(f"Found str: '{text}' | Conf: {conf} | Rect: x={tx} y={ty} w={tw} h={th}")
                            new_rects.append({'x': tx, 'y': ty, 'w': tw, 'h': th, 'text': text})
                            
                self.detected_rects = new_rects
            except Exception as e:
                print(f"OCR Error: {e}")
                # Wait briefly on error to avoid spamming CPU
                time.sleep(0.5)
                
            # Run at roughly 5 FPS to strike a balance between CPU and responsiveness
            time.sleep(0.2)

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
            
            # Redraw OCR rectangles efficiently
            # We first clear existing ones
            for r_id in self.drawn_rects:
                self.canvas.delete(r_id)
            self.drawn_rects.clear()
            
            for d in self.detected_rects:
                r_id = self.canvas.create_rectangle(d['x'], d['y'], d['x'] + d['w'], d['y'] + d['h'], outline="green", width=1)
                self.drawn_rects.append(r_id)
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
