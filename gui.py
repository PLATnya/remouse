import tkinter as tk
from tkinter import ttk
import config_manager
from mouse_engine import MouseEngine

class MouseControllerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mouse Controller")
        self.root.geometry("400x350")
        self.root.resizable(False, False)
        
        # Load config
        self.config = config_manager.load_config()
        self.engine = MouseEngine()
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title Label
        title_label = ttk.Label(main_frame, text="Mouse Settings", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Base Speed Slider
        self._create_slider(main_frame, "Base Sensitivity", "base_speed", 0.5, 10.0)
        
        # Acceleration Slider
        self._create_slider(main_frame, "Acceleration Curve", "acceleration", 1.0, 50.0)
        
        # Max Speed Slider
        self._create_slider(main_frame, "Max Speed", "max_speed", 10.0, 100.0)
        
        # Control Buttons Frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        self.start_btn = ttk.Button(btn_frame, text="Start Controller", command=self.start_engine)
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop Controller", command=self.stop_engine, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        
        # Status Label
        self.status_var = tk.StringVar(value="Status: Stopped")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="gray")
        self.status_label.pack(side=tk.BOTTOM)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _create_slider(self, parent, label_text, config_key, min_val, max_val):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        
        # Label with current value
        val_var = tk.DoubleVar(value=self.config[config_key])
        label = ttk.Label(frame, text=f"{label_text}: {val_var.get():.1f}")
        label.pack(anchor=tk.W)
        
        def on_change(event, k=config_key, v=val_var, l=label, text=label_text):
            current_val = round(float(v.get()), 1)
            l.config(text=f"{text}: {current_val}")
            self.config[k] = current_val
            config_manager.save_config(self.config)
            
            # If engine is running, we might need to restart it to pick up new config cleanly
            # Or the engine reads it on the fly. We'll let it use the saved config.
            if self.engine.running:
                # Hot-reload in engine
                self.engine.config = self.config
                
        # Slider
        slider = ttk.Scale(frame, from_=min_val, to=max_val, orient=tk.HORIZONTAL, variable=val_var, command=on_change)
        slider.pack(fill=tk.X)

    def start_engine(self):
        self.engine.start()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("Status: Running (Use Arrow Keys)")
        self.status_label.config(foreground="green")

    def stop_engine(self):
        self.engine.stop()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Status: Stopped")
        self.status_label.config(foreground="gray")

    def on_closing(self):
        self.stop_engine()
        self.root.destroy()
