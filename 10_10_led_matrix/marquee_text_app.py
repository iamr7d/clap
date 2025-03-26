import sys
import os
import serial
import time 
import numpy as np

from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QSlider, QComboBox, QSpinBox, QCheckBox, QGroupBox,
                            QGridLayout, QTabWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QPalette

# Initialize QApplication first before any widgets
app = QApplication(sys.argv)

# Connect to Arduino on COM5
try:
    arduino = serial.Serial(port='COM5', baudrate=9600, timeout=1)
    print("Connected to Arduino on COM5")
except Exception as e:
    print(f"Error connecting to Arduino: {e}")
    arduino = None

def send_command(cmd):
    """Send a command string to Arduino."""
    if arduino:
        arduino.write(f"{cmd}\n".encode())
        time.sleep(0.1)
        return arduino.readline().decode().strip()
    else:
        print(f"Would send: {cmd}")
        return "Arduino not connected"

# In marquee_text_app.py
def send_led_matrix(matrix):
    """Send a 10x10 LED matrix as a 100-character string to Arduino."""
    # Send the matrix as-is without flipping
    data_str = 'W' + ''.join(str(cell) for row in matrix for cell in row)
    print("Sending Matrix Data:", data_str)
    return send_command(data_str)
    
def create_empty_matrix():
    """Create an empty 10x10 matrix (all LEDs off)"""
    return [[0 for _ in range(10)] for _ in range(10)]

def create_full_matrix():
    """Create a full 10x10 matrix (all LEDs on)"""
    return [[1 for _ in range(10)] for _ in range(10)]

# LED Button for the interactive grid
class LEDButton(QPushButton):
    def __init__(self, row, col):
        super().__init__()
        self.row = row
        self.col = col
        self.state = 0  # 0 = off, 1 = on
        self.setFixedSize(30, 30)
        self.updateStyle()
        self.clicked.connect(self.toggle)

    def update_matrix(self, matrix):
        # Display the matrix as-is in the UI
        if self.tabs.currentIndex() == 0:  # Marquee tab
            for r in range(10):
                for c in range(10):
                    self.marquee_led_buttons[r][c].setState(matrix[r][c])
        else:  # Manual tab
            for r in range(10):
                for c in range(10):
                    self.led_buttons[r][c].setState(matrix[r][c])
        
        # Store the original matrix
        self.current_matrix = matrix
    def toggle(self):
        self.state = 1 if self.state == 0 else 0
        self.updateStyle()
    
    def updateStyle(self):
        if self.state == 1:
            self.setStyleSheet("background-color: #FFFF00; border: 1px solid black;")
        else:
            self.setStyleSheet("background-color: #444444; border: 1px solid black;")
    
    def setState(self, state):
        self.state = state
        self.updateStyle()

