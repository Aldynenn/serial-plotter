import sys
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QComboBox, QPushButton, QLabel, 
    QLineEdit, QFormLayout
)
from PyQt6.QtCore import Qt
from vispy import scene
from vispy.scene import visuals

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Serial plotter")
        self.setGeometry(100, 100, 1000, 600)
        
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
        self.update_plot()
        
    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setMaximumWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        
        # Label
        self.info_label = QLabel("Select a plot type:")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.info_label)
        
        # ComboBox
        self.plot_combo = QComboBox()
        self.plot_combo.addItems([
            "Line Plot",
            "Scatter Plot"
        ])
        self.plot_combo.currentTextChanged.connect(self.on_combo_changed)
        sidebar_layout.addWidget(self.plot_combo)
        
        # Y-axis range inputs
        form_layout = QFormLayout()
        
        self.y_min_input = QLineEdit()
        self.y_min_input.setText("0")
        self.y_min_input.setPlaceholderText("Y Min")
        form_layout.addRow("Y Min:", self.y_min_input)
        
        self.y_max_input = QLineEdit()
        self.y_max_input.setText("4096")
        self.y_max_input.setPlaceholderText("Y Max")
        form_layout.addRow("Y Max:", self.y_max_input)
        
        sidebar_layout.addLayout(form_layout)
        
        # Button
        self.update_button = QPushButton("Update Plot")
        self.update_button.clicked.connect(self.update_plot)
        sidebar_layout.addWidget(self.update_button)
        
        # Add stretch to push everything to the top
        sidebar_layout.addStretch()
        
        return sidebar
    
    def on_combo_changed(self, text):
        self.info_label.setText(f"Selected: {text}")
    
    def update_plot(self):
        # Clear existing visuals
        self.view.scene.children.clear()
        
        # Get Y-axis range
        try:
            y_min = float(self.y_min_input.text())
            y_max = float(self.y_max_input.text())
        except ValueError:
            y_min, y_max = 0, 4096
            self.info_label.setText("Invalid Y range, using defaults")
        
        # Re-add grid
        self.grid = scene.GridLines(parent=self.view.scene, color=(0.4, 0.4, 0.4, 0.4))
        
        # Add Y-axis with labels
        y_axis = scene.AxisWidget(orientation='left')
        y_axis.stretch = (1, 1)
        self.view.add_widget(y_axis)
        y_axis.link_view(self.view)
        
        plot_type = self.plot_combo.currentText()
        
        if plot_type == "Scatter Plot":
            self.create_scatter_plot()
        elif plot_type == "Line Plot":
            self.create_line_plot()
        
        # Set camera range to match Y-axis limits
        self.view.camera.set_range(y=(y_min, y_max))
    
    def create_scatter_plot(self):
        # Generate random 2D points
        n = 1000
        pos = np.random.randn(n, 2) * 2
        
        # Create more appealing color palette
        colors = np.zeros((n, 4))
        colors[:, 0] = 0.3 + 0.7 * np.random.rand(n)  # Red channel
        colors[:, 1] = 0.5 + 0.5 * np.random.rand(n)  # Green channel
        colors[:, 2] = 0.8 + 0.2 * np.random.rand(n)  # Blue channel (more blue)
        colors[:, 3] = 0.8  # Slight transparency for depth
        
        scatter = visuals.Markers()
        scatter.set_data(pos, face_color=colors, size=6, edge_width=0, 
                        symbol='o', edge_color=None)
        scatter.antialias = 1  # Enable antialiasing
        self.view.add(scatter)
    
    def create_line_plot(self):
        # Generate the same random 2D points but connected with lines
        n = 1000
        np.random.seed(42)  # Use seed for consistent pattern
        pos = np.random.randn(n, 2) * 2
        
        # Sort points by x-coordinate to create a meaningful line connection
        sorted_indices = np.argsort(pos[:, 0])
        pos_sorted = pos[sorted_indices]
        
        # Create antialiased line with better styling
        line = visuals.Line(pos_sorted, color=(0.2, 0.8, 1.0, 0.9), 
                           width=1, antialias=True, method='gl')
        self.view.add(line)
        
        # Add points on top of the line with coordinated colors
        colors = np.zeros((n, 4))
        colors[:, 0] = 0.3 + 0.7 * np.random.rand(n)
        colors[:, 1] = 0.5 + 0.5 * np.random.rand(n)
        colors[:, 2] = 0.8 + 0.2 * np.random.rand(n)
        colors[:, 3] = 0.85
        
        scatter = visuals.Markers()
        scatter.set_data(pos_sorted, face_color=colors, size=5, 
                        edge_width=0, edge_color=None, symbol='o')
        scatter.antialias = 1
        self.view.add(scatter)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()