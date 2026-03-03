import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "base_speed": 2.0,      # Initial pixels per interval
    "acceleration": 15.0,    # Pixels per second increase
    "max_speed": 40.0,      # Maximum pixels per interval
    "update_interval": 0.01, # 100 Hz refresh rate
    "rect_width": 20.0,     # Rectangle cursor width
    "rect_height": 20.0,    # Rectangle cursor height
    "show_rect_cursor": True, # Whether the rectangle cursor overlay is active
    "step_mode": False,      # Enable step-based movement (one move per key press)
    "step_size": 10.0        # Pixels to move per key press in step mode
}

def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Ensure all keys exist in case of updates
            for key, val in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = val
            return config
    except Exception as e:
        print(f"Error loading config, using default: {e}")
        return dict(DEFAULT_CONFIG)

def save_config(config: dict):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")
