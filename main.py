import sys
import numpy as np
import serial
import serial.tools.list_ports
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
    QSlider,
    QCheckBox
)
from PyQt6.QtCore import Qt, QTimer
from vispy import scene
from vispy.scene import visuals


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Serial plotter")
        self.setGeometry(100, 100, 1000, 600)
        
        # Initialize data storage
        self.data_points = np.empty((0, 2))
        self.max_points = 500
        self.x_counter = 0  # Counter for x-axis positioning
        
        # Serial communication variables
        self.is_plotting = False
        self.serial_port = None
        self.serial_timer = QTimer()
        self.serial_timer.timeout.connect(self.read_serial_data)
        

        # Display settings
        self.show_points = True
        self.show_line = True
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create sidebar
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Create VisPy canvas
        self.canvas = scene.SceneCanvas(keys='interactive', show=True, bgcolor='#1e1e1e')
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = 'panzoom'
        
        # Add grid with Y-axis segmentation
        self.grid = scene.GridLines(parent=self.view.scene, color=(0.4, 0.4, 0.4, 0.4))
        
        # Add canvas to main layout
        main_layout.addWidget(self.canvas.native, stretch=1)
        
        # Initialize with default plot
        self.create_plot()



    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setMaximumWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)

        # Label
        self.info_label = QLabel("Select COM port:")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.info_label)
        
        # COM port and baud rate in FormLayout
        com_form_layout = QFormLayout()
        
        self.plot_combo = QComboBox()
        self.plot_combo.currentTextChanged.connect(self.on_combo_changed)
        com_form_layout.addRow("COM Port:", self.plot_combo)

        self.baud_rate_input = QLineEdit()
        self.baud_rate_input.setText("115200")
        com_form_layout.addRow("Baud Rate:", self.baud_rate_input)
        
        self.max_points_input = QLineEdit()
        self.max_points_input.setText("500")
        com_form_layout.addRow("Max Points:", self.max_points_input)
        
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
        self.y_min_input.setText("-1024")
        self.y_min_input.setPlaceholderText("Y Min")
        form_layout.addRow("Y Min:", self.y_min_input)
        
        self.y_max_input = QLineEdit()
        self.y_max_input.setText("1024")
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
        
        # Statistics display
        self.stats_label = QLabel(
            "Statistics:\n"
            "Min: N/A\n"
            "Max: N/A\n"
            "Avg: N/A\n"
            "Mode: N/A\n"
            "Median: N/A\n"
            "Std. dev.: N/A"
        )
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sidebar_layout.addWidget(self.stats_label)

        # Add stretch to push everything to the top
        sidebar_layout.addStretch()
        
        return sidebar



    def create_plot(self):
        # Clear existing visuals
        # self.view.scene.children.clear()
        
        # Add grid
        self.grid = scene.GridLines(parent=self.view.scene, color=(1, 1, 1, 0.5))
        
        # Add Y-axis with labels
        y_axis = scene.AxisWidget(orientation='left')
        y_axis.stretch = (1, 1)
        self.view.add_widget(y_axis)
        y_axis.link_view(self.view)
        
        # plot_type = self.plot_combo.currentText()
        
        self.create_line_plot()
        self.refresh_com_ports()
        
        # Set camera range to match Y-axis limits
        self.set_camera_range()



    def update_visuals(self):
        if len(self.data_points) > 0:
            if self.show_line:
                self.line.set_data(self.data_points)
            else:
                self.line.set_data(np.empty((0, 2)))
            
            if self.show_points:
                self.scatter.set_data(
                    self.data_points, 
                    face_color=(0.1, 0.9, 1, 1), 
                    size=6, 
                    edge_width=0, 
                    edge_color=None, 
                    symbol='o'
                )
            else:
                self.scatter.set_data(np.empty((0, 2)))
        else:
            # Clear the visuals when no data
            self.line.set_data(np.empty((0, 2)))
            self.scatter.set_data(np.empty((0, 2)))
            
        # Set camera to show fixed range with newest data on right
        # Current x position (newest data point)
        current_x = self.x_counter - 1
        
        # Set fixed x-axis range showing max_points width
        x_range_width = self.max_points
        x_min = current_x - x_range_width + 1
        x_max = current_x + 1
        
        # Get Y-axis range from input fields
        try:
            y_min = float(self.y_min_input.text())
            y_max = float(self.y_max_input.text())
        except ValueError:
            y_min, y_max = 0, 1024
        
        # Set camera rect directly to avoid bounds computation issues with empty data
        self.view.camera.rect = (x_min, y_min, x_max - x_min, y_max - y_min)

    def create_line_plot(self):
        # Create antialiased line with better styling
        self.line = visuals.Line(
            self.data_points, 
            color=(0.1, 0.9, 1, 1), 
            width=1, 
            antialias=True, 
            method='gl'
        )
        self.view.add(self.line)
        
        # Add points on top of the line
        self.scatter = visuals.Markers()
        self.scatter.antialias = 1
        self.view.add(self.scatter)

        self.update_visuals()



    def clear_plot_values(self):
        self.data_points = np.empty((0, 2))
        self.x_counter = 0
        self.scatter.set_data(self.data_points)
        self.line.set_data(self.data_points)
        self.info_label.setText("Values flushed")
        self.update_statistics()

    def on_combo_changed(self, text):
        self.info_label.setText(f"Selected: {text}")

    def refresh_com_ports(self):
        self.plot_combo.clear()
        ports = serial.tools.list_ports.comports()
        
        if ports:
            for port in ports:
                port_display = f"{port.device} - {port.description}"
                self.plot_combo.addItem(port_display, port.device)
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
                baud_rate = 115200
            try:
                max_points = int(self.max_points_input.text())
                if max_points > 0:
                    self.max_points = max_points
            except ValueError:
                pass  # Keep current max_points value
            try:
                self.serial_port = serial.Serial(port_device, baud_rate, timeout=0.1)
                self.is_plotting = True
                self.start_stop_button.setText("Stop")
                self.serial_timer.start()
                self.info_label.setText(f"Started plotting from {port_device}")
            except serial.SerialException as e:
                self.info_label.setText(f"Error opening port!")
                self.serial_port = None
        else:
            self.stop_plotting()

    def stop_plotting(self):
        self.is_plotting = False
        self.serial_timer.stop()
        self.start_stop_button.setText("Start")
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.serial_port = None
        self.info_label.setText("Stopped plotting")

    def read_serial_data(self):
        if not self.serial_port or not self.serial_port.is_open:
            return
        try:
            while self.serial_port.in_waiting > 0:
                line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    try: # Try to parse as float
                        value = float(line) 
                        self.push_new_value(y_value=value)
                    except ValueError: # Skip line if it can't be parsed
                        pass
        except serial.SerialException as e:
            self.info_label.setText(f"Serial error: {str(e)}")
            self.stop_plotting()


    def toggle_line_visibility(self, state):
        self.show_line = state == Qt.CheckState.Checked.value
        self.update_visuals()
    
    def toggle_points_visibility(self, state):
        self.show_points = state == Qt.CheckState.Checked.value
        self.update_visuals()

    def set_camera_range(self):
        # Get Y-axis range
        try:
            self.y_min = float(self.y_min_input.text())
            self.y_max = float(self.y_max_input.text())
        except ValueError:
            self.y_min, self.y_max = 0, 1024
            self.info_label.setText("Invalid Y range, using defaults")
        
        # Update visuals with new range
        self.update_visuals()

    def update_statistics(self):
        if len(self.data_points) == 0:
            self.stats_label.setText(
                "Statistics:\n"
                "Min: N/A\n"
                "Max: N/A\n"
                "Avg: N/A\n"
                "Mode: N/A\n"
                "Median: N/A\n"
                "Std. dev.: N/A"
            )
            return
        
        # Extract Y values
        y_values = self.data_points[:, 1]
        
        # Calculate statistics
        min_val = np.min(y_values)
        max_val = np.max(y_values)
        avg_val = np.mean(y_values)
        median_val = np.median(y_values)
        
        # Calculate mode (most frequent value, rounded to 2 decimals for grouping)
        if len(y_values) >= 2:
            rounded_values = np.round(y_values, 2)
            unique_vals, counts = np.unique(rounded_values, return_counts=True)
            mode_val = unique_vals[np.argmax(counts)]
            std_val = np.std(y_values)
        else:
            mode_val = y_values[0]
            std_val = 0.0
        
        # Update label with formatted statistics
        self.stats_label.setText(
            f"Statistics:\n"
            f"Min: {min_val:.2f}\n"
            f"Max: {max_val:.2f}\n"
            f"Avg: {avg_val:.2f}\n"
            f"Mode: {mode_val:.2f}\n"
            f"Median: {median_val:.2f}\n"
            f"Std. dev.: {std_val:.2f}"
        )

    def push_new_value(self, x_value=None, y_value=None):
        # Use counter for x-axis to create time-series effect
        x_value = self.x_counter
        self.x_counter += 1
            
        # Create new point
        new_point = np.array([[x_value, y_value]])
        
        # Add new point to data (always at the end/right side)
        self.data_points = np.vstack([self.data_points, new_point])
        
        # Remove oldest point if exceeding max_points (from the left side)
        if len(self.data_points) > self.max_points:
            self.data_points = self.data_points[1:]
        
        # Update visuals and statistics
        self.update_visuals()
        self.update_statistics()



def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()