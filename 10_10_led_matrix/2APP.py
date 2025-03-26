import sys
import time
import serial
import random
import serial
import time

# Initialize serial connection (set to None initially)
ser = None

# Try to connect to Arduino
try:
    # Update the COM port to match your Arduino
    ser = serial.Serial('COM3', 9600, timeout=1)
    time.sleep(2)  # Wait for connection to establish
    print("Connected to Arduino on COM3")
except Exception as e:
    print(f"Failed to connect to Arduino: {e}")

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QLabel, QPushButton, QSlider, 
                            QComboBox, QLineEdit, QSpinBox, QMessageBox, QGroupBox,
                            QRadioButton, QButtonGroup, QCheckBox, QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette

# Global variables
arduino = None

# Try to connect to Arduino on COM5
try:
    # This will be replaced by the user-selected port in the settings
    # We don't connect here anymore - connection happens through the UI
    pass
except Exception as e:
    print(f"Error connecting to Arduino: {e}")

def send_command(cmd):
    """Send a command string to Arduino."""
    if arduino:
        try:
            arduino.write(f"{cmd}\n".encode())
            time.sleep(0.1)
            return arduino.readline().decode().strip()
        except Exception as e:
            print(f"Error sending command: {e}")
            return f"Error: {e}"
    else:
        print(f"Would send: {cmd}")
        return "Arduino not connected"

