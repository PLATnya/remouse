import sys
import os
import ctypes
import threading
import time
from pynput import mouse, keyboard
from PIL import Image, ImageGrab
import pytesseract

# Setup tesseract path for Windows
if sys.platform == "win32":
    tess_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tess_path):
        pytesseract.pytesseract.tesseract_cmd = tess_path

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QRect, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QPen, QColor, QCursor

# Constants for hiding the Windows cursor
OCR_NORMAL = 32512
SPI_SETCURSORS = 0x0057


class CursorOverlay(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        # Setup window properties for overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Make the window click-through (Windows specific)
        if sys.platform == "win32":
            hwnd = int(self.winId())
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex_style | 0x00080000 | 0x00000020)
        
        self.width = float(self.config.get("rect_width", 20.0))
        self.height = float(self.config.get("rect_height", 20.0))
        
        # Set initial geometry (will be updated in start)
        self.setFixedSize(int(self.width), int(self.height))
        
        self.mouse_controller = mouse.Controller()
        
        self.cursor_hidden = False
        self.running = False
        
        self.detected_rects = []
        
        self.ocr_thread = None
        
        self.tab_index = -1
        self.last_programmatic_mouse_pos = None
        self.base_rect_x, self.base_rect_y = self.mouse_controller.position
        self.scan_win_x = 0
        self.scan_win_y = 0
        
        # Keyboard listener
        self.keyboard_listener = None
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_loop)
        
    def update_config(self, config):
        self.config = config
        new_width = float(self.config.get("rect_width", 20.0))
        new_height = float(self.config.get("rect_height", 20.0))
        
        if new_width != self.width or new_height != self.height:
            self.width = new_width
            self.height = new_height
            self.setFixedSize(int(self.width), int(self.height))
            self.update()
            
    def start(self):
        if not self.running:
            self.running = True
            self.base_rect_x, self.base_rect_y = self.mouse_controller.position
            
            # Start keyboard listener
            self.keyboard_listener = keyboard.Listener(on_release=self._on_key_release)
            self.keyboard_listener.start()
            
            if self.config.get("show_rect_cursor", True):
                self._hide_system_cursor()
            
            # Start OCR Thread
            self.ocr_thread = threading.Thread(target=self._ocr_loop, daemon=True)
            self.ocr_thread.start()
            
            # Show and start update timer (~60 FPS)
            self.show()
            self.update_timer.start(16)
            
    def _on_key_release(self, key):
        # Get the configured key from config
        next_key = self.config.get("next_rect_key", "Tab").lower()
        
        # Map config key string to pynput key
        key_map = {
            "tab": keyboard.Key.tab,
            "caps_lock": keyboard.Key.caps_lock,
            "space": keyboard.Key.space,
            "enter": keyboard.Key.enter,
            "esc": keyboard.Key.esc,
            "f1": keyboard.Key.f1,
            "f2": keyboard.Key.f2,
            "f3": keyboard.Key.f3,
            "f4": keyboard.Key.f4,
            "f5": keyboard.Key.f5,
            "f6": keyboard.Key.f6,
            "f7": keyboard.Key.f7,
            "f8": keyboard.Key.f8,
            "f9": keyboard.Key.f9,
            "f10": keyboard.Key.f10,
            "f11": keyboard.Key.f11,
            "f12": keyboard.Key.f12,
        }
        
        expected_key = key_map.get(next_key, keyboard.Key.tab)
        
        if key == expected_key:
            if not self.detected_rects:
                self.tab_index = -1
                return
            
            # Sort detected rects to go left-to-right, top-to-bottom
            sorted_rects = sorted(self.detected_rects, key=lambda r: (r['y'], r['x']))
            
            self.tab_index = (self.tab_index + 1) % len(sorted_rects)
            rect = sorted_rects[self.tab_index]
            
            target_x = self.scan_win_x + rect['x'] + rect['w'] / 2.0
            target_y = self.scan_win_y + rect['y'] + rect['h'] / 2.0
            
            self.last_programmatic_mouse_pos = (target_x, target_y)
            self.mouse_controller.position = (target_x, target_y)
            
    def _ocr_loop(self):
        last_move_x, last_move_y = self.base_rect_x, self.base_rect_y
        last_ocr_x, last_ocr_y = None, None
        stop_count = 0
        
        while self.running:
            if not self.config.get("show_rect_cursor", True):
                time.sleep(0.1)
                continue
                
            x, y = self.base_rect_x, self.base_rect_y
            
            dist_from_move = (x - last_move_x)**2 + (y - last_move_y)**2
            last_move_x, last_move_y = x, y
            
            if dist_from_move < 10:
                stop_count += 1
            else:
                stop_count = 0
                self.detected_rects = []
                self.tab_index = -1
                
            if stop_count >= 2:
                if last_ocr_x is not None and last_ocr_y is not None:
                    dist_from_ocr = (x - last_ocr_x)**2 + (y - last_ocr_y)**2
                    if dist_from_ocr < 10:
                        time.sleep(0.1)
                        continue
                        
                last_ocr_x, last_ocr_y = x, y
            else:
                time.sleep(0.1)
                continue
                
            win_x = int(x - self.width / 2)
            win_y = int(y - self.height / 2)
            
            try:
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
            self.hide()
            return
            
        if self.config.get("show_rect_cursor", True):
            if not self.isVisible():
                self.show()
                self._hide_system_cursor()
                
            x, y = self.mouse_controller.position
            
            is_manual_move = False
            if self.last_programmatic_mouse_pos:
                dist_prog = (x - self.last_programmatic_mouse_pos[0])**2 + (y - self.last_programmatic_mouse_pos[1])**2
                if dist_prog > 10:
                    is_manual_move = True
                    self.last_programmatic_mouse_pos = None
            else:
                dist_base = (x - self.base_rect_x)**2 + (y - self.base_rect_y)**2
                if dist_base > 10:
                    is_manual_move = True
            
            if is_manual_move:
                self.base_rect_x, self.base_rect_y = x, y
                self.tab_index = -1
                
            # Center the rectangle on the base rect anchor
            win_x = int(self.base_rect_x - self.width / 2)
            win_y = int(self.base_rect_y - self.height / 2)
            
            self.scan_win_x = win_x
            self.scan_win_y = win_y
            
            self.move(win_x, win_y)
            # Ensure topmost
            self.raise_()
            
            # Trigger repaint
            self.update()
        else:
            if self.isVisible():
                self.hide()
                self._restore_system_cursor()
                
    def paintEvent(self, event):
        if not self.config.get("show_rect_cursor", True):
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw main rectangle (red outline)
        pen = QPen(QColor("red"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(0, 0, int(self.width) - 1, int(self.height) - 1)
        
        # Draw OCR detected rectangles (green)
        pen = QPen(QColor("green"))
        pen.setWidth(1)
        painter.setPen(pen)
        
        for d in self.detected_rects:
            painter.drawRect(int(d['x']), int(d['y']), int(d['w']), int(d['h']))
            
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
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        self.update_timer.stop()
        self.hide()
