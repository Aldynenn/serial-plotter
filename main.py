import sys
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QComboBox, QPushButton, QLabel)
from PyQt6.QtCore import Qt
from vispy import scene
from vispy.scene import visuals

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VisPy PyQt6 Application")
        self.setGeometry(100, 100, 1000, 600)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create sidebar
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Create VisPy canvas
        self.canvas = scene.SceneCanvas(keys='interactive', show=True)
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = 'turntable'
        self.view.camera.distance = 10
        
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
            "3D Scatter Plot",
            "3D Line Plot",
            "3D Surface Plot",
            "Spiral"
        ])
        self.plot_combo.currentTextChanged.connect(self.on_combo_changed)
        sidebar_layout.addWidget(self.plot_combo)
        
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
        
        plot_type = self.plot_combo.currentText()
        
        if plot_type == "3D Scatter Plot":
            self.create_scatter_plot()
        elif plot_type == "3D Line Plot":
            self.create_line_plot()
        elif plot_type == "3D Surface Plot":
            self.create_surface_plot()
        elif plot_type == "Spiral":
            self.create_spiral_plot()
    
    def create_scatter_plot(self):
        # Generate random 3D points
        n = 500
        pos = np.random.randn(n, 3)
        colors = np.random.rand(n, 4)
        colors[:, 3] = 1.0  # Full opacity
        
        scatter = visuals.Markers()
        scatter.set_data(pos, face_color=colors, size=5)
        self.view.add(scatter)
    
    def create_line_plot(self):
        # Generate a 3D line
        t = np.linspace(0, 4*np.pi, 200)
        pos = np.column_stack([
            np.sin(t),
            np.cos(t),
            t / (4*np.pi) * 3
        ])
        
        line = visuals.Line(pos, color='cyan', width=3)
        self.view.add(line)
    
    def create_surface_plot(self):
        # Generate a 3D surface
        x = np.linspace(-3, 3, 50)
        y = np.linspace(-3, 3, 50)
        X, Y = np.meshgrid(x, y)
        Z = np.sin(np.sqrt(X**2 + Y**2))
        
        surface = visuals.SurfacePlot(x=x, y=y, z=Z, color=(0.5, 0.8, 1.0, 1.0))
        self.view.add(surface)
    
    def create_spiral_plot(self):
        # Generate a 3D spiral
        t = np.linspace(0, 8*np.pi, 500)
        radius = np.linspace(0.1, 2, 500)
        pos = np.column_stack([
            radius * np.cos(t),
            radius * np.sin(t),
            t / (2*np.pi)
        ])
        
        # Create gradient colors
        colors = np.zeros((500, 4))
        colors[:, 0] = np.linspace(1, 0, 500)  # Red
        colors[:, 1] = np.linspace(0, 1, 500)  # Green
        colors[:, 2] = 0.5                      # Blue
        colors[:, 3] = 1.0                      # Alpha
        
        line = visuals.Line(pos, color=colors, width=4)
        self.view.add(line)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()