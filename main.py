import sys
import serial
from PyQt6.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QComboBox, 
    QPushButton, 
    QLabel, 
    QLineEdit, 
    QFormLayout, 
    QCheckBox
)
from PyQt6.QtCore import Qt, QTimer

from config import (
    DEFAULT_BAUD_RATE, 
    DEFAULT_MAX_POINTS, 
    DEFAULT_Y_MIN, 
    DEFAULT_Y_MAX, 
    DEFAULT_UPDATE_INTERVAL
)
from serial_handler import SerialHandler
from plot_widget import PlotWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Serial plotter")
        self.setGeometry(100, 100, 1000, 600)
        
        # Initialize handlers
        self.serial_handler = SerialHandler()
        self.plot_widget = PlotWidget(max_points=DEFAULT_MAX_POINTS)
        
        # State
        self.is_plotting = False
        
        # Timers
        self.serial_timer = QTimer()
        self.serial_timer.timeout.connect(self.read_serial_data)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.batch_update_visuals)
        self.update_timer.setInterval(DEFAULT_UPDATE_INTERVAL)
        self.update_timer.start()
        
        self.initialize_components()


    def initialize_components(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create sidebar
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Add plot widget canvas
        main_layout.addWidget(self.plot_widget.canvas.native, stretch=1)
        
        # Initialize UI
        self.refresh_com_ports()
        self.set_camera_range()

    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setMaximumWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)

        # Status label
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.info_label)
        
        # COM port and baud rate FormLayout
        com_form_layout = QFormLayout()
        
        # COM port combo box
        self.plot_combo = QComboBox()
        self.plot_combo.currentTextChanged.connect(self.on_combo_changed)
        com_form_layout.addRow("COM Port:", self.plot_combo)

        # Baud rate input
        self.baud_rate_input = QLineEdit()
        self.baud_rate_input.setText(str(DEFAULT_BAUD_RATE))
        com_form_layout.addRow("Baud Rate:", self.baud_rate_input)
        
        # Max points input
        self.max_points_input = QLineEdit()
        self.max_points_input.setText(str(DEFAULT_MAX_POINTS))
        com_form_layout.addRow("Max Points:", self.max_points_input)
        
        # Add FormLayout to sidebar
        sidebar_layout.addLayout(com_form_layout)

        # Refresh ports button
        self.refresh_ports_button = QPushButton("Refresh ports")
        self.refresh_ports_button.clicked.connect(self.refresh_com_ports)
        sidebar_layout.addWidget(self.refresh_ports_button)

        # Start-stop button
        self.start_stop_button = QPushButton("Start")
        self.start_stop_button.clicked.connect(self.toggle_start_stop)
        sidebar_layout.addWidget(self.start_stop_button)

        # Y-axis range inputs
        form_layout = QFormLayout()
        
        self.y_min_input = QLineEdit()
        self.y_min_input.setText(str(DEFAULT_Y_MIN))
        self.y_min_input.setPlaceholderText("Y Min")
        form_layout.addRow("Y Min:", self.y_min_input)
        
        self.y_max_input = QLineEdit()
        self.y_max_input.setText(str(DEFAULT_Y_MAX))
        self.y_max_input.setPlaceholderText("Y Max")
        form_layout.addRow("Y Max:", self.y_max_input)
        
        sidebar_layout.addLayout(form_layout)
        
        # Set Range button
        self.set_range_button = QPushButton("Set Range")
        self.set_range_button.clicked.connect(self.set_camera_range)
        sidebar_layout.addWidget(self.set_range_button)

        # Clear button
        self.clear_button = QPushButton("Flush values")
        self.clear_button.clicked.connect(self.clear_plot_values)
        sidebar_layout.addWidget(self.clear_button)

        # Display options checkboxes
        self.show_line_checkbox = QCheckBox("Show lines")
        self.show_line_checkbox.setChecked(True)
        self.show_line_checkbox.stateChanged.connect(self.toggle_line_visibility)
        sidebar_layout.addWidget(self.show_line_checkbox)
        
        self.show_points_checkbox = QCheckBox("Show points")
        self.show_points_checkbox.setChecked(True)
        self.show_points_checkbox.stateChanged.connect(self.toggle_points_visibility)
        sidebar_layout.addWidget(self.show_points_checkbox)
        
        self.stats_label = QLabel("Statistics:\nNo data")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.stats_label.setWordWrap(True)
        sidebar_layout.addWidget(self.stats_label)

        sidebar_layout.addStretch() # Push everything to the top
        
        return sidebar

    def batch_update_visuals(self):
        if not self.plot_widget.pending_updates:
            return
        
        self.plot_widget.update_visuals()
        
        try:
            y_min = float(self.y_min_input.text())
            y_max = float(self.y_max_input.text())
        except ValueError:
            y_min, y_max = DEFAULT_Y_MIN, DEFAULT_Y_MAX
        
        self.plot_widget.update_camera(y_min, y_max)
        self.update_statistics()

    def clear_plot_values(self):
        self.plot_widget.clear_data()
        self.info_label.setText("Values flushed")
        self.batch_update_visuals()
        self.update_statistics()


    def on_combo_changed(self, text):
        self.info_label.setText(f"Selected: {text}")

    def refresh_com_ports(self):
        self.plot_combo.clear()
        ports = self.serial_handler.get_available_ports()
        
        if ports:
            for port_device, port_display in ports:
                self.plot_combo.addItem(port_display, port_device)
            self.info_label.setText(f"Found {len(ports)} port(s)")
        else:
            self.plot_combo.addItem("No ports available")
            self.info_label.setText("No COM ports found")


    def toggle_start_stop(self):
        if not self.is_plotting:
            port_device = self.plot_combo.currentData()
            if not port_device or port_device == "No ports available":
                self.info_label.setText("No valid port selected")
                return
            
            try:
                baud_rate = int(self.baud_rate_input.text())
            except ValueError:
                baud_rate = DEFAULT_BAUD_RATE
            
            try:
                max_points = int(self.max_points_input.text())
                if max_points > 0:
                    self.plot_widget.max_points = max_points
            except ValueError:
                pass
            
            success, message = self.serial_handler.connect(port_device, baud_rate)
            if success:
                self.is_plotting = True
                self.start_stop_button.setText("Stop")
                self.serial_timer.start()
                self.info_label.setText(message)
            else:
                self.info_label.setText(message)
        else:
            self.stop_plotting()

    def stop_plotting(self):
        self.is_plotting = False
        self.serial_timer.stop()
        self.start_stop_button.setText("Start")
        self.serial_handler.disconnect()
        self.info_label.setText("Stopped plotting")


    def read_serial_data(self):
        try:
            for tag, value in self.serial_handler.read_data():
                self.plot_widget.push_value(tag, value)
        except serial.SerialException as e:
            self.info_label.setText(str(e))
            self.stop_plotting()

    def toggle_line_visibility(self, state):
        self.plot_widget.set_line_visibility(state == Qt.CheckState.Checked.value)
        self.batch_update_visuals()

    def toggle_points_visibility(self, state):
        self.plot_widget.set_points_visibility(state == Qt.CheckState.Checked.value)
        self.batch_update_visuals()


    def set_camera_range(self):
        try:
            y_min = float(self.y_min_input.text())
            y_max = float(self.y_max_input.text())
        except ValueError:
            y_min, y_max = DEFAULT_Y_MIN, DEFAULT_Y_MAX
            self.info_label.setText("Invalid Y range, using defaults")
        
        self.plot_widget.update_camera(y_min, y_max)

    def update_statistics(self):
        stats = self.plot_widget.get_statistics()
        
        if not stats:
            self.stats_label.setText("Statistics:\nNo data")
            return
        
        stats_lines = ["Statistics:"]
        for tag in sorted(stats.keys()):
            s = stats[tag]
            stats_lines.append(f"\n[{tag}]")
            stats_lines.append(f"-Min: {s['min']:.2f}")
            stats_lines.append(f"-Max: {s['max']:.2f}")
            stats_lines.append(f"-Avg: {s['avg']:.2f}")
            stats_lines.append(f"-Median: {s['median']:.2f}")
            stats_lines.append(f"-Mode: {s['mode']:.2f}")
            stats_lines.append(f"-Std dev: {s['std']:.2f}")
        
        self.stats_label.setText("\n".join(stats_lines))



def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()