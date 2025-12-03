import numpy as np
from vispy import scene
from vispy.scene import visuals
from config import COLOR_PALETTE, GRID_COLOR, BACKGROUND_COLOR, LINE_WIDTH, MARKER_SIZE


class PlotWidget:
    def __init__(self, max_points=1000):
        self.max_points = max_points
        self.x_counter = 0
        self.data_series = {}
        self.series_visuals = {}
        self.pending_updates = set()
        self.color_index = 0
        self.show_points = True
        self.show_line = True
        
        # Create canvas
        self.canvas = scene.SceneCanvas(keys='interactive', show=True, bgcolor=BACKGROUND_COLOR)
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = 'panzoom'
        self.grid = scene.GridLines(parent=self.view.scene, color=GRID_COLOR)
        
        # Add Y-axis
        y_axis = scene.AxisWidget(orientation='left')
        y_axis.stretch = (1, 1)
        self.view.add_widget(y_axis)
        y_axis.link_view(self.view)
    
    def get_or_create_series(self, tag):
        if tag not in self.data_series:
            self.data_series[tag] = np.empty((0, 2))
            
            color = COLOR_PALETTE[self.color_index % len(COLOR_PALETTE)]
            self.color_index += 1
            
            # Create line visual
            line = visuals.Line(
                np.empty((0, 2)), 
                color=color, 
                width=LINE_WIDTH, 
                antialias=True, 
                method='gl'
            )
            self.view.add(line)
            
            # Create scatter visual
            scatter = visuals.Markers()
            scatter.antialias = 1
            scatter.set_data(
                np.empty((0, 2)),
                face_color=color,
                size=MARKER_SIZE,
                edge_width=0,
                symbol='o'
            )
            self.view.add(scatter)
            self.series_visuals[tag] = (line, scatter)
        return self.data_series[tag]
    
    def push_value(self, tag, y_value):
        self.get_or_create_series(tag)
        x_value = self.x_counter
        self.x_counter += 1
        self.data_series[tag] = np.vstack([self.data_series[tag], np.array([[x_value, y_value]])])
        # Keep only max_points
        if len(self.data_series[tag]) > self.max_points:
            self.data_series[tag] = self.data_series[tag][1:]
        self.pending_updates.add(tag)
    
    def update_visuals(self):
        for tag in list(self.pending_updates):
            if tag not in self.series_visuals:
                continue            
            line, scatter = self.series_visuals[tag]
            data = self.data_series.get(tag, np.empty((0, 2)))
            
            # Get the color from the line visual
            color = line.color
            
            if len(data) > 0:
                if self.show_line:
                    line.set_data(data)
                else:
                    line.set_data(np.empty((0, 2)))
                
                if self.show_points:
                    scatter.set_data(data, face_color=color, size=MARKER_SIZE, edge_width=0, symbol='o')
                else:
                    scatter.set_data(np.empty((0, 2)))
            else:
                line.set_data(np.empty((0, 2)))
                scatter.set_data(np.empty((0, 2)))
        self.pending_updates.clear()
    
    def update_camera(self, y_min, y_max):
        current_x = self.x_counter - 1
        x_range_width = self.max_points
        x_min = current_x - x_range_width + 1
        x_max = current_x + 1
        self.view.camera.rect = (x_min, y_min, x_max - x_min, y_max - y_min)
    
    def clear_data(self):
        for tag in self.data_series:
            self.data_series[tag] = np.empty((0, 2))
            self.pending_updates.add(tag)
        self.x_counter = 0
    
    def set_line_visibility(self, visible):
        self.show_line = visible
        self.pending_updates.update(self.data_series.keys())
    
    def set_points_visibility(self, visible):
        self.show_points = visible
        self.pending_updates.update(self.data_series.keys())
    
    def get_statistics(self):
        stats = {}
        for tag in sorted(self.data_series.keys()):
            data = self.data_series[tag]
            if len(data) == 0:
                continue
            
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
            
            stats[tag] = {
                'min': min_val,
                'max': max_val,
                'avg': avg_val,
                'median': median_val,
                'mode': mode_val,
                'std': std_val
            }
        
        return stats
