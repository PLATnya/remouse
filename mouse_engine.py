import math
import time
import threading
from pynput import keyboard, mouse
import config_manager

class MouseEngine:
    def __init__(self):
        self.mouse = mouse.Controller()
        
        # Directions: Up, Down, Left, Right
        self.keys_pressed = {
            keyboard.Key.up: False,
            keyboard.Key.down: False,
            keyboard.Key.left: False,
            keyboard.Key.right: False
        }
        
        # Track previous key states for step mode (detect new presses)
        self.keys_previously_pressed = {
            keyboard.Key.up: False,
            keyboard.Key.down: False,
            keyboard.Key.left: False,
            keyboard.Key.right: False
        }
        
        self.running = False
        self.thread = None
        self.listener = None
        self.config = config_manager.load_config()
        self.start_time = None

    def _on_press(self, key):
        if key in self.keys_pressed:
            if not any(self.keys_pressed.values()):
                # First key pressed, start timing for acceleration
                self.start_time = time.time()
            self.keys_pressed[key] = True

    def _on_release(self, key):
        if key in self.keys_pressed:
            self.keys_pressed[key] = False
            self.keys_previously_pressed[key] = False
            if not any(self.keys_pressed.values()):
                # All keys released, reset timing
                self.start_time = None

    def _move_loop(self):
        while self.running:
            if self.start_time is not None:
                step_mode = self.config.get('step_mode', False)
                
                if step_mode:
                    # Step mode: move only on new key press (one move per press)
                    moved = False
                    for key in self.keys_pressed:
                        if self.keys_pressed[key] and not self.keys_previously_pressed[key]:
                            # This is a new key press, move once
                            step_size = float(self.config.get('step_size', 10.0))
                            
                            if key == keyboard.Key.up:
                                self.mouse.move(0, -step_size)
                                moved = True
                            elif key == keyboard.Key.down:
                                self.mouse.move(0, step_size)
                                moved = True
                            elif key == keyboard.Key.left:
                                self.mouse.move(-step_size, 0)
                                moved = True
                            elif key == keyboard.Key.right:
                                self.mouse.move(step_size, 0)
                                moved = True
                            
                            # Update previous state to prevent repeated moves
                            self.keys_previously_pressed[key] = True
                    
                    # If no movement needed, sleep briefly
                    if not moved:
                        time.sleep(float(self.config['update_interval']))
                else:
                    # Continuous mode: use constant speed
                    current_speed = float(self.config['base_speed'])
                    
                    # Calculate movement delta
                    dir_x, dir_y = 0, 0
                    if self.keys_pressed[keyboard.Key.up]:
                        dir_y -= 1
                    if self.keys_pressed[keyboard.Key.down]:
                        dir_y += 1
                    if self.keys_pressed[keyboard.Key.left]:
                        dir_x -= 1
                    if self.keys_pressed[keyboard.Key.right]:
                        dir_x += 1
                    
                    if dir_x != 0 or dir_y != 0:
                        magnitude = math.hypot(dir_x, dir_y)
                        dx = (dir_x / magnitude) * current_speed
                        dy = (dir_y / magnitude) * current_speed
                        self.mouse.move(dx, dy)
                    
                    time.sleep(float(self.config['update_interval']))
            else:
                time.sleep(float(self.config['update_interval']))

    def start(self):
        if self.running:
            return
            
        # Reload config in case it was changed
        self.config = config_manager.load_config()
        
        self.running = True
        self.start_time = None
        
        # Reset previous key states for step mode
        for k in self.keys_previously_pressed:
            self.keys_previously_pressed[k] = False
        
        # Start keyboard listener
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release)
        self.listener.start()
        
        # Start movement loop thread
        self.thread = threading.Thread(target=self._move_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.listener:
            self.listener.stop()
            self.listener = None
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        self.start_time = None
        for k in self.keys_pressed:
            self.keys_pressed[k] = False
        for k in self.keys_previously_pressed:
            self.keys_previously_pressed[k] = False
