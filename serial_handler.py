import serial
import serial.tools.list_ports


class SerialHandler:
    def __init__(self):
        self.serial_port = None
        self.is_connected = False
    
    def get_available_ports(self):
        ports = serial.tools.list_ports.comports()
        return [(port.device, f"{port.device} - {port.description}") for port in ports]
    
    def connect(self, port_device, baud_rate):
        try:
            self.serial_port = serial.Serial(port_device, baud_rate, timeout=0.1)
            self.is_connected = True
            return True, f"Connected to {port_device}"
        except serial.SerialException as e:
            self.serial_port = None
            self.is_connected = False
            return False, f"Error opening port: {str(e)}"
    
    def disconnect(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.serial_port = None
        self.is_connected = False
    
    def read_data(self):
        if not self.serial_port or not self.serial_port.is_open:
            return        
        try:
            while self.serial_port.in_waiting > 0:
                line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    if ':' in line:
                        # Parse with tag (format: "tag:value")
                        parts = line.split(':', 1)
                        tag = parts[0].strip()
                        try:
                            value = float(parts[1].strip())
                            yield (tag, value)
                        except ValueError:
                            pass
                    else:
                        # Parse value without tag
                        try:
                            value = float(line)
                            yield ('default', value)
                        except ValueError:
                            pass
        except serial.SerialException as e:
            raise serial.SerialException(f"Serial error: {str(e)}")
