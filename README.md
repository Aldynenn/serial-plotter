# Serial Plotter

A serial data plotter built with PyQt6 and VisPy for visualizing numeric data from serial devices.

## Features

- Real-time plotting with interactive pan and zoom controls
- Customizable Y-axis range
- Toggle display between lines, points, or both
- Multiple baud rate support
- Displays up to 500 data points (auto-scrolling)
- Value statistics (min, max, average, mode, median, standard deviation)

## Installation

Install dependencies (ignore if you're using UV):

```bash
pip install PyQt6 vispy numpy pyserial
```

## Usage

Run the application:

```bash
python main.py
```

Run with UV:

```bash
uv run main.py
```

### Quick Start

1. Select your COM port from the dropdown (click "Refresh ports" if needed)
2. Set the baud rate (default: 115200)
3. Click "Start" to begin plotting
4. Use "Flush values" to clear the plot

### Data Format

Send one numeric value per line via serial:
```
123.45
456.78
789.01
...
```

Non-numeric lines are ignored.

### Controls

- **Y-axis range**: Set min/max values and click "Set Range"
- **Display options**: Toggle "Show lines" and "Show points" checkboxes
- **Plot interaction**: Click-drag to pan, mouse wheel to zoom

## Troubleshooting

- **No ports available**: Check device connection and drivers
- **Error opening port**: Verify port isn't in use and baud rate is correct
- **No data showing**: Check Y-axis range matches your data values