class LEDButton(QPushButton):
    """Custom button for LED matrix control"""
    def __init__(self, row, col, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.state = False
        self.setFixedSize(30, 30)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton { background-color: #444; border: 1px solid #666; border-radius: 15px; }
            QPushButton:checked { background-color: #ff0; }
        """)
        self.clicked.connect(self.toggle_state)
        
    def toggle_state(self):
        self.state = self.isChecked()
        
    def set_state(self, state):
        self.state = state
        self.setChecked(state)

class MarqueeThread(QThread):
    """Thread for running marquee text animation"""
    update_signal = pyqtSignal(list)
    finished_signal = pyqtSignal()
    
    def __init__(self, text, font_path, matrix_rows, matrix_cols, speed=100, direction="left"):
        super().__init__()
        self.text = text
        self.font_path = font_path
        self.matrix_rows = matrix_rows
        self.matrix_cols = matrix_cols
        self.speed = speed
        self.direction = direction
        self.running = False
        
    def stop(self):
        self.running = False


# Replace the deprecated getsize() method with getbbox()
    def run(self):
        self.running = True
        
        # Create a bitmap of the text
        try:
            font_size = max(8, self.matrix_rows - 2)  # Adjust font size based on matrix height
            font = ImageFont.truetype(self.font_path, font_size)
        except:
            # Fallback to default font
            font = ImageFont.load_default()
            
        # Get text dimensions using getbbox() instead of getsize()
        bbox = font.getbbox(self.text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Create image with enough width for scrolling
        img_width = text_width + 2 * self.matrix_cols
        img_height = max(text_height, self.matrix_rows)
        
        
        # Create image and draw text
        image = Image.new('1', (img_width, img_height), 0)
        draw = ImageDraw.Draw(image)
        draw.text((self.matrix_cols, 0), self.text, font=font, fill=1)
        
        # Convert to numpy array for easier manipulation
        bitmap = np.array(image)
        
        # Scroll the text
        if self.direction == "left":
            start_pos = 0
            end_pos = bitmap.shape[1] - self.matrix_cols
            step = 1
        else:  # right
            start_pos = bitmap.shape[1] - self.matrix_cols
            end_pos = 0
            step = -1
            
        pos = start_pos
        while self.running and ((step > 0 and pos <= end_pos) or (step < 0 and pos >= end_pos)):
            # Extract current view
            if pos + self.matrix_cols <= bitmap.shape[1]:
                current_view = bitmap[:, pos:pos+self.matrix_cols]
            else:
                # Handle edge case
                current_view = np.zeros((bitmap.shape[0], self.matrix_cols), dtype=np.uint8)
                current_view[:, :bitmap.shape[1]-pos] = bitmap[:, pos:]
            
            # Resize to match matrix dimensions if needed
            if current_view.shape[0] != self.matrix_rows or current_view.shape[1] != self.matrix_cols:
                # Pad or crop to match matrix dimensions
                padded_view = np.zeros((self.matrix_rows, self.matrix_cols), dtype=np.uint8)
                
                # Center vertically
                y_offset = (self.matrix_rows - current_view.shape[0]) // 2
                if y_offset >= 0:
                    # Pad
                    padded_view[y_offset:y_offset+current_view.shape[0], :current_view.shape[1]] = current_view
                else:
                    # Crop
                    padded_view[:, :current_view.shape[1]] = current_view[-y_offset:self.matrix_rows-y_offset, :]
                
                current_view = padded_view
            
            # Convert to list of lists for the LED matrix
            matrix = current_view.tolist()
            
            # Emit signal to update the UI
            self.update_signal.emit(matrix)
            
            # Send to Arduino
            send_led_matrix(matrix)
            
            # Move to next position
            pos += step
            
            # Delay based on speed
            delay = 1000 / self.speed  # Convert speed to milliseconds
            time.sleep(delay / 1000)  # Convert to seconds
        
        # Signal that we're done
        self.finished_signal.emit()



class AnimationThread(QThread):
    """Thread for running animations"""
    update_signal = pyqtSignal(list)
    finished_signal = pyqtSignal()
    
    def __init__(self, animation_type, matrix_rows, matrix_cols, speed=5):
        super().__init__()
        self.animation_type = animation_type
        self.matrix_rows = matrix_rows
        self.matrix_cols = matrix_cols
        self.speed = speed
        self.running = False
        
    def stop(self):
        self.running = False
        
    def run(self):
        self.running = True
        
        if self.animation_type == "blink":
            self.run_blink_animation()
        elif self.animation_type == "wave":
            self.run_wave_animation()
        elif self.animation_type == "spiral":
            self.run_spiral_animation()
        elif self.animation_type == "random":
            self.run_random_animation()
        elif self.animation_type == "rain":
            self.run_rain_animation()
        elif self.animation_type == "snake":
            self.run_snake_animation()
        
        # Signal that we're done
        self.finished_signal.emit()
    
    def run_blink_animation(self):
        """Run a simple blinking animation"""
        while self.running:
            # All on
            matrix = create_full_matrix(self.matrix_rows, self.matrix_cols)
            self.update_signal.emit(matrix)
            send_led_matrix(matrix)
            time.sleep(0.5 / self.speed)
            
            if not self.running:
                break
                
            # All off
            matrix = create_empty_matrix(self.matrix_rows, self.matrix_cols)
            self.update_signal.emit(matrix)
            send_led_matrix(matrix)
            time.sleep(0.5 / self.speed)
    
    def run_wave_animation(self):
        """Run a wave animation"""
        # Create empty matrix
        matrix = create_empty_matrix(self.matrix_rows, self.matrix_cols)
        
        # Run wave animation
        while self.running:
            # Horizontal wave
            for col in range(self.matrix_cols):
                for row in range(self.matrix_rows):
                    matrix[row][col] = 1
                
                self.update_signal.emit(matrix)
                send_led_matrix(matrix)
                time.sleep(0.1 / self.speed)
                
                if not self.running:
                    return
                
                # Clear column
                for row in range(self.matrix_rows):
                    matrix[row][col] = 0
            
            # Vertical wave
            for row in range(self.matrix_rows):
                for col in range(self.matrix_cols):
                    matrix[row][col] = 1
                
                self.update_signal.emit(matrix)
                send_led_matrix(matrix)
                time.sleep(0.1 / self.speed)
                
                if not self.running:
                    return
                
                # Clear row
                for col in range(self.matrix_cols):
                    matrix[row][col] = 0
    
    def run_spiral_animation(self):
        """Run a spiral animation"""
        # Create empty matrix
        matrix = create_empty_matrix(self.matrix_rows, self.matrix_cols)
        
        # Define spiral path
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # Right, Down, Left, Up
        dir_idx = 0
        row, col = 0, 0
        
        # Track visited cells
        visited = set()
        total_cells = self.matrix_rows * self.matrix_cols
        
        # Run spiral animation
        while self.running and len(visited) < total_cells:
            # Light up current cell
            matrix[row][col] = 1
            visited.add((row, col))
            
            self.update_signal.emit(matrix)
            send_led_matrix(matrix)
            time.sleep(0.1 / self.speed)
            
            if not self.running:
                return
            
            # Find next cell
            next_dir = directions[dir_idx]
            next_row, next_col = row + next_dir[0], col + next_dir[1]
            
            # Check if next cell is valid
            if (next_row < 0 or next_row >= self.matrix_rows or 
                next_col < 0 or next_col >= self.matrix_cols or 
                (next_row, next_col) in visited):
                # Change direction
                dir_idx = (dir_idx + 1) % 4
                next_dir = directions[dir_idx]
                next_row, next_col = row + next_dir[0], col + next_dir[1]
            
            row, col = next_row, next_col
        
        # Keep it lit for a moment
        time.sleep(0.5 / self.speed)
        
        # Clear in reverse
        for row, col in reversed(list(visited)):
            if not self.running:
                return
                
            matrix[row][col] = 0
            self.update_signal.emit(matrix)
            send_led_matrix(matrix)
            time.sleep(0.1 / self.speed)
    
    def run_random_animation(self):
        """Run a random animation"""
        # Create empty matrix
        matrix = create_empty_matrix(self.matrix_rows, self.matrix_cols)
        
        # Run random animation
        while self.running:
            # Randomly turn on/off LEDs
            for _ in range(10):  # Update 10 LEDs at a time
                row = random.randint(0, self.matrix_rows - 1)
                col = random.randint(0, self.matrix_cols - 1)
                matrix[row][col] = 1 - matrix[row][col]  # Toggle
            
            self.update_signal.emit(matrix)
            send_led_matrix(matrix)
            time.sleep(0.2 / self.speed)
    
    def run_rain_animation(self):
        """Run a rain animation"""
        # Create empty matrix
        matrix = create_empty_matrix(self.matrix_rows, self.matrix_cols)
        
        # Run rain animation
        while self.running:
            # Shift everything down
            for row in range(self.matrix_rows - 1, 0, -1):
                for col in range(self.matrix_cols):
                    matrix[row][col] = matrix[row - 1][col]
            
            # Add new raindrops at the top
            for col in range(self.matrix_cols):
                matrix[0][col] = 1 if random.random() < 0.3 else 0
            
            self.update_signal.emit(matrix)
            send_led_matrix(matrix)
            time.sleep(0.2 / self.speed)
    
    def run_snake_animation(self):
        """Run a snake animation"""
        # Create empty matrix
        matrix = create_empty_matrix(self.matrix_rows, self.matrix_cols)
        
        # Initial snake position
        snake = [(0, 0)]
        direction = (0, 1)  # Right
        
        # Run snake animation
        while self.running:
            # Clear matrix
            matrix = create_empty_matrix(self.matrix_rows, self.matrix_cols)
            
            # Draw snake
            for row, col in snake:
                matrix[row][col] = 1
            
            self.update_signal.emit(matrix)
            send_led_matrix(matrix)
            time.sleep(0.2 / self.speed)
            
            if not self.running:
                return
            
            # Move snake
            head_row, head_col = snake[-1]
            next_row = (head_row + direction[0]) % self.matrix_rows
            next_col = (head_col + direction[1]) % self.matrix_cols
            
            # Add new head
            snake.append((next_row, next_col))
            
            # Remove tail if snake is too long
            if len(snake) > 5:
                snake.pop(0)
            
            # Randomly change direction
            if random.random() < 0.2:
                directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # Right, Down, Left, Up
                direction = random.choice(directions)

class MarqueeApp(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.matrix_rows = 10  # Default matrix size
        self.matrix_cols = 10
        self.marquee_thread = None
        self.current_matrix = create_empty_matrix(self.matrix_rows, self.matrix_cols)
        self.led_buttons = []  # Store references to all LED buttons
        self.font_path = None  # Initialize font_path with a default value
        self.initUI()
        
    def initUI(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle("FILMDA: Smart Clapper")
        self.setGeometry(100, 100, 800, 600)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Create tabs
        self.setupMarqueeTab()
        self.setupManualTab()
        self.setupPatternTab()
        self.setupSettingsTab()
        
    def setupSettingsTab(self):
        """Set up the settings tab with matrix size configuration"""
        settings_tab = QWidget()
        layout = QVBoxLayout()
        
        # Matrix size group
        size_group = QGroupBox("LED Matrix Size")
        size_layout = QVBoxLayout()
        
        # Row and column inputs
        row_layout = QHBoxLayout()
        row_layout.addWidget(QLabel("Number of Rows:"))
        self.row_spinbox = QSpinBox()
        self.row_spinbox.setRange(1, 32)
        self.row_spinbox.setValue(self.matrix_rows)
        row_layout.addWidget(self.row_spinbox)
        size_layout.addLayout(row_layout)
        
        col_layout = QHBoxLayout()
        col_layout.addWidget(QLabel("Number of Columns:"))
        self.col_spinbox = QSpinBox()
        self.col_spinbox.setRange(1, 32)
        self.col_spinbox.setValue(self.matrix_cols)
        col_layout.addWidget(self.col_spinbox)
        size_layout.addLayout(col_layout)
        
        # Preset ratios
        ratio_layout = QHBoxLayout()
        ratio_layout.addWidget(QLabel("Preset Ratios:"))
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(["Custom", "8x8", "10x10", "16x16", "8x16", "16x8", "32x8"])
        self.ratio_combo.currentTextChanged.connect(self.applyMatrixRatio)
        ratio_layout.addWidget(self.ratio_combo)
        size_layout.addLayout(ratio_layout)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # Arduino connection group
        arduino_group = QGroupBox("Arduino Connection")
        arduino_layout = QVBoxLayout()
        
        # COM port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("COM Port:"))
        self.port_combo = QComboBox()
        
        # Populate available COM ports
        import serial.tools.list_ports
        available_ports = [port.device for port in serial.tools.list_ports.comports()]
        if not available_ports:
            available_ports = ["No ports available"]
        self.port_combo.addItems(available_ports)
        
        port_layout.addWidget(self.port_combo)
        arduino_layout.addLayout(port_layout)
        
        # Baud rate selection
        baud_layout = QHBoxLayout()
        baud_layout.addWidget(QLabel("Baud Rate:"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        baud_layout.addWidget(self.baud_combo)
        arduino_layout.addLayout(baud_layout)
        
        # Connect button
        connect_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connectArduino)
        connect_layout.addWidget(self.connect_button)
        arduino_layout.addLayout(connect_layout)
        
        arduino_group.setLayout(arduino_layout)
        layout.addWidget(arduino_group)
        
        # Apply button
        apply_layout = QHBoxLayout()
        apply_button = QPushButton("Apply Settings")
        apply_button.clicked.connect(self.applySettings)
        apply_layout.addWidget(apply_button)
        layout.addLayout(apply_layout)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        settings_tab.setLayout(layout)
        self.tabs.addTab(settings_tab, "Settings")
    
    def applyMatrixRatio(self, ratio_text):
        """Apply a preset matrix ratio"""
        if ratio_text == "Custom":
            return
            
        # Parse the ratio
        parts = ratio_text.split('x')
        if len(parts) == 2:
            try:
                rows = int(parts[0])
                cols = int(parts[1])
                
                # Update spinboxes
                self.row_spinbox.setValue(rows)
                self.col_spinbox.setValue(cols)
            except ValueError:
                pass
    
    def updateMatrixSize(self):
        """Update matrix size based on spinbox values"""
        self.matrix_rows = self.row_spinbox.value()
        self.matrix_cols = self.col_spinbox.value()
    
    def applySettings(self):
        """Apply the settings changes"""
        # Get the old size
        old_rows = self.matrix_rows
        old_cols = self.matrix_cols
        
        # Update matrix size
        self.updateMatrixSize()
        
        # Check if size changed
        if old_rows != self.matrix_rows or old_cols != self.matrix_cols:
            # Rebuild the manual tab
            self.rebuildManualTab()
            
            # Reset the current matrix
            self.current_matrix = create_empty_matrix(self.matrix_rows, self.matrix_cols)
            
            # Update the UI
            QMessageBox.information(self, "Settings Applied", 
                                   f"Matrix size updated to {self.matrix_rows}x{self.matrix_cols}")
        else:
            QMessageBox.information(self, "Settings Applied", "Settings applied successfully")
    
    def connectArduino(self):
        """Connect to Arduino with selected settings"""
        global arduino
        
        # Get selected port and baud rate
        port = self.port_combo.currentText()
        baud = int(self.baud_combo.currentText())
        
        try:
            # Close existing connection if any
            if arduino:
                arduino.close()
            
            # Connect to Arduino
            arduino = serial.Serial(port=port, baudrate=baud, timeout=1)
            print(f"Connected to Arduino on {port} at {baud} baud")
            QMessageBox.information(self, "Connection Successful", 
                                   f"Connected to Arduino on {port} at {baud} baud")
            return True
        except Exception as e:
            print(f"Error connecting to Arduino: {e}")
            QMessageBox.warning(self, "Connection Failed", 
                               f"Error connecting to Arduino: {str(e)}")
            return False
    
    def rebuildManualTab(self):
        """Rebuild the manual tab with the new matrix size"""
        # Remove the old tab
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Manual LED Control":
                self.tabs.removeTab(i)
                break
        
        # Create a new tab
        self.setupManualTab()
    
    def setupMarqueeTab(self):
        """Set up the marquee text tab"""
        marquee_tab = QWidget()
        layout = QVBoxLayout()
        
        # Text input
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Text:"))
        self.text_input = QLineEdit()
        self.text_input.setText("Hello World")
        text_layout.addWidget(self.text_input)
        layout.addLayout(text_layout)
        
        # Font selection
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font:"))
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Default", "Arial", "Times New Roman", "Courier New"])
        self.font_combo.currentIndexChanged.connect(self.selectFont)
        font_layout.addWidget(self.font_combo)
        layout.addLayout(font_layout)
        
        # Direction selection
        direction_layout = QHBoxLayout()
        direction_layout.addWidget(QLabel("Direction:"))
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Left to Right", "Right to Left"])
        direction_layout.addWidget(self.direction_combo)
        layout.addLayout(direction_layout)
        
        # Speed control
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 20)
        self.speed_slider.setValue(5)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(1)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(QLabel("Slow"))
        speed_layout.addWidget(QLabel("Fast"))
        layout.addLayout(speed_layout)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.startMarquee)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stopMarquee)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        layout.addLayout(control_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        marquee_tab.setLayout(layout)
        self.tabs.addTab(marquee_tab, "Marquee Text")
    
    def setupManualTab(self):
        """Set up the manual LED control tab"""
        manual_tab = QWidget()
        main_layout = QVBoxLayout()
        
        # LED matrix grid
        grid_layout = QGridLayout()
        grid_layout.setSpacing(2)
        
        # Create LED buttons
        self.led_buttons = []
        for row in range(self.matrix_rows):
            row_buttons = []
            for col in range(self.matrix_cols):
                button = LEDButton(row, col)
                button.clicked.connect(self.updateMatrix)
                grid_layout.addWidget(button, row, col)
                row_buttons.append(button)
            self.led_buttons.append(row_buttons)
        
        # Add grid to a group box
        grid_group = QGroupBox("LED Matrix")
        grid_group.setLayout(grid_layout)
        main_layout.addWidget(grid_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self.clearMatrix)
        control_layout.addWidget(clear_button)
        
        fill_button = QPushButton("Fill All")
        fill_button.clicked.connect(self.fillMatrix)
        control_layout.addWidget(fill_button)
        
        invert_button = QPushButton("Invert")
        invert_button.clicked.connect(self.invertMatrix)
        control_layout.addWidget(invert_button)
        
        send_button = QPushButton("Send to Arduino")
        send_button.clicked.connect(self.sendMatrix)
        control_layout.addWidget(send_button)
        
        main_layout.addLayout(control_layout)
        
        # Brightness control
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("Brightness:"))
        brightness_slider = QSlider(Qt.Horizontal)
        brightness_slider.setRange(0, 255)
        brightness_slider.setValue(128)
        brightness_slider.valueChanged.connect(self.setBrightness)
        brightness_layout.addWidget(brightness_slider)
        main_layout.addLayout(brightness_layout)
        
        manual_tab.setLayout(main_layout)
        self.tabs.addTab(manual_tab, "Manual LED Control")
    
    def setupPatternTab(self):
        """Set up the pattern tab"""
        pattern_tab = QWidget()
        layout = QVBoxLayout()
        
        # Pattern selection
        pattern_group = QGroupBox("Patterns")
        pattern_layout = QGridLayout()
        
        # Add pattern buttons
        patterns = [
            ("Checkerboard", self.applyPattern, "checkerboard"),
            ("Horizontal Lines", self.applyPattern, "horizontal_lines"),
            ("Vertical Lines", self.applyPattern, "vertical_lines"),
            ("Border", self.applyPattern, "border"),
            ("X Pattern", self.applyPattern, "x_pattern"),
            ("Heart", self.applyPattern, "heart"),
            ("Smiley", self.applyPattern, "smiley"),
            ("Random", self.applyPattern, "random")
        ]
        
        row, col = 0, 0
        for name, func, pattern in patterns:
            button = QPushButton(name)
            button.clicked.connect(lambda checked, p=pattern: func(p))
            pattern_layout.addWidget(button, row, col)
            
            col += 1
            if col > 3:  # 4 buttons per row
                col = 0
                row += 1
        
        pattern_group.setLayout(pattern_layout)
        layout.addWidget(pattern_group)
        
        # Animation controls
        animation_group = QGroupBox("Animations")
        animation_layout = QVBoxLayout()
        
        # Animation type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Animation Type:"))
        self.animation_combo = QComboBox()
        self.animation_combo.addItems(["Blink", "Wave", "Spiral", "Random", "Rain", "Snake"])
        type_layout.addWidget(self.animation_combo)
        animation_layout.addLayout(type_layout)
        
        # Animation speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.animation_speed = QSlider(Qt.Horizontal)
        self.animation_speed.setRange(1, 10)
        self.animation_speed.setValue(5)
        speed_layout.addWidget(self.animation_speed)
        animation_layout.addLayout(speed_layout)
        
        # Animation controls
        control_layout = QHBoxLayout()
        self.start_animation_button = QPushButton("Start Animation")
        self.start_animation_button.clicked.connect(self.startAnimation)
        control_layout.addWidget(self.start_animation_button)
        
        self.stop_animation_button = QPushButton("Stop Animation")
        self.stop_animation_button.clicked.connect(self.stopAnimation)
        self.stop_animation_button.setEnabled(False)
        control_layout.addWidget(self.stop_animation_button)
        animation_layout.addLayout(control_layout)
        
        animation_group.setLayout(animation_layout)
        layout.addWidget(animation_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        pattern_tab.setLayout(layout)
        self.tabs.addTab(pattern_tab, "Patterns")
    
    def updateMatrix(self):
        """Update the matrix based on button states"""
        for row in range(self.matrix_rows):
            for col in range(self.matrix_cols):
                self.current_matrix[row][col] = 1 if self.led_buttons[row][col].state else 0
    
    def clearMatrix(self):
        """Clear all LEDs in the matrix"""
        for row in range(self.matrix_rows):
            for col in range(self.matrix_cols):
                self.led_buttons[row][col].set_state(False)
        
        self.updateMatrix()
        self.sendMatrix()
    
    def fillMatrix(self):
        """Fill all LEDs in the matrix"""
        for row in range(self.matrix_rows):
            for col in range(self.matrix_cols):
                self.led_buttons[row][col].set_state(True)
        
        self.updateMatrix()
        self.sendMatrix()
    
    def invertMatrix(self):
        """Invert all LEDs in the matrix"""
        for row in range(self.matrix_rows):
            for col in range(self.matrix_cols):
                current_state = self.led_buttons[row][col].state
                self.led_buttons[row][col].set_state(not current_state)
        
        self.updateMatrix()
        self.sendMatrix()
    
    def sendMatrix(self):
        """Send the current matrix to Arduino"""
        send_led_matrix(self.current_matrix)
    
    def setBrightness(self, value):
        """Set the brightness of the LED matrix"""
        send_command(f"B{value}")
    
    def selectFont(self, index):
        """Select a font for the marquee text"""
        # Default font paths
        font_paths = [
            None,  # Default
            "arial.ttf",
            "times.ttf",
            "cour.ttf"
        ]
        
        self.font_path = font_paths[index]
    

    def startMarquee(self):
        """Start the marquee text animation"""
        # Get text and direction
        text = self.text_input.text()
        if not text:
            QMessageBox.warning(self, "Error", "Please enter some text")
            return
        
        direction = "left" if self.direction_combo.currentText() == "Right to Left" else "right"
        speed = self.speed_slider.value()
        
        # Use a default font if none is selected
        if not hasattr(self, 'font_path') or self.font_path is None:
            self.font_path = None  # None will use the default font
        
        # Stop any existing thread
        self.stopMarquee()
        
        # Create and start new thread
        self.marquee_thread = MarqueeThread(text, self.font_path, self.matrix_rows, self.matrix_cols, speed, direction)
        self.marquee_thread.update_signal.connect(self.updateLEDMatrix)
        self.marquee_thread.finished_signal.connect(self.marqueeFinished)
        self.marquee_thread.start()
        
        # Update UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Running marquee...")
    
    def stopMarquee(self):
        """Stop the marquee text animation"""
        if self.marquee_thread and self.marquee_thread.isRunning():
            self.marquee_thread.stop()
            self.marquee_thread.wait()
        
        # Update UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Ready")
    
    def marqueeFinished(self):
        """Called when the marquee animation finishes"""
        # Update UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Ready")
        
        # Clear the LED matrix
        matrix = create_empty_matrix(self.matrix_rows, self.matrix_cols)
        self.updateLEDMatrix(matrix)
    
    def updateLEDMatrix(self, matrix):
        """Update the LED matrix display in the manual tab"""
        # Check if we have a valid manual tab with buttons
        if not self.led_buttons:
            return
            
        # Update button states based on matrix
        for row in range(min(len(matrix), self.matrix_rows)):
            for col in range(min(len(matrix[row]), self.matrix_cols)):
                state = bool(matrix[row][col])
                if row < len(self.led_buttons) and col < len(self.led_buttons[row]):
                    self.led_buttons[row][col].set_state(state)
        
        # Update the current matrix
        self.current_matrix = matrix
    
    def applyPattern(self, pattern):
        """Apply a predefined pattern to the matrix"""
        # Create empty matrix
        matrix = create_empty_matrix(self.matrix_rows, self.matrix_cols)
        
        if pattern == "checkerboard":
            # Create checkerboard pattern
            for row in range(self.matrix_rows):
                for col in range(self.matrix_cols):
                    matrix[row][col] = (row + col) % 2
        
        elif pattern == "horizontal_lines":
            # Create horizontal lines
            for row in range(self.matrix_rows):
                if row % 2 == 0:
                    for col in range(self.matrix_cols):
                        matrix[row][col] = 1
        
        elif pattern == "vertical_lines":
            # Create vertical lines
            for col in range(self.matrix_cols):
                if col % 2 == 0:
                    for row in range(self.matrix_rows):
                        matrix[row][col] = 1
        
        elif pattern == "border":
            # Create border
            for row in range(self.matrix_rows):
                for col in range(self.matrix_cols):
                    if (row == 0 or row == self.matrix_rows - 1 or 
                        col == 0 or col == self.matrix_cols - 1):
                        matrix[row][col] = 1
        
        elif pattern == "x_pattern":
            # Create X pattern
            for row in range(self.matrix_rows):
                for col in range(self.matrix_cols):
                    if (row == col or row == self.matrix_cols - col - 1):
                        matrix[row][col] = 1
        
        elif pattern == "heart":
            # Create heart pattern (works best with at least 7x7 matrix)
            # Simple heart shape
            heart_pattern = [
                [0, 1, 1, 0, 1, 1, 0],
                [1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1, 1, 1],
                [0, 1, 1, 1, 1, 1, 0],
                [0, 0, 1, 1, 1, 0, 0],
                [0, 0, 0, 1, 0, 0, 0]
            ]
            
            # Center the pattern in the matrix
            offset_row = (self.matrix_rows - len(heart_pattern)) // 2
            offset_col = (self.matrix_cols - len(heart_pattern[0])) // 2
            
            for r, row in enumerate(heart_pattern):
                if offset_row + r < 0 or offset_row + r >= self.matrix_rows:
                    continue
                    
                for c, val in enumerate(row):
                    if offset_col + c < 0 or offset_col + c >= self.matrix_cols:
                        continue
                        
                    matrix[offset_row + r][offset_col + c] = val
        
        elif pattern == "smiley":
            # Create smiley pattern (works best with at least 8x8 matrix)
            # Simple smiley face
            smiley_pattern = [
                [0, 0, 1, 1, 1, 1, 0, 0],
                [0, 1, 0, 0, 0, 0, 1, 0],
                [1, 0, 1, 0, 0, 1, 0, 1],
                [1, 0, 0, 0, 0, 0, 0, 1],
                [1, 0, 1, 0, 0, 1, 0, 1],
                [1, 0, 0, 1, 1, 0, 0, 1],
                [0, 1, 0, 0, 0, 0, 1, 0],
                [0, 0, 1, 1, 1, 1, 0, 0]
            ]
            
            # Center the pattern in the matrix
            offset_row = (self.matrix_rows - len(smiley_pattern)) // 2
            offset_col = (self.matrix_cols - len(smiley_pattern[0])) // 2
            
            for r, row in enumerate(smiley_pattern):
                if offset_row + r < 0 or offset_row + r >= self.matrix_rows:
                    continue
                    
                for c, val in enumerate(row):
                    if offset_col + c < 0 or offset_col + c >= self.matrix_cols:
                        continue
                        
                    matrix[offset_row + r][offset_col + c] = val
        
        elif pattern == "random":
            # Create random pattern
            for row in range(self.matrix_rows):
                for col in range(self.matrix_cols):
                    matrix[row][col] = random.randint(0, 1)
        
        # Update the matrix display
        self.updateLEDMatrix(matrix)
        self.sendMatrix()
    
    def startAnimation(self):
        """Start an animation"""
        # Get animation type and speed
        animation_type = self.animation_combo.currentText().lower()
        speed = self.animation_speed.value()
        
        # Stop any existing animation
        self.stopAnimation()
        
        # Create and start new thread
        self.animation_thread = AnimationThread(animation_type, self.matrix_rows, self.matrix_cols, speed)
        self.animation_thread.update_signal.connect(self.updateLEDMatrix)
        self.animation_thread.finished_signal.connect(self.animationFinished)
        self.animation_thread.start()
        
        # Update UI
        self.start_animation_button.setEnabled(False)
        self.stop_animation_button.setEnabled(True)
    
    def stopAnimation(self):
        """Stop the current animation"""
        if hasattr(self, 'animation_thread') and self.animation_thread and self.animation_thread.isRunning():
            self.animation_thread.stop()
            self.animation_thread.wait()
        
        # Update UI
        self.start_animation_button.setEnabled(True)
        self.stop_animation_button.setEnabled(False)
    
    def animationFinished(self):
        """Called when an animation finishes"""
        # Update UI
        self.start_animation_button.setEnabled(True)
        self.stop_animation_button.setEnabled(False)
        
        # Clear the LED matrix
        matrix = create_empty_matrix(self.matrix_rows, self.matrix_cols)
        self.updateLEDMatrix(matrix)

def send_led_matrix(matrix):
    """Send LED matrix to Arduino"""
    global ser
    try:
        # Convert the matrix to a binary string (0s and 1s)
        binary_data = ""
        for row in matrix:
            for cell in row:
                # Convert True/False to 1/0
                binary_data += "1" if cell else "0"
        
        # Format the command with matrix dimensions and binary data
        command = f"W{len(matrix)},{len(matrix[0])},{binary_data}\n"
        
        # Send to Arduino if serial is available
        if ser and ser.is_open:
            ser.write(command.encode())
            print(f"Sent: {command}")
        else:
            print("Serial connection not available")
    except Exception as e:
        print(f"Error sending to Arduino: {e}")
        

def create_empty_matrix(rows=10, cols=10):
    """Create an empty matrix with specified dimensions (all LEDs off)"""
    return [[0 for _ in range(cols)] for _ in range(rows)]

def create_full_matrix(rows=10, cols=10):
    """Create a full matrix with specified dimensions (all LEDs on)"""
    return [[1 for _ in range(cols)] for _ in range(rows)]

if __name__ == "__main__":
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    window = MarqueeApp()
    window.show()
    sys.exit(app.exec_())