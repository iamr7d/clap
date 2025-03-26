import sys
import os
import serial
import time 
import numpy as np

from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QSlider, QSpinBox, QComboBox, QCheckBox, 
    QGridLayout, QGroupBox, QDoubleSpinBox, QFileDialog, QMessageBox
)
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

def send_led_matrix(matrix):
    """Send a 10x10 LED matrix as a 100-character string to Arduino."""
    # Convert the matrix to a string without flipping
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
                 direction="Right to Left", flip_horizontal=False, color=1):
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
        width = 10 + len(self.text) * 8
        img = Image.new('1', (width, 8), 0)
        draw = ImageDraw.Draw(img)
        
        # Draw the text
        draw.text((10, -2), self.text, fill=self.color, font=font)
        
        # Invert if requested
        if self.invert:
            img = Image.eval(img, lambda px: 1 - px)
        
        # No horizontal flip here - we'll handle display consistency in _update_and_send
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
        
        # No horizontal flip here
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
        
        # No horizontal flip before rotation
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
        
        # No horizontal flip before rotation
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
        
        # No horizontal flip
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
        # Create a copy of the matrix for display
        display_matrix = [row[:] for row in matrix]
        
        # For the physical LED display, we need to flip horizontally
        # to match the orientation of the physical matrix
        arduino_matrix = self._flip_matrix_horizontal(matrix) if self.flip_horizontal else matrix
        
        # Update the UI with the display matrix (not flipped)
        self.matrix_signal.emit(display_matrix)
        
        # Send the properly oriented matrix to Arduino
        send_led_matrix(arduino_matrix)
        
        # Pause based on speed
        time.sleep(self.speed)
    
    def _flip_matrix_horizontal(self, matrix):
        """Flip a matrix horizontally (reverse each row)"""
        return [row[::-1] for row in matrix]
    
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
        self.setWindowTitle('FILMDA. Smart Clapper')
        self.setGeometry(100, 100, 800, 600)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.marquee_tab = QWidget()
        self.manual_tab = QWidget()
        self.pattern_tab = QWidget()
        self.settings_tab = QWidget()
        
        # Add tabs to widget
        self.tabs.addTab(self.marquee_tab, "Marquee Text")
        self.tabs.addTab(self.manual_tab, "Manual Control")
        self.tabs.addTab(self.pattern_tab, "Patterns")
        self.tabs.addTab(self.settings_tab, "Settings")
        
        # Initialize tabs
        self.initMarqueeTab()
        self.initManualTab()
        self.initPatternTab()
        self.initSettingsTab()
        
        # Set the central widget
        self.setCentralWidget(self.tabs)
        
        # Set dark theme
        self.setDarkTheme()
        
        # Show the window
        self.show()
    
    def setDarkTheme(self):
        # Set dark palette
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        
        self.setPalette(dark_palette)
        
        # Set stylesheet
        self.setStyleSheet("""
            QToolTip { 
                color: #ffffff; 
                background-color: #2a82da; 
                border: 1px solid white; 
            }
            QTabWidget::pane { 
                border: 1px solid #444; 
            }
            QTabBar::tab {
                background: #333; 
                color: white;
                padding: 10px;
                margin-right: 2px;
            }
            QTabBar::tab:selected { 
                background: #444; 
            }
            QPushButton { 
                background-color: #555; 
                color: white; 
                border: none; 
                padding: 5px; 
                border-radius: 3px; 
            }
            QPushButton:hover { 
                background-color: #666; 
            }
            QPushButton:pressed { 
                background-color: #777; 
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { 
                background-color: #333; 
                color: white; 
                border: 1px solid #555; 
                padding: 2px; 
            }
            QLabel { 
                color: white; 
            }
            QCheckBox { 
                color: white; 
            }
            QGroupBox { 
                border: 1px solid #555; 
                margin-top: 10px; 
                color: white; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 3px 0 3px; 
            }
        """)
    
    def initMarqueeTab(self):
        # Create layout
        layout = QVBoxLayout()
        
        # Text input group
        text_group = QGroupBox("Text Input")
        text_layout = QVBoxLayout()
        
        # Text input
        text_input_layout = QHBoxLayout()
        text_input_layout.addWidget(QLabel("Text:"))
        self.text_input = QLineEdit("Hello World!")
        text_input_layout.addWidget(self.text_input)
        text_layout.addLayout(text_input_layout)
        
        # Font selection
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font:"))
        self.font_combo = QComboBox()
        
        # Add system fonts
        default_font = "C:/Users/rahul/OneDrive/Desktop/10_10_led_matrix/10_10_led_matrix/Gotham-Font/Gotham-Black.otf"
        self.font_combo.addItem("Default (Gotham Black)", default_font)
        
        # Add custom font option
        self.font_combo.addItem("Custom Font...", "custom")
        self.font_path = default_font
        
        font_layout.addWidget(self.font_combo)
        
        # Font size
        font_layout.addWidget(QLabel("Size:"))
        self.font_size = QSpinBox()
        self.font_size.setRange(6, 9)
        self.font_size.setValue(8)
        font_layout.addWidget(self.font_size)
        
        text_layout.addLayout(font_layout)
        
        # Animation controls
        anim_layout = QHBoxLayout()
        
        # Direction
        anim_layout.addWidget(QLabel("Direction:"))
        self.direction_combo = QComboBox()
        self.direction_combo.addItems([
            "Right to Left", 
            "Left to Right", 
            "Top to Bottom", 
            "Bottom to Top", 
            "Diagonal"
        ])
        anim_layout.addWidget(self.direction_combo)
        
        # Speed
        anim_layout.addWidget(QLabel("Speed:"))
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.05, 1.0)
        self.speed_spin.setSingleStep(0.05)
        self.speed_spin.setValue(0.2)
        anim_layout.addWidget(self.speed_spin)
        
        # Loops
        anim_layout.addWidget(QLabel("Loops:"))
        self.loops_spin = QSpinBox()
        self.loops_spin.setRange(0, 100)
        self.loops_spin.setValue(1)
        self.loops_spin.setSpecialValueText("∞")  # Infinite loops when 0
        anim_layout.addWidget(self.loops_spin)
        
        text_layout.addLayout(anim_layout)
        
        # Options
        options_layout = QHBoxLayout()
        
        # Invert
        self.invert_check = QCheckBox("Invert Colors")
        options_layout.addWidget(self.invert_check)
        
        # Flip horizontally for physical display
        self.flip_check = QCheckBox("Flip Horizontally for Physical Display")
        self.flip_check.setChecked(True)  # Default to checked
        options_layout.addWidget(self.flip_check)
        
        text_layout.addLayout(options_layout)
        
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)
        
        # Preview group
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        # LED Matrix preview
        matrix_layout = QGridLayout()
        self.led_buttons = []
        
        for r in range(10):
            row_buttons = []
            for c in range(10):
                btn = LEDButton(r, c)
                matrix_layout.addWidget(btn, r, c)
                row_buttons.append(btn)
            self.led_buttons.append(row_buttons)
        
        preview_layout.addLayout(matrix_layout)
        
        # Status
        self.status_label = QLabel("Ready")
        preview_layout.addWidget(self.status_label)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Marquee")
        self.start_button.clicked.connect(self.startMarquee)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stopMarquee)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        self.clear_button = QPushButton("Clear Display")
        self.clear_button.clicked.connect(self.clearDisplay)
        control_layout.addWidget(self.clear_button)
        
        layout.addLayout(control_layout)
        
        # Set the layout
        self.marquee_tab.setLayout(layout)
        
        # Connect font combo box
        self.font_combo.currentIndexChanged.connect(self.onFontChanged)
    
    def onFontChanged(self, index):
        font_data = self.font_combo.itemData(index)
        if font_data == "custom":
            # Open file dialog to select font
            font_file, _ = QFileDialog.getOpenFileName(
                self, "Select Font File", "", "Font Files (*.ttf *.otf)"
            )
            if font_file:
                self.font_path = font_file
                # Update combo box text but keep the "custom" data
                self.font_combo.setItemText(index, os.path.basename(font_file))
            else:
                # Revert to previous selection if canceled
                self.font_combo.setCurrentIndex(0)
        else:
            self.font_path = font_data
    
    def initManualTab(self):
        layout = QVBoxLayout()
        
        # Control group
        control_group = QGroupBox("Manual Control")
        control_layout = QVBoxLayout()
        
        # LED Matrix for manual control
        matrix_layout = QGridLayout()
        self.manual_buttons = []
        
        for r in range(10):
            row_buttons = []
            for c in range(10):
                btn = LEDButton(r, c)
                btn.clicked.connect(self.onManualButtonClick)
                matrix_layout.addWidget(btn, r, c)
                row_buttons.append(btn)
            self.manual_buttons.append(row_buttons)
        
        control_layout.addLayout(matrix_layout)
        
        # Button controls
        button_layout = QHBoxLayout()
        
        self.send_manual_button = QPushButton("Send to Display")
        self.send_manual_button.clicked.connect(self.sendManualMatrix)
        button_layout.addWidget(self.send_manual_button)
        
        self.clear_manual_button = QPushButton("Clear Grid")
        self.clear_manual_button.clicked.connect(self.clearManualGrid)
        button_layout.addWidget(self.clear_manual_button)
        
        self.fill_manual_button = QPushButton("Fill Grid")
        self.fill_manual_button.clicked.connect(self.fillManualGrid)
        button_layout.addWidget(self.fill_manual_button)
        
        control_layout.addLayout(button_layout)
        
        # Pattern buttons
        pattern_layout = QHBoxLayout()
        
        self.pattern_1_button = QPushButton("Checkerboard")
        self.pattern_1_button.clicked.connect(lambda: self.applyPattern("checkerboard"))
        pattern_layout.addWidget(self.pattern_1_button)
        
        self.pattern_2_button = QPushButton("Border")
        self.pattern_2_button.clicked.connect(lambda: self.applyPattern("border"))
        pattern_layout.addWidget(self.pattern_2_button)
        
        self.pattern_3_button = QPushButton("X Pattern")
        self.pattern_3_button.clicked.connect(lambda: self.applyPattern("x"))
        pattern_layout.addWidget(self.pattern_3_button)
        
        control_layout.addLayout(pattern_layout)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        self.manual_tab.setLayout(layout)
    
    def initPatternTab(self):
        layout = QVBoxLayout()
        
        # Patterns group
        patterns_group = QGroupBox("Built-in Patterns")
        patterns_layout = QVBoxLayout()
        
        # Pattern selection
        pattern_select_layout = QHBoxLayout()
        pattern_select_layout.addWidget(QLabel("Pattern:"))
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "Blink All", 
            "Rows Sequence", 
            "Columns Sequence", 
            "Spiral In", 
            "Spiral Out",
            "Rain",
            "Random Pixels"
        ])
        pattern_select_layout.addWidget(self.pattern_combo)
        
        # Speed
        pattern_select_layout.addWidget(QLabel("Speed:"))
        self.pattern_speed = QDoubleSpinBox()
        self.pattern_speed.setRange(0.05, 1.0)
        self.pattern_speed.setSingleStep(0.05)
        self.pattern_speed.setValue(0.2)
        pattern_select_layout.addWidget(self.pattern_speed)
        
        # Loops
        pattern_select_layout.addWidget(QLabel("Loops:"))
        self.pattern_loops = QSpinBox()
        self.pattern_loops.setRange(0, 100)
        self.pattern_loops.setValue(3)
        self.pattern_loops.setSpecialValueText("∞")  # Infinite loops when 0
        pattern_select_layout.addWidget(self.pattern_loops)
        
        patterns_layout.addLayout(pattern_select_layout)
        
        # Preview
        pattern_preview_layout = QGridLayout()
        self.pattern_buttons = []
        
        for r in range(10):
            row_buttons = []
            for c in range(10):
                btn = LEDButton(r, c)
                pattern_preview_layout.addWidget(btn, r, c)
                row_buttons.append(btn)
            self.pattern_buttons.append(row_buttons)
        
        patterns_layout.addLayout(pattern_preview_layout)
        
        # Controls
        pattern_control_layout = QHBoxLayout()
        
        self.start_pattern_button = QPushButton("Start Pattern")
        self.start_pattern_button.clicked.connect(self.startPattern)
        pattern_control_layout.addWidget(self.start_pattern_button)
        
        self.stop_pattern_button = QPushButton("Stop Pattern")
        self.stop_pattern_button.clicked.connect(self.stopPattern)
        self.stop_pattern_button.setEnabled(False)
        pattern_control_layout.addWidget(self.stop_pattern_button)
        
        patterns_layout.addLayout(pattern_control_layout)
        
        patterns_group.setLayout(patterns_layout)

        layout.addWidget(patterns_group)
        
        self.pattern_tab.setLayout(layout)
        
        # Pattern thread
        self.pattern_thread = None
    
    def initSettingsTab(self):
        layout = QVBoxLayout()
        
        # Arduino settings
        arduino_group = QGroupBox("Arduino Connection")
        arduino_layout = QVBoxLayout()
        
        # COM Port
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("COM Port:"))
        self.port_combo = QComboBox()
        self.port_combo.addItems(["COM5", "COM3", "COM4", "COM6"])
        self.port_combo.setCurrentText("COM5")
        port_layout.addWidget(self.port_combo)
        
        # Reconnect button
        self.reconnect_button = QPushButton("Reconnect")
        self.reconnect_button.clicked.connect(self.reconnectArduino)
        port_layout.addWidget(self.reconnect_button)
        
        arduino_layout.addLayout(port_layout)
        
        # Status
        self.arduino_status = QLabel("Status: Connected to COM5" if arduino else "Status: Not connected")
        arduino_layout.addWidget(self.arduino_status)
        
        arduino_group.setLayout(arduino_layout)
        layout.addWidget(arduino_group)
        
        # Display settings
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()
        
        # Brightness
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("Brightness:"))
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(100)
        self.brightness_slider.valueChanged.connect(self.setBrightness)
        brightness_layout.addWidget(self.brightness_slider)
        self.brightness_value = QLabel("100%")
        brightness_layout.addWidget(self.brightness_value)
        
        display_layout.addLayout(brightness_layout)
        
        # Orientation
        orientation_layout = QHBoxLayout()
        orientation_layout.addWidget(QLabel("Orientation:"))
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Normal", "Rotate 90°", "Rotate 180°", "Rotate 270°"])
        self.orientation_combo.currentIndexChanged.connect(self.setOrientation)
        orientation_layout.addWidget(self.orientation_combo)
        
        display_layout.addLayout(orientation_layout)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        # Test patterns
        test_group = QGroupBox("Test Patterns")
        test_layout = QHBoxLayout()
        
        self.test_all_on = QPushButton("All LEDs On")
        self.test_all_on.clicked.connect(self.testAllOn)
        test_layout.addWidget(self.test_all_on)
        
        self.test_all_off = QPushButton("All LEDs Off")
        self.test_all_off.clicked.connect(self.testAllOff)
        test_layout.addWidget(self.test_all_off)
        
        self.test_sequence = QPushButton("Test Sequence")
        self.test_sequence.clicked.connect(self.testSequence)
        test_layout.addWidget(self.test_sequence)
        
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        # About section
        about_group = QGroupBox("About")
        about_layout = QVBoxLayout()
        
        about_text = QLabel("FILMDA. Smart Clapper v1.0\n"
                           "Created by R7D. AI Labs")
        about_layout.addWidget(about_text)
        
        about_group.setLayout(about_layout)
        layout.addWidget(about_group)
        
        self.settings_tab.setLayout(layout)
    
    def startMarquee(self):
        # Get parameters from UI
        text = self.text_input.text()
        if not text:
            self.status_label.setText("Error: Please enter some text")
            return
        
        speed = self.speed_spin.value()
        loops = self.loops_spin.value()
        font_path = self.font_path
        font_size = self.font_size.value()
        invert = self.invert_check.isChecked()
        direction = self.direction_combo.currentText()
        flip_horizontal = self.flip_check.isChecked()
        
        # Update status
        self.status_label.setText(f"Starting marquee: '{text}'")
        
        # Create and start thread
        self.marquee_thread = MarqueeThread(
            text, speed, loops, font_path, font_size, invert, 
            direction, flip_horizontal
        )
        
        # Connect signals
        self.marquee_thread.update_signal.connect(self.updateStatus)
        self.marquee_thread.matrix_signal.connect(self.updateLEDMatrix)
        self.marquee_thread.finished_signal.connect(self.onMarqueeFinished)
        
        # Start the thread
        self.marquee_thread.start()
        
        # Update UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
    
    def stopMarquee(self):
        if self.marquee_thread and self.marquee_thread.isRunning():
            self.marquee_thread.stop()
            self.marquee_thread.wait()
            self.status_label.setText("Marquee stopped")
        
        # Update UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def onMarqueeFinished(self):
        # Update UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Ready")
    
    def updateStatus(self, message):
        self.status_label.setText(message)
    
    def updateLEDMatrix(self, matrix):
        # Update the current matrix
        self.current_matrix = matrix
        
        # Update the LED buttons
        for r in range(10):
            for c in range(10):
                if r < len(matrix) and c < len(matrix[r]):
                    self.led_buttons[r][c].setState(matrix[r][c])
    
    def clearDisplay(self):
        # Send clear command to Arduino
        send_command("C")
        
        # Clear the UI
        empty_matrix = create_empty_matrix()
        self.updateLEDMatrix(empty_matrix)
        
        self.status_label.setText("Display cleared")
    
    def onManualButtonClick(self):
        # This is handled by the LEDButton's toggle method
        pass
    
    def sendManualMatrix(self):
        # Create matrix from button states
        matrix = []
        for r in range(10):
            row = []
            for c in range(10):
                row.append(self.manual_buttons[r][c].state)
            matrix.append(row)
        
        # Apply horizontal flip for physical display if needed
        if self.flip_check.isChecked():
            matrix = [row[::-1] for row in matrix]
        
        # Send to Arduino
        send_led_matrix(matrix)
    
    def clearManualGrid(self):
        # Set all buttons to off
        for r in range(10):
            for c in range(10):
                self.manual_buttons[r][c].setState(0)
    
    def fillManualGrid(self):
        # Set all buttons to on
        for r in range(10):
            for c in range(10):
                self.manual_buttons[r][c].setState(1)
    
    def applyPattern(self, pattern):
        matrix = create_empty_matrix()
        
        if pattern == "checkerboard":
            for r in range(10):
                for c in range(10):
                    if (r + c) % 2 == 0:
                        matrix[r][c] = 1
        
        elif pattern == "border":
            for r in range(10):
                for c in range(10):
                    if r == 0 or r == 9 or c == 0 or c == 9:
                        matrix[r][c] = 1
        
        elif pattern == "x":
            for r in range(10):
                for c in range(10):
                    if r == c or r == 9 - c:
                        matrix[r][c] = 1
        
        # Update the buttons
        for r in range(10):
            for c in range(10):
                self.manual_buttons[r][c].setState(matrix[r][c])
    
    def startPattern(self):
        pattern = self.pattern_combo.currentText()
        speed = self.pattern_speed.value()
        loops = self.pattern_loops.value()
        
        # TODO: Implement pattern animations
        # For now, just show a message
        QMessageBox.information(self, "Pattern", f"Pattern '{pattern}' would run at speed {speed} for {loops} loops")
        
        # Update UI
        self.start_pattern_button.setEnabled(False)
        self.stop_pattern_button.setEnabled(True)
    
    def stopPattern(self):
        # TODO: Implement stopping pattern animations
        
        # Update UI
        self.start_pattern_button.setEnabled(True)
        self.stop_pattern_button.setEnabled(False)
    
    def reconnectArduino(self):
        global arduino
        
        port = self.port_combo.currentText()
        
        try:
            # Close existing connection if any
            if arduino:
                arduino.close()
            
            # Open new connection
            arduino = serial.Serial(port=port, baudrate=9600, timeout=1)
            self.arduino_status.setText(f"Status: Connected to {port}")
            
            # Reset Arduino
            send_command("R")
            
        except Exception as e:
            self.arduino_status.setText(f"Status: Error - {str(e)}")
            arduino = None
    
    def setBrightness(self, value):
        # Update label
        self.brightness_value.setText(f"{value}%")
        
        # Send brightness command to Arduino
        # Scale from 0-100 to 0-255
        brightness = int(value * 2.55)
        send_command(f"B{brightness}")
    
    def setOrientation(self, index):
        # Send orientation command to Arduino
        send_command(f"O{index}")
    
    def testAllOn(self):
        # Send all on command
        send_command("A")
    
    def testAllOff(self):
        # Send all off command
        send_command("C")
    
    def testSequence(self):
        # Send test sequence command
        send_command("T")
    
    def closeEvent(self, event):
        # Stop any running threads
        if self.marquee_thread and self.marquee_thread.isRunning():
            self.marquee_thread.stop()
            self.marquee_thread.wait()
        
        # Close Arduino connection
        if arduino:
            arduino.close()
        
        event.accept()

# Run the application
if __name__ == "__main__":
    window = MarqueeApp()
    sys.exit(app.exec_())