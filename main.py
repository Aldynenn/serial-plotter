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
        self.data_series = {}
        self.series_visuals = {}
        self.max_points = 500
        self.x_counter = 0 # counter for x-axis positioning
        
        # Colors for data series
        self.color_palette = [
            (0.1, 0.9, 1.0, 1), # Cyan
            (1.0, 0.3, 0.3, 1), # Red
            (0.3, 1.0, 0.3, 1), # Green
            (1.0, 0.8, 0.1, 1), # Yellow
            (1.0, 0.4, 1.0, 1), # Magenta
            (1.0, 0.6, 0.2, 1), # Orange
            (0.5, 0.5, 1.0, 1), # Light Blue
            (0.8, 0.2, 0.8, 1), # Purple
        ]
        self.color_index = 0
        
        # Serial communication, timers
        self.is_plotting = False
        self.serial_port = None
        self.serial_timer = QTimer()
        self.serial_timer.timeout.connect(self.read_serial_data)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.batch_update_visuals)
        self.update_timer.setInterval(8)
        self.pending_updates = set()
        self.update_timer.start()

        self.show_points = True
        self.show_line = True
        
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
        # self.view.camera.aspect = 1  # Maintain aspect ratio
        
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
        self.baud_rate_input.setText("115200")
        com_form_layout.addRow("Baud Rate:", self.baud_rate_input)
        
        # Max points input
        self.max_points_input = QLineEdit()
        self.max_points_input.setText("1000")
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
        self.y_min_input.setText("-1100")
        self.y_min_input.setPlaceholderText("Y Min")
        form_layout.addRow("Y Min:", self.y_min_input)
        
        self.y_max_input = QLineEdit()
        self.y_max_input.setText("1100")
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

        # Add stretch to push everything to the top
        sidebar_layout.addStretch()
        
        return sidebar



    def create_plot(self):        
        self.grid = scene.GridLines(parent=self.view.scene, color=(1, 1, 1, 0.5))
        
        # Add Y-axis with labels
        y_axis = scene.AxisWidget(orientation='left')
        y_axis.stretch = (1, 1)
        self.view.add_widget(y_axis)
        y_axis.link_view(self.view)
        
        self.create_line_plot()
        self.refresh_com_ports()
        self.set_camera_range()



    def update_visuals(self):
        # Update datasets with pending updates
        for tag in list(self.pending_updates):
            if tag not in self.series_visuals:
                continue
                
            line, scatter = self.series_visuals[tag]
            data = self.data_series.get(tag, np.empty((0, 2)))
            
            if len(data) > 0:
                if self.show_line:
                    line.set_data(data)
                else:
                    line.set_data(np.empty((0, 2)))
                
                if self.show_points:
                    scatter.set_data(data)
                else:
                    scatter.set_data(np.empty((0, 2)))
            else:
                line.set_data(np.empty((0, 2)))
                scatter.set_data(np.empty((0, 2)))
        
        self.pending_updates.clear()
    
    def batch_update_visuals(self):
        if not self.pending_updates:
            return
            
        self.update_visuals()
        
        current_x = self.x_counter - 1
        x_range_width = self.max_points
        x_min = current_x - x_range_width + 1
        x_max = current_x + 1
        
        try:
            y_min = float(self.y_min_input.text())
            y_max = float(self.y_max_input.text())
        except ValueError:
            y_min, y_max = 0, 1024
        
        self.view.camera.rect = (x_min, y_min, x_max - x_min, y_max - y_min)
        self.update_statistics()

    def create_line_plot(self):
        self.update_visuals()
    
    def get_or_create_series(self, tag):
        if tag not in self.data_series:
            self.data_series[tag] = np.empty((0, 2))
            
            color = self.color_palette[self.color_index % len(self.color_palette)]
            self.color_index += 1
            
            # Create lines
            line = visuals.Line(
                np.empty((0, 2)), 
                color=color, 
                width=1, 
                antialias=True, 
                method='gl'
            )
            self.view.add(line)
            
            # Create points
            scatter = visuals.Markers()
            scatter.antialias = 1
            scatter.set_data(
                np.empty((0, 2)),
                face_color=color,
                size=4,
                edge_width=0,
                edge_color=None,
                symbol='o'
            )
            self.view.add(scatter)
            
            self.series_visuals[tag] = (line, scatter)
        
        return self.data_series[tag]



    def clear_plot_values(self):
        for tag in self.data_series:
            self.data_series[tag] = np.empty((0, 2))
            self.pending_updates.add(tag)
        self.x_counter = 0
        self.info_label.setText("Values flushed")
        self.batch_update_visuals()
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
                    if ':' in line:
                        # Try to parse with tag (format: "tag:value")
                        parts = line.split(':', 1)
                        tag = parts[0].strip()
                        try:
                            value = float(parts[1].strip())
                            self.push_new_value(tag=tag, y_value=value)
                        except ValueError:
                            pass  # Skip if value can't be parsed
                    else:
                        # Try to parse value without tag
                        try:
                            value = float(line)
                            self.push_new_value(tag='default', y_value=value)
                        except ValueError:
                            pass  # Skip line if it can't be parsed
        except serial.SerialException as e:
            self.info_label.setText(f"Serial error: {str(e)}")
            self.stop_plotting()


    def toggle_line_visibility(self, state):
        self.show_line = state == Qt.CheckState.Checked.value
        self.pending_updates.update(self.data_series.keys())
        self.batch_update_visuals()
    
    def toggle_points_visibility(self, state):
        self.show_points = state == Qt.CheckState.Checked.value
        self.pending_updates.update(self.data_series.keys())
        self.batch_update_visuals()

    def set_camera_range(self):
        try:
            self.y_min = float(self.y_min_input.text())
            self.y_max = float(self.y_max_input.text())
        except ValueError:
            self.y_min, self.y_max = 0, 1024
            self.info_label.setText("Invalid Y range, using defaults")
        self.batch_update_visuals()

    def update_statistics(self):
        # Build statistics text for each dataset that has data
        stats_lines = ["Statistics:"]
        has_data = False
        
        for tag in sorted(self.data_series.keys()):
            data = self.data_series[tag]
            if len(data) == 0:
                continue  # Skip empty datasets
            
            has_data = True
            y_values = data[:, 1]
            
            min_val = np.min(y_values)
            max_val = np.max(y_values)
            avg_val = np.mean(y_values)
            median_val = np.median(y_values)
            
            if len(y_values) >= 2:
                rounded_values = np.round(y_values, 2)
                unique_vals, counts = np.unique(rounded_values, return_counts=True)
                mode_val = unique_vals[np.argmax(counts)]
                std_val = np.std(y_values)
            else:
                mode_val = y_values[0]
                std_val = 0.0
            
            stats_lines.append(f"\n[{tag}]")
            stats_lines.append(f"-Min: {min_val:.2f}")
            stats_lines.append(f"-Max: {max_val:.2f}")
            stats_lines.append(f"-Avg: {avg_val:.2f}")
            stats_lines.append(f"-Median: {median_val:.2f}")
            stats_lines.append(f"-Mode: {mode_val:.2f}")
            stats_lines.append(f"-Std dev: {std_val:.2f}")
        
        if not has_data:
            self.stats_label.setText("Statistics:\nNo data")
        else:
            self.stats_label.setText("\n".join(stats_lines))

    def push_new_value(self, tag='default', x_value=None, y_value=None):
        self.get_or_create_series(tag)
        
        # Add new point to the specific dataset
        x_value = self.x_counter
        self.x_counter += 1
        self.data_series[tag] = np.vstack([self.data_series[tag], np.array([[x_value, y_value]])])
        if len(self.data_series[tag]) > self.max_points:
            self.data_series[tag] = self.data_series[tag][1:]
        
        self.pending_updates.add(tag)



def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()