# Worker thread for running the marquee animation
class MarqueeThread(QThread):
    update_signal = pyqtSignal(str)  # Signal to update UI
    matrix_signal = pyqtSignal(list)  # Signal to update LED grid
    finished_signal = pyqtSignal()   # Signal when animation is complete
    
    def __init__(self, text, speed, loops, font_path, font_size, invert, 
                 direction="Right to Left", flip_horizontal=True, color=1):
        super().__init__()
        self.text = text
        self.speed = speed
        self.loops = loops
        self.font_path = font_path
        # Limit font size to ensure it fits in the 10x10 matrix
        self.font_size = min(font_size, 9)  # Cap at 9 pixels to ensure visibility
        self.invert = invert
        self.direction = direction
        self.flip_horizontal = flip_horizontal
        self.color = color
        self.running = True
    
    def stop(self):
        self.running = False
        
    def run(self):
        try:
            self.update_signal.emit(f"Starting marquee: '{self.text}'")
            
            # Reset the Arduino
            send_command("R")
            time.sleep(0.1)
            
            # Load font
            try:
                font = ImageFont.truetype(self.font_path, self.font_size)
                self.update_signal.emit(f"Using font: {self.font_path}")
            except Exception as e:
                # Try to load Gotham Black as a fallback
                gotham_path = "C:/Users/rahul/OneDrive/Desktop/10_10_led_matrix/10_10_led_matrix/Gotham-Font/Gotham-Black.otf"
                try:
                    font = ImageFont.truetype(gotham_path, self.font_size)
                    self.update_signal.emit(f"Using default Gotham Black font")
                except Exception as e2:
                    self.update_signal.emit(f"Error loading fonts: {e}. Using system default.")
                    font = ImageFont.load_default()
            
            # Handle different directions
            if self.direction == "Left to Right":
                self._scroll_left_to_right(font)
            elif self.direction == "Right to Left":
                self._scroll_right_to_left(font)
            elif self.direction == "Top to Bottom":
                self._scroll_top_to_bottom(font)
            elif self.direction == "Bottom to Top":
                self._scroll_bottom_to_top(font)
            elif "Diagonal" in self.direction:
                self._scroll_diagonal(font)
            else:
                # Default to right to left
                self._scroll_right_to_left(font)
                
            self.update_signal.emit("Marquee complete")
            self.finished_signal.emit()
        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")
            self.finished_signal.emit()
    
    def _scroll_right_to_left(self, font):
        # Create a wide image to hold the scrolling text
        width = 10 + len(self.text) * 8  # Each character is roughly 6-8 pixels wide
        img = Image.new('1', (width, 8), 0)
        draw = ImageDraw.Draw(img)
        
        # Draw the text with adjusted vertical position
        draw.text((10, -2), self.text, fill=self.color, font=font)
        
        # Invert if requested
        if self.invert:
            img = Image.eval(img, lambda px: 1 - px)
        
        # Flip horizontally if needed
        if self.flip_horizontal:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        
        # Convert to numpy array for easier manipulation
        img_array = np.array(img)
        
        # Loop count tracking
        loop_count = 0
        
        # Scroll the text from right to left
        for pos in range(width - 10):
            if not self.running:
                break
                
            # Extract the current window
            window = img_array[:, pos:pos+10].copy()
            
            # Ensure the window is exactly 8x10
            if window.shape[1] < 10:
                # Pad with zeros if needed
                padding = np.zeros((8, 10 - window.shape[1]), dtype=window.dtype)
                window = np.hstack((window, padding))
            
            # Create a 10x10 matrix with the first 2 rows empty
            matrix = create_empty_matrix()  # Start with all zeros
            for r in range(8):
                for c in range(10):
                    matrix[r+2][c] = int(window[r][c]) if c < window.shape[1] else 0
            
            # Update the UI and send to Arduino
            self._update_and_send(matrix)
            
            # Check for loop completion
            if pos == width - 11:
                loop_count += 1
                self._check_loops(loop_count)
                if not self.running:
                    break
    
    def _scroll_left_to_right(self, font):
        # Similar to right_to_left but with reversed position
        width = 10 + len(self.text) * 8
        img = Image.new('1', (width, 8), 0)
        draw = ImageDraw.Draw(img)
        
        draw.text((10, -2), self.text, fill=self.color, font=font)
        
        if self.invert:
            img = Image.eval(img, lambda px: 1 - px)
        
        # No need to flip horizontally for left-to-right
        
        img_array = np.array(img)
        loop_count = 0
        
        # Scroll from left to right
        for pos in range(width - 10, -1, -1):  # Reverse direction
            if not self.running:
                break
                
            window = img_array[:, pos:pos+10].copy()
            
            if window.shape[1] < 10:
                padding = np.zeros((8, 10 - window.shape[1]), dtype=window.dtype)
                window = np.hstack((window, padding))
            
            matrix = create_empty_matrix()
            for r in range(8):
                for c in range(10):
                    matrix[r+2][c] = int(window[r][c]) if c < window.shape[1] else 0
            
            self._update_and_send(matrix)
            
            if pos == 0:
                loop_count += 1
                self._check_loops(loop_count)
                if not self.running:
                    break
    
    def _scroll_top_to_bottom(self, font):
        # Create a tall image for vertical scrolling
        height = 10 + len(self.text) * 8
        img = Image.new('1', (8, height), 0)
        draw = ImageDraw.Draw(img)
        
        # Rotate text 90 degrees
        img_rot = Image.new('1', (height, 8), 0)
        draw_rot = ImageDraw.Draw(img_rot)
        draw_rot.text((10, -2), self.text, fill=self.color, font=font)
        img_rot = img_rot.rotate(90, expand=True)
        
        # Copy rotated image to our vertical image
        img.paste(img_rot, (0, 0))
        
        if self.invert:
            img = Image.eval(img, lambda px: 1 - px)
        
        img_array = np.array(img)
        loop_count = 0
        
        # Scroll from top to bottom
        for pos in range(height - 8):
            if not self.running:
                break
                
            # Extract horizontal slice
            window = img_array[pos:pos+8, :].copy()
            
            matrix = create_empty_matrix()
            for r in range(8):
                for c in range(8):  # Only use 8 columns
                    if r < window.shape[0] and c < window.shape[1]:
                        matrix[r+2][c+1] = int(window[r][c])  # Center horizontally
            
            self._update_and_send(matrix)
            
            if pos == height - 9:
                loop_count += 1
                self._check_loops(loop_count)
                if not self.running:
                    break
    
    def _scroll_bottom_to_top(self, font):
        # Similar to top_to_bottom but with reversed position
        height = 10 + len(self.text) * 8
        img = Image.new('1', (8, height), 0)
        draw = ImageDraw.Draw(img)
        
        # Rotate text 90 degrees
        img_rot = Image.new('1', (height, 8), 0)
        draw_rot = ImageDraw.Draw(img_rot)
        draw_rot.text((10, -2), self.text, fill=self.color, font=font)
        img_rot = img_rot.rotate(90, expand=True)
        
        # Copy rotated image to our vertical image
        img.paste(img_rot, (0, 0))
        
        if self.invert:
            img = Image.eval(img, lambda px: 1 - px)
        
        img_array = np.array(img)
        loop_count = 0
        
        # Scroll from bottom to top
        for pos in range(height - 8, -1, -1):  # Reverse direction
            if not self.running:
                break
                
            # Extract horizontal slice
            window = img_array[pos:pos+8, :].copy() if pos+8 <= height else img_array[pos:, :].copy()
            
            matrix = create_empty_matrix()
            for r in range(min(8, window.shape[0])):
                for c in range(8):  # Only use 8 columns
                    if c < window.shape[1]:
                        matrix[r+2][c+1] = int(window[r][c])  # Center horizontally
            
            self._update_and_send(matrix)
            
            if pos == 0:
                loop_count += 1
                self._check_loops(loop_count)
                if not self.running:
                    break
    
    def _scroll_diagonal(self, font):
        # This is a simplified implementation
        width = 10 + len(self.text) * 8
        height = 10 + len(self.text) * 8
        img = Image.new('1', (width, height), 0)
        draw = ImageDraw.Draw(img)
        
        draw.text((10, 10), self.text, fill=self.color, font=font)
        
        if self.invert:
            img = Image.eval(img, lambda px: 1 - px)
        
        img_array = np.array(img)
        loop_count = 0
        
        # Diagonal scrolling (simplified)
        for pos in range(width + height - 10):
            if not self.running:
                break
                
            matrix = create_empty_matrix()
            for r in range(10):
                for c in range(10):
                    x = c + pos - r
                    y = r
                    if 0 <= x < width and 0 <= y < height:
                        matrix[r][c] = int(img_array[y][x])
            
            self._update_and_send(matrix)
            
            if pos == width + height - 11:
                loop_count += 1
                self._check_loops(loop_count)
                if not self.running:
                    break
    
    def _update_and_send(self, matrix):
        # Update the UI
        self.matrix_signal.emit(matrix)
        
        # Send to Arduino
        send_led_matrix(matrix)
        
        # Pause based on speed
        time.sleep(self.speed)
    
    def _check_loops(self, loop_count):
        self.update_signal.emit(f"Loop {loop_count}/{self.loops}")
        
        # Check if we've reached the desired number of loops
        if self.loops > 0 and loop_count >= self.loops:
            self.running = False

class MarqueeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.marquee_thread = None
        self.current_matrix = create_empty_matrix()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('10x10 LED Matrix Controller')
        self.setGeometry(100, 100, 800, 600)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.marquee_tab = QWidget()
        self.manual_tab = QWidget()
        
        self.tabs.addTab(self.marquee_tab, "Marquee Text")
        self.tabs.addTab(self.manual_tab, "Manual LED Control")
        
        # Set up marquee tab
        self.setupMarqueeTab()
        
        # Set up manual control tab
        self.setupManualTab()
        
        # Set the central widget
        self.setCentralWidget(self.tabs)
    
    def setupMarqueeTab(self):
        # Main layout for marquee tab
        main_layout = QVBoxLayout()
        
        # Text input section
        text_group = QGroupBox("Marquee Text")
        text_layout = QVBoxLayout()
        
        text_input_layout = QHBoxLayout()
        text_input_layout.addWidget(QLabel("Text:"))
        self.text_input = QLineEdit("HELLO WORLD")
        text_input_layout.addWidget(self.text_input)
        text_layout.addLayout(text_input_layout)
        
        text_group.setLayout(text_layout)
        main_layout.addWidget(text_group)
        
        # Animation settings
        anim_group = QGroupBox("Animation Settings")
        anim_layout = QVBoxLayout()
        
        # Speed slider
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(5, 50)  # 0.05s to 0.5s
        self.speed_slider.setValue(20)  # Default 0.2s
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("0.20s")
        speed_layout.addWidget(self.speed_label)
        anim_layout.addLayout(speed_layout)
        
        # Connect slider to update label
        self.speed_slider.valueChanged.connect(self.update_speed_label)
        
        # Loops
        loops_layout = QHBoxLayout()
        loops_layout.addWidget(QLabel("Loops:"))
        self.loops_spin = QSpinBox()
        self.loops_spin.setRange(0, 100)  # 0 = infinite
        self.loops_spin.setValue(1)
        loops_layout.addWidget(self.loops_spin)
        loops_layout.addWidget(QLabel("(0 = infinite)"))
        anim_layout.addLayout(loops_layout)
        
        # Direction
        direction_layout = QHBoxLayout()
        direction_layout.addWidget(QLabel("Direction:"))
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Right to Left", "Left to Right", "Top to Bottom", "Bottom to Top"])
        direction_layout.addWidget(self.direction_combo)
        anim_layout.addLayout(direction_layout)
        
        # Color options
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(["White", "Red", "Green", "Blue", "Yellow"])
        self.color_combo.setCurrentIndex(0)  # Default to White
        color_layout.addWidget(self.color_combo)
        anim_layout.addLayout(color_layout)
        
        # Font selection
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font:"))
        self.font_combo = QComboBox()
        
        # Add available fonts
        font_dir = "C:/Users/rahul/OneDrive/Desktop/10_10_led_matrix/10_10_led_matrix/Gotham-Font"
        default_font = None
        
        if os.path.exists(font_dir):
            for file in os.listdir(font_dir):
                if file.endswith(('.ttf', '.otf')):
                    font_path = os.path.join(font_dir, file)
                    self.font_combo.addItem(file, font_path)
                    if "Black" in file:  # Set Gotham Black as default
                        default_font = self.font_combo.count() - 1
        
        # Add system default font
        self.font_combo.addItem("System Default", "")
        
        if default_font is not None:
            self.font_combo.setCurrentIndex(default_font)
        else:
            self.font_combo.setCurrentIndex(0)
            
        font_layout.addWidget(self.font_combo)
        anim_layout.addLayout(font_layout)
        
        # Font size
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("Font Size:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 12)
        self.font_size_spin.setValue(8)
        font_size_layout.addWidget(self.font_size_spin)
        anim_layout.addLayout(font_size_layout)
        
        # Invert checkbox
        invert_layout = QHBoxLayout()
        self.invert_check = QCheckBox("Invert Colors")
        invert_layout.addWidget(self.invert_check)
        anim_layout.addLayout(invert_layout)
        
        # Flip horizontal checkbox
        flip_layout = QHBoxLayout()
        self.flip_check = QCheckBox("Flip Horizontal")
        self.flip_check.setChecked(True)  # Default to checked
        flip_layout.addWidget(self.flip_check)
        anim_layout.addLayout(flip_layout)
        
        anim_group.setLayout(anim_layout)
        main_layout.addWidget(anim_group)
        
        # Port selection
        port_group = QGroupBox("Arduino Connection")
        port_layout = QHBoxLayout()
        
        port_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        
        # Add common COM ports
        for i in range(1, 11):
            self.port_combo.addItem(f"COM{i}")
        
        # Set default to COM5
        index = self.port_combo.findText("COM5")
        if index >= 0:
            self.port_combo.setCurrentIndex(index)
            
        port_layout.addWidget(self.port_combo)
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_arduino)
        port_layout.addWidget(self.connect_button)
        
        port_group.setLayout(port_layout)
        main_layout.addWidget(port_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Marquee")
        self.start_button.clicked.connect(self.start_marquee)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_marquee)
        control_layout.addWidget(self.stop_button)
        
        main_layout.addLayout(control_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
        
        self.marquee_tab.setLayout(main_layout)
    
    def connect_to_arduino(self):
        global arduino
        port = self.port_combo.currentText()
        try:
            if arduino:
                arduino.close()
            arduino = serial.Serial(port=port, baudrate=9600, timeout=1)
            self.status_label.setText(f"Connected to Arduino on {port}")
        except Exception as e:
            self.status_label.setText(f"Error connecting to Arduino: {e}")
            arduino = None
    
    def update_speed_label(self, value):
        speed = value / 100.0
        self.speed_label.setText(f"{speed:.2f}s")
    
    def start_marquee(self):
        # Stop any existing thread
        if self.marquee_thread and self.marquee_thread.isRunning():
            self.marquee_thread.stop()
            self.marquee_thread.wait()
        
        text = self.text_input.text()
        if not text:
            self.status_label.setText("Error: Please enter some text")
            return
            
        # Get settings
        speed = self.speed_slider.value() / 100.0
        loops = self.loops_spin.value()
        font_path = self.font_combo.currentData()
        font_size = self.font_size_spin.value()
        invert = self.invert_check.isChecked()
        flip_horizontal = self.flip_check.isChecked()
        direction = self.direction_combo.currentText()
        color_text = self.color_combo.currentText()
        color = 1  # Default white
        
        self.marquee_thread = MarqueeThread(
            text, speed, loops, font_path, font_size, invert, 
            direction=direction, flip_horizontal=flip_horizontal, color=color
        )
        
        # Connect signals
        self.marquee_thread.update_signal.connect(self.update_status)
        self.marquee_thread.matrix_signal.connect(self.update_matrix)
        self.marquee_thread.finished_signal.connect(self.animation_finished)
        
        # Start the thread
        self.marquee_thread.start()
        
        # Update UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Running marquee animation...")
    
    def stop_marquee(self):
        if self.marquee_thread and self.marquee_thread.isRunning():
            self.marquee_thread.stop()
            self.status_label.setText("Stopping animation...")
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def update_matrix(self, matrix):
        self.current_matrix = matrix
        # If we're on the manual tab, update the LED buttons
        if self.tabs.currentIndex() == 1:
            for r in range(10):
                for c in range(10):
                    self.led_buttons[r][c].setState(matrix[r][c])
    
    def animation_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Animation complete")
    
    def setupManualTab(self):
        main_layout = QVBoxLayout()
        
        # Create a grid for the LED buttons
        grid_layout = QGridLayout()
        grid_layout.setSpacing(2)
        
        # Create a 10x10 grid of LED buttons
        self.led_buttons = []
        for r in range(10):
            row_buttons = []
            for c in range(10):
                button = LEDButton(r, c)
                button.clicked.connect(lambda checked, r=r, c=c: self.toggle_led(r, c))
                grid_layout.addWidget(button, r, c)
                row_buttons.append(button)
            self.led_buttons.append(row_buttons)
        
        main_layout.addLayout(grid_layout)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self.clear_all_leds)
        control_layout.addWidget(clear_button)
        
        fill_button = QPushButton("Fill All")
        fill_button.clicked.connect(self.fill_all_leds)
        control_layout.addWidget(fill_button)
        
        send_button = QPushButton("Send to Arduino")
        send_button.clicked.connect(self.send_manual_matrix)
        control_layout.addWidget(send_button)
        
        main_layout.addLayout(control_layout)
        
        # Status label
        self.manual_status_label = QLabel("Ready")
        main_layout.addWidget(self.manual_status_label)
        
        self.manual_tab.setLayout(main_layout)
    
    def toggle_led(self, row, col):
        # Update the internal matrix
        self.current_matrix[row][col] = 1 if self.current_matrix[row][col] == 0 else 0
    
    def clear_all_leds(self):
        # Set all LEDs to off
        self.current_matrix = create_empty_matrix()
        for r in range(10):
            for c in range(10):
                self.led_buttons[r][c].setState(0)
        self.manual_status_label.setText("All LEDs cleared")
    
    def fill_all_leds(self):
        # Set all LEDs to on
        self.current_matrix = create_full_matrix()
        for r in range(10):
            for c in range(10):
                self.led_buttons[r][c].setState(1)
        self.manual_status_label.setText("All LEDs filled")
    
    def send_manual_matrix(self):
        # Send the current matrix to Arduino
        result = send_led_matrix(self.current_matrix)
        self.manual_status_label.setText(f"Sent to Arduino: {result}")

# Main entry point
if __name__ == "__main__":
    matrix_app = MarqueeApp()
    matrix_app.show()
    sys.exit(app.exec_())