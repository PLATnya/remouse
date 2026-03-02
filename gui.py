from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QSlider, QCheckBox, QPushButton,
                             QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import config_manager
from mouse_engine import MouseEngine
from cursor_overlay import CursorOverlay


class MouseControllerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Load config
        self.config = config_manager.load_config()
        self.engine = MouseEngine()
        self.overlay = CursorOverlay(self.config)
        
        # Setup UI
        self.setup_ui()
        
        # Handle window close - override closeEvent method
        # Note: We store reference to call from overridden method
        
    def setup_ui(self):
        self.setWindowTitle("Mouse Controller")
        self.setFixedSize(400, 550)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)
        
        # Title Label
        title_label = QLabel("Mouse Settings")
        title_font = QFont("Helvetica", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        main_layout.addSpacing(10)
        
        # Base Speed Slider
        self._create_slider(main_layout, "Base Sensitivity", "base_speed", 0.5, 10.0)
        
        # Acceleration Slider
        self._create_slider(main_layout, "Acceleration Curve", "acceleration", 1.0, 50.0)
        
        # Max Speed Slider
        self._create_slider(main_layout, "Max Speed", "max_speed", 10.0, 100.0)
        
        # Rectangle Show Toggle
        self._create_checkbox(main_layout, "Show Rectangle Cursor & Hide System Cursor", "show_rect_cursor")
        
        # Rectangle Width Slider
        self._create_slider(main_layout, "Rectangle Width", "rect_width", 5.0, 200.0)
        
        # Rectangle Height Slider
        self._create_slider(main_layout, "Rectangle Height", "rect_height", 5.0, 200.0)
        
        # Spacer
        main_layout.addStretch()
        
        # Control Buttons Frame
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.start_btn = QPushButton("Start Controller")
        self.start_btn.clicked.connect(self.start_engine)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Controller")
        self.stop_btn.clicked.connect(self.stop_engine)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)
        
        # Status Label
        self.status_var = "Status: Stopped"
        self.status_label = QLabel(self.status_var)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: gray;")
        main_layout.addWidget(self.status_label)
        
    def _create_slider(self, parent_layout, label_text, config_key, min_val, max_val):
        # Container frame
        frame = QFrame()
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(2)
        
        # Label with current value
        current_val = self.config.get(config_key, (min_val + max_val) / 2)
        self.slider_labels = getattr(self, 'slider_labels', {})
        self.slider_vars = getattr(self, 'slider_vars', {})
        
        label = QLabel(f"{label_text}: {current_val:.1f}")
        self.slider_labels[config_key] = label
        frame_layout.addWidget(label)
        
        # Slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(int(min_val * 10))
        slider.setMaximum(int(max_val * 10))
        slider.setValue(int(current_val * 10))
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setTickInterval(int((max_val - min_val)))
        slider.valueChanged.connect(
            lambda value, k=config_key, l=label, text=label_text: self._on_slider_change(value, k, l, text)
        )
        self.slider_vars[config_key] = slider
        frame_layout.addWidget(slider)
        
        parent_layout.addWidget(frame)
        
    def _on_slider_change(self, value, config_key, label, label_text):
        current_val = round(value / 10.0, 1)
        label.setText(f"{label_text}: {current_val}")
        self.config[config_key] = current_val
        config_manager.save_config(self.config)
        
        # If engine is running, hot-reload config
        if self.engine.running:
            self.engine.config = self.config
            
    def _create_checkbox(self, parent_layout, label_text, config_key):
        frame = QFrame()
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        
        val = self.config.get(config_key, True)
        
        checkbox = QCheckBox(label_text)
        checkbox.setChecked(val)
        checkbox.stateChanged.connect(
            lambda state, k=config_key: self._on_checkbox_change(state, k)
        )
        self.checkbox_vars = getattr(self, 'checkbox_vars', {})
        self.checkbox_vars[config_key] = checkbox
        frame_layout.addWidget(checkbox)
        
        parent_layout.addWidget(frame)
        
    def _on_checkbox_change(self, state, config_key):
        value = state == Qt.CheckState.Checked.value
        self.config[config_key] = value
        config_manager.save_config(self.config)
        self.overlay.update_config(self.config)
        if self.engine.running:
            self.engine.config = self.config
            
    def start_engine(self):
        self.engine.start()
        self.overlay.update_config(self.config)
        self.overlay.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_var = "Status: Running (Use Arrow Keys)"
        self.status_label.setText(self.status_var)
        self.status_label.setStyleSheet("color: green;")
        
    def stop_engine(self):
        self.overlay.stop()
        self.engine.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_var = "Status: Stopped"
        self.status_label.setText(self.status_var)
        self.status_label.setStyleSheet("color: gray;")
        
    def closeEvent(self, event):
        self.on_closing()
        event.accept()
        
    def on_closing(self):
        self.stop_engine()
