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
    QSlider
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

        # Wrapper for COM port selection
        # com_port_wrapper = QWidget()
        # com_port_wrapper.setMaximumWidth(200)
        # com_port_wrapper_layout = QHBoxLayout(com_port_wrapper)

        # Label
        self.info_label = QLabel("Select COM port:")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.info_label)
        
        # ComboBox
        self.plot_combo = QComboBox()
        self.plot_combo.currentTextChanged.connect(self.on_combo_changed)
        sidebar_layout.addWidget(self.plot_combo)

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
        self.y_min_input.setText("0")
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

        # Add button
        self.add_value_button = QPushButton("Add new value")
        self.add_value_button.clicked.connect(self.push_new_value)
        sidebar_layout.addWidget(self.add_value_button)
        
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
        """Update the line and scatter plot with current data"""
        if len(self.data_points) > 0:
            # No need to sort since data is already in time order
            self.line.set_data(self.data_points)
            self.scatter.set_data(
                self.data_points, 
                face_color=(0.1, 0.9, 1, 1), 
                size=4, 
                edge_width=0, 
                edge_color=None, 
                symbol='o'
            )
            
        # Always set camera to show fixed range with newest data on right
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
        
        # Set both X and Y ranges at the same time
        self.view.camera.set_range(x=(x_min, x_max), y=(y_min, y_max))

    def create_line_plot(self):
        # Generate initial sequential data points
        n = 490
        np.random.seed(42)
        
        # Create sequential x values and random y values
        x_values = np.arange(n)
        # y_values = np.random.randn(n) * 2
        # y values should be the sine of x values
        y_values = 512 + 512 * np.sin(x_values * 0.2)
        
        # Store initial data and update counter
        self.data_points = np.column_stack([x_values, y_values])
        self.x_counter = n
        
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
                self.serial_port = serial.Serial(port_device, 115200, timeout=0.1)
                self.is_plotting = True
                self.start_stop_button.setText("Stop")
                self.serial_timer.start()
                self.info_label.setText(f"Started plotting from {port_device}")
            except serial.SerialException as e:
                self.info_label.setText(f"Error opening port: {str(e)}")
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

    def push_new_value(self, x_value=None, y_value=None):
        """Push a new value to the right side of the data and remove oldest if exceeding max_points"""
        # Generate random y value if not provided, use counter for x
        if y_value is None:
            y_value = np.random.randn() * 2
            
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
        
        # Update visuals
        self.update_visuals()



def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()