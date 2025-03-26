import sys
import os
import serial
import time 
import numpy as np
import json
import os
from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QSlider, QSpinBox, QComboBox, QCheckBox, 
    QGridLayout, QGroupBox, QDoubleSpinBox, QFileDialog, QMessageBox
)

import threading
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QPalette

def startMarquee(self):
    """Start the marquee animation"""
    # Get values from UI
    text = self.text_input.text().upper()  # Changed to uppercase as requested
    speed = self.speed_spin.value()
    
    # Check if text is empty
    if not text:
        self.updateStatus("Please enter text for the marquee")
        return
    
    # Define variables for the MarqueeThread
    font_path = "C:\\Users\\rahul\\OneDrive\\Desktop\\10_10_led_matrix\\10_10_led_matrix\\Gotham-Font\\Gotham-Bold.otf"
    font_size = 12
    invert = False
    direction = "left"
    flip_horizontal = False
    loops = 0  # Default loops (0 = infinite)
    
    # Create and start the marquee thread
    self.marquee_thread = MarqueeThread(
        text, speed, self.arduino, font_path, font_size, invert, 
        direction, flip_horizontal, loops
    )
    self.marquee_thread.status_update.connect(self.updateStatus)
    self.marquee_thread.start()
    
    # Connect signals
    self.marquee_thread.update_signal.connect(self.updateMatrix)
    self.marquee_thread.finished_signal.connect(self.marqueeFinished)
        
    # Update UI
    self.start_button.setEnabled(False)
    self.stop_button.setEnabled(True)
    
    # Update status
    self.updateStatus(f"Marquee started with text: {text}")

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

class Arduino:
    """Simple class to handle Arduino serial communication"""
    def __init__(self, port, baudrate=9600, timeout=1):
        import serial
        self.port = port
        self.serial = serial.Serial(port, baudrate, timeout=timeout)
        print(f"Connected to Arduino on {port}")
        
    def write(self, data):
        """Write data to Arduino"""
        if isinstance(data, str):
            data = data.encode()
        self.serial.write(data)
        
    def read(self, size=1):
        """Read data from Arduino"""
        return self.serial.read(size)
        
    def readline(self):
        """Read a line from Arduino"""
        return self.serial.readline()
        
    def close(self):
        """Close the serial connection"""
        self.serial.close()

    def send_matrix_data(self, data):
        """Send matrix data to Arduino"""
        self.write(data)
        
    def clear_display(self):
        """Clear the LED display"""
        self.write("C")  # Assuming 'C' is the command to clear the display




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
    """Thread for scrolling marquee text on the LED matrix"""
    update_signal = pyqtSignal(list)  # Signal to update UI with current matrix state
    finished_signal = pyqtSignal()   # Signal when animation is complete
    
    def __init__(self, text, speed, arduino, font_path, font_size, invert, 
                direction="Right to Left", flip_horizontal=False, loops=0, color=1):
        super().__init__()
        self.text = text
        self.speed = speed
        self.arduino = arduino  # Add this line
        self.loops = loops
        self.font_path = font_path
        # Limit font size to ensure it fits in the 10x10 matrix
        self.font_size = min(font_size, 9)  # Cap at 9 pixels to ensure visibility
        self.invert = invert
        self.direction = direction
        self.flip_horizontal = flip_horizontal
        self.color = color
        self.running = True
        self.stop_flag = threading.Event()  # Initialize the stop_flag

    def run(self):
        """Run the marquee animation"""
        try:
            # Create image with text
            image = self.create_text_image()
            
            # Debug info
            print(f"Image created with dimensions: {image.width}x{image.height}")
            
            # Get the binary representation of the image
            binary_frames = self.image_to_binary(image)
            
            # Debug info
            print(f"Created {len(binary_frames)} binary frames")
            
            # Loop through frames
            loop_count = 0
            while not self.stop_flag.is_set():
                for frame in binary_frames:
                    if self.stop_flag.is_set():
                        break
                        
                    # Debug - print first few characters of the frame
                    print(f"Sending frame: {frame[:20]}...")
                    
                    # Send the frame to Arduino
                    self.arduino.send_matrix_data(frame)
                    
                    # Sleep for speed delay
                    time.sleep(1.0 / self.speed)
                    
                loop_count += 1
                if self.loops > 0 and loop_count >= self.loops:
                    break
        

            # When sending a frame, emit the signal
            for frame in binary_frames:
                if self.stop_flag.is_set():
                    break
                    
                # Debug - print first few characters of the frame
                print(f"Sending frame: {frame[:20]}...")
                
                # Emit signal instead of directly accessing arduino
                self.update_signal.emit(frame)
                
                # Sleep for speed delay
                time.sleep(1.0 / self.speed)
                
            # Clear display when done
            self.arduino.clear_display()
            print("Marquee finished, display cleared")
            
        except Exception as e:
            print(f"Error in MarqueeThread.run(): {str(e)}")
            import traceback
            traceback.print_exc()
            self.finished_signal.emit()
        finally:
            self.finished_signal.emit() 

    def _update_and_send(self, matrix_data):
        """Update and send matrix data to Arduino"""
        try:
            # Convert matrix data to binary string
            data_str = 'W' + ''.join(str(cell) for row in matrix_data for cell in row)
            
            # Send to Arduino
            self.arduino.write(data_str)
            
            # Update UI
            self.updateMatrix(matrix_data)
        except Exception as e:
            print(f"Error in _update_and_send: {str(e)}")
            import traceback
            traceback.print_exc()
            self.finished_signal.emit()
    
    def stop(self):
        """Stop the marquee animation"""
        self.running = False
        self.stop_flag.set()  # Set the stop flag to signal the thread to stop
        
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
    
    

    def create_text_image(self):
        """Create an image with the text to display"""
        # Load font
        try:
            font = ImageFont.truetype(self.font_path, self.font_size)
            print(f"Using font: {self.font_path}")
        except Exception as e:
            # Try to load Gotham Black as a fallback
            gotham_path = "C:/Users/rahul/OneDrive/Desktop/10_10_led_matrix/10_10_led_matrix/Gotham-Font/Gotham-Black.otf"
            try:
                font = ImageFont.truetype(gotham_path, self.font_size)
                print(f"Using default Gotham Black font")
            except Exception as e2:
                print(f"Error loading fonts: {e}. Using system default.")
                font = ImageFont.load_default()
        
        # Get text size using the newer method
        dummy_img = Image.new('1', (100, 100))
        dummy_draw = ImageDraw.Draw(dummy_img)
        
        # Use textbbox for newer Pillow versions
        try:
            left, top, right, bottom = dummy_draw.textbbox((0, 0), self.text, font=font)
            text_width = right - left
            text_height = bottom - top
        except AttributeError:
            # Fallback for older versions (though this will likely fail based on the error)
            try:
                text_width, text_height = dummy_draw.textsize(self.text, font=font)
            except:
                # If all else fails, estimate based on character count
                text_width = len(self.text) * self.font_size * 0.6
                text_height = self.font_size
        
        # Create image large enough for scrolling
        image_width = int(text_width + 20)  # Add extra space for scrolling
        image_height = max(10, int(text_height))  # At least 10 pixels high for the matrix
        
        # Create image
        image = Image.new('1', (image_width, image_height), color=0)
        draw = ImageDraw.Draw(image)
        
        # Draw text
        draw.text((10, 0), self.text, font=font, fill=1)
        
        # Resize to ensure height is 10 pixels
        if image_height != 10:
            image = image.resize((image_width, 10), Image.LANCZOS)
        
        # Invert if needed
        if self.invert:
            image = ImageOps.invert(image.convert('L')).convert('1')
        
        # Flip if needed
        if self.flip_horizontal:
            image = ImageOps.mirror(image)
        
        return image


    def image_to_binary(self, image):
        """Convert image to binary frames for the LED matrix"""
        frames = []
        
        # For scrolling left to right
        if self.direction == "right":
            start = -image.width
            end = 10
            step = 1
        # For scrolling right to left (default)
        else:
            start = 10
            end = -image.width
            step = -1
        
        # Create frames for each position
        for x in range(start, end, step):
            # Create a 10x10 frame
            frame = Image.new('1', (10, 10), color=0)
            
            # Paste the portion of the image that's visible
            frame.paste(image, (x, 0))
            
            # Convert to binary string
            binary = ""
            for y in range(10):
                for x in range(10):
                    pixel = frame.getpixel((x, y))
                    binary += "1" if pixel > 0 else "0"
            
            # Add the command prefix
            binary = "W" + binary
            frames.append(binary)
        
        return frames

    def stop(self):
        """Stop the marquee animation"""
        self.stop_flag = threading.Event()
        self.stop_flag.set()



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
        
        # Initialize Arduino connection (will be done in settings tab)
        self.arduino = None
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

    def savePattern(self):
        """Save the current pattern to a file"""
        # Get current pattern from manual grid
        pattern = []
        for row in range(10):
            row_data = []
            for col in range(10):
                row_data.append(1 if self.manual_buttons[row][col].state else 0)
            pattern.append(row_data)
        
        # Get pattern name
        pattern_name, ok = QInputDialog.getText(self, "Save Pattern", "Enter pattern name:")
        
        if ok and pattern_name:
            # Create patterns directory if it doesn't exist
            os.makedirs("patterns", exist_ok=True)
            
            # Save pattern to file
            with open(f"patterns/{pattern_name}.json", "w") as f:
                json.dump(pattern, f)
            
            self.updateStatus(f"Pattern '{pattern_name}' saved successfully")
            
    def loadPattern(self):
        """Load a pattern from a file"""
        # Check if patterns directory exists
        if not os.path.exists("patterns"):
            self.updateStatus("No patterns found")
            return
        
        # Get list of pattern files
        pattern_files = [f for f in os.listdir("patterns") if f.endswith(".json")]
        
        if not pattern_files:
            self.updateStatus("No patterns found")
            return
        
        # Extract pattern names (remove .json extension)
        pattern_names = [os.path.splitext(f)[0] for f in pattern_files]
        
        # Show pattern selection dialog
        pattern_name, ok = QInputDialog.getItem(
            self, "Load Pattern", "Select a pattern:", pattern_names, 0, False
        )
        
        if ok and pattern_name:
            # Load pattern from file
            with open(f"patterns/{pattern_name}.json", "r") as f:
                pattern = json.load(f)
            
            # Update manual buttons
            for row in range(10):
                for col in range(10):
                    if row < len(pattern) and col < len(pattern[row]):
                        self.manual_buttons[row][col].setState(pattern[row][col])
            
            self.updateStatus(f"Pattern '{pattern_name}' loaded successfully")


    def onManualButtonClick(self):
        """Handle manual button clicks"""
        # This is handled by the LEDButton's toggle method
        # We just need to send the updated matrix to Arduino
        self.sendManualMatrix()

    def sendManualMatrix(self):
        """Send the current manual matrix to Arduino"""
        # Get current matrix from manual grid
        matrix = []
        for row in range(10):
            row_data = []
            for col in range(10):
                row_data.append(1 if self.manual_buttons[row][col].state else 0)
            matrix.append(row_data)
        
        # Send matrix to Arduino
        self.arduino.writeMatrix(matrix)
        
        # Update status
        self.updateStatus("Manual matrix sent to Arduino")

    def clearManualGrid(self):
        """Clear the manual grid"""
        # Set all manual buttons to off
        for row in range(10):
            for col in range(10):
                self.manual_buttons[row][col].setState(0)
        
        # Send the cleared matrix to Arduino
        self.sendManualMatrix()
        
        # Update status
        self.updateStatus("Manual grid cleared")

    def fillManualGrid(self):
        """Fill the manual grid (set all LEDs on)"""
        # Set all manual buttons to on
        for row in range(10):
            for col in range(10):
                self.manual_buttons[row][col].setState(1)
        
        # Send the filled matrix to Arduino
        self.sendManualMatrix()
        
        # Update status
        self.updateStatus("Manual grid filled")

    def initPatternTab(self):
        """Initialize the pattern tab"""
        # Create pattern tab layout
        pattern_layout = QVBoxLayout()
        
        # Create pattern selection group
        pattern_group = QGroupBox("Select Pattern")
        pattern_group_layout = QVBoxLayout()
        
        # Create pattern selection combo box
        self.pattern_combo = QComboBox()
        self.loadPatternList()  # Load available patterns
        pattern_group_layout.addWidget(self.pattern_combo)
        
        # Create pattern control buttons
        pattern_buttons_layout = QHBoxLayout()
        
        # Start pattern button
        self.start_pattern_button = QPushButton("Start Pattern")
        self.start_pattern_button.clicked.connect(self.startPattern)
        pattern_buttons_layout.addWidget(self.start_pattern_button)
        
        # Stop pattern button
        self.stop_pattern_button = QPushButton("Stop Pattern")
        self.stop_pattern_button.clicked.connect(self.stopPattern)
        pattern_buttons_layout.addWidget(self.stop_pattern_button)
        
        pattern_group_layout.addLayout(pattern_buttons_layout)
        pattern_group.setLayout(pattern_group_layout)
        pattern_layout.addWidget(pattern_group)
        
        # Set pattern tab layout
        pattern_widget = QWidget()
        pattern_widget.setLayout(pattern_layout)
        self.tabs.addTab(pattern_widget, "Patterns")

    def updateMatrix(self, matrix_data):
        """Update the LED matrix display with the given data"""
        try:
            # If matrix_data is a binary string (from MarqueeThread)
            if isinstance(matrix_data, str) and matrix_data.startswith('W'):
                # Send directly to Arduino
                self.arduino.write(matrix_data)
                
                # Also update the UI if needed
                # (Convert binary string to matrix representation for UI)
                
            # If it's already a matrix representation
            elif isinstance(matrix_data, list):
                # Convert to binary string and send
                data_str = 'W' + ''.join(str(cell) for row in matrix_data for cell in row)
                self.arduino.write(data_str)
                
            self.status_label.setText("Matrix updated")
        except Exception as e:
            self.status_label.setText(f"Error updating matrix: {str(e)}")
            print(f"Error in updateMatrix: {str(e)}")
            
    def loadPatternList(self):
        """Load the list of saved patterns into the combo box"""
        # Clear the combo box
        self.pattern_combo.clear()
        
        # Check if patterns directory exists
        if not os.path.exists("patterns"):
            # Create the directory if it doesn't exist
            os.makedirs("patterns", exist_ok=True)
            return
        
        # Get list of pattern files
        pattern_files = [f for f in os.listdir("patterns") if f.endswith(".json")]
        
        # Extract pattern names (remove .json extension)
        pattern_names = [os.path.splitext(f)[0] for f in pattern_files]
        
        # Add patterns to combo box
        for name in pattern_names:
            self.pattern_combo.addItem(name)


    def startPattern(self):
        """Start the selected pattern"""
        # Get selected pattern
        pattern_name = self.pattern_combo.currentText()
        if not pattern_name:
            self.updateStatus("No pattern selected")
            return
        
        # Load pattern from file
        pattern_path = f"patterns/{pattern_name}.json"
        if not os.path.exists(pattern_path):
            self.updateStatus(f"Pattern file not found: {pattern_path}")
            return
        
        try:
            with open(pattern_path, "r") as f:
                pattern = json.load(f)
            
            # Send pattern to Arduino
            self.arduino.writeMatrix(pattern)
            
            # Update status
            self.updateStatus(f"Pattern '{pattern_name}' started")
        except Exception as e:
            self.updateStatus(f"Error loading pattern: {str(e)}")

    def stopPattern(self):
        """Stop the current pattern"""
        # Clear the display
        self.clearDisplay()
        
        # Update status
        self.updateStatus("Pattern stopped")


    def initSettingsTab(self):
        """Initialize the settings tab"""
        # Create settings tab layout
        settings_layout = QVBoxLayout()
        
        # Create serial port settings group
        serial_group = QGroupBox("Serial Port Settings")
        serial_group_layout = QVBoxLayout()  # Changed from QFormLayout to QVBoxLayout
        
        # Port selection
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.refreshPorts()  # Load available ports
        port_layout.addWidget(self.port_combo)
        serial_group_layout.addLayout(port_layout)
        
        # Refresh ports button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refreshPorts)
        serial_group_layout.addWidget(refresh_button)
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connectArduino)
        serial_group_layout.addWidget(self.connect_button)
        
        serial_group.setLayout(serial_group_layout)
        settings_layout.addWidget(serial_group)
        
        # Set settings tab layout
        settings_widget = QWidget()
        settings_widget.setLayout(settings_layout)
        self.tabs.addTab(settings_widget, "Settings")


    def clearDisplay(self):
        """Clear the LED matrix display"""
        # Create an empty matrix (all LEDs off)
        empty_matrix = [[0 for _ in range(10)] for _ in range(10)]
        
        # Update the display
        self.updateLEDMatrix(empty_matrix)
        
        # Update status
        self.updateStatus("Display cleared")


    def refreshPorts(self):
        """Refresh the list of available serial ports"""
        # Clear the combo box
        self.port_combo.clear()
        
        # Get available ports
        available_ports = []
        try:
            import serial.tools.list_ports
            available_ports = [port.device for port in serial.tools.list_ports.comports()]
        except:
            # Fallback to common ports if pyserial not available
            available_ports = ["COM1", "COM2", "COM3", "COM4", "COM5", "COM6"]
        
        # Add ports to combo box
        for port in available_ports:
            self.port_combo.addItem(port)
        
        # Select current port if it exists
        if hasattr(self, 'arduino') and self.arduino is not None and hasattr(self.arduino, 'port'):
            if self.arduino.port in available_ports:
                self.port_combo.setCurrentText(self.arduino.port)
                


    def connectArduino(self):
        """Connect to Arduino on selected port"""
        port = self.port_combo.currentText()
        
        # Update status
        self.updateStatus(f"Connecting to Arduino on {port}...")
        
        # Initialize Arduino connection
        try:
            self.arduino = Arduino(port)
            self.updateStatus(f"Connected to Arduino on {port}")
            self.connect_button.setText("Reconnect")
        except Exception as e:
            self.updateStatus(f"Error connecting to Arduino: {str(e)}")

    def startMarquee(self):
        """Start the marquee animation"""
        try:
            # Get parameters from UI
            text = self.text_input.text()
            speed = self.speed_slider.value()
            font_path = self.font_path
            font_size = self.font_size_spin.value()
            invert = self.invert_checkbox.isChecked()
            direction = self.direction_combo.currentText()
            flip_horizontal = self.flip_horizontal_checkbox.isChecked()
            loops = self.loops_spin.value()
            
            # Initialize Arduino if not already done
            if not hasattr(self, 'arduino') or self.arduino is None:
                self.arduino = Arduino("COM5")  # Use the appropriate COM port
            
            # Create and start the marquee thread
            self.marquee_thread = MarqueeThread(
                text, speed, self.arduino, font_path, font_size, invert,
                direction, flip_horizontal, loops
            )
            
            # Connect signals
            self.marquee_thread.update_signal.connect(self.updateMatrix)
            self.marquee_thread.finished_signal.connect(self.marqueeFinished)
            
            # Start the thread
            self.marquee_thread.start()
            
            # Update UI
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error starting marquee: {str(e)}")
            

    def stopMarquee(self):
        """Stop the marquee animation"""
        if self.marquee_thread and self.marquee_thread.isRunning():
            self.marquee_thread.stop()
            self.marquee_thread.wait()
            self.status_label.setText("Marquee stopped")  # Direct update
        
        # Update UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)


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
        
        # Add save/load buttons
        save_load_layout = QHBoxLayout()
        
        self.save_button = QPushButton("Save Pattern")
        self.save_button.clicked.connect(self.savePattern)
        
        self.load_button = QPushButton("Load Pattern")
        self.load_button.clicked.connect(self.loadPattern)
        
        save_load_layout.addWidget(self.save_button)
        save_load_layout.addWidget(self.load_button)
        
        control_layout.addLayout(save_load_layout)
        
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
    
    # Add new methods for save/load functionality
def savePattern(self):
    # Get current pattern from manual grid
    pattern = []
    for row in range(10):
        row_data = []
        for col in range(10):
            row_data.append(1 if self.manual_buttons[row][col].state else 0)
        pattern.append(row_data)
    
    # Get pattern name
    pattern_name, ok = QInputDialog.getText(self, "Save Pattern", "Enter pattern name:")
    
    if ok and pattern_name:
        # Create patterns directory if it doesn't exist
        os.makedirs("patterns", exist_ok=True)
        
        # Save pattern to file
        with open(f"patterns/{pattern_name}.json", "w") as f:
            json.dump(pattern, f)
        
        self.updateStatus(f"Pattern '{pattern_name}' saved successfully")

    def loadPattern(self):
        # Create patterns directory if it doesn't exist
        os.makedirs("patterns", exist_ok=True)
        
        # Get list of saved patterns
        pattern_files = [f[:-5] for f in os.listdir("patterns") if f.endswith(".json")]
        
        if not pattern_files:
            self.updateStatus("No saved patterns found")
            return
        
        # Let user select a pattern
        pattern_name, ok = QInputDialog.getItem(
            self, "Load Pattern", "Select a pattern:", pattern_files, 0, False
        )
        
        if ok and pattern_name:
            try:
                # Load pattern from file
                with open(f"patterns/{pattern_name}.json", "r") as f:
                    pattern = json.load(f)
                
                # Apply pattern to manual grid
                self.clearManualGrid()
                for row in range(10):
                    for col in range(10):
                        if pattern[row][col] == 1:
                            self.manual_buttons[row][col].state = True
                            self.manual_buttons[row][col].update_style()
                
                self.updateStatus(f"Pattern '{pattern_name}' loaded successfully")
            except Exception as e:
                self.updateStatus(f"Error loading pattern: {str(e)}")
    def initPatternTab(self):
        layout = QVBoxLayout()
        
        # Patterns group
        patterns_group = QGroupBox("Built-in Patterns")
        patterns_layout = QVBoxLayout()
        # Add new animations
        self.pattern_combo.addItem("Spiral")
        self.pattern_combo.addItem("Rainfall")
        self.pattern_combo.addItem("Fireworks")
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
        
        # Speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Animation Speed:"))
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(10)
        self.speed_slider.setValue(5)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(1)
        
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(QLabel("Fast"))
        
        patterns_layout.addLayout(speed_layout)
        
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


    # Add new pattern methods
    def spiral_pattern(self):
        matrix = create_empty_matrix()
        center_x, center_y = 4.5, 4.5
        max_radius = 7.0
        
        for radius in range(1, int(max_radius) + 1):
            # Draw a circle with the current radius
            for angle in range(0, 360, 10):
                rad_angle = math.radians(angle)
                x = int(center_x + radius * math.cos(rad_angle))
                y = int(center_y + radius * math.sin(rad_angle))
                
                if 0 <= x < 10 and 0 <= y < 10:
                    matrix[y][x] = 1
            
            # Update the display
            self.updateLEDMatrix(matrix)
            time.sleep(0.2)
            
            # Clear for next iteration
            matrix = create_empty_matrix()
        
        return matrix

    def rainfall_pattern(self):
        matrix = create_empty_matrix()
        
        for _ in range(20):  # Run for 20 iterations
            # Move existing drops down
            for row in range(9, 0, -1):
                for col in range(10):
                    matrix[row][col] = matrix[row-1][col]
            
            # Generate new drops at top row
            for col in range(10):
                matrix[0][col] = 1 if random.random() < 0.3 else 0
            
            # Update display
            self.updateLEDMatrix(matrix)
            time.sleep(0.2)
        
        return matrix

    def fireworks_pattern(self):
        matrix = create_empty_matrix()
        
        for _ in range(5):  # 5 fireworks
            # Random starting point at bottom
            start_col = random.randint(2, 7)
            
            # Rocket going up
            for row in range(9, 2, -1):
                matrix = create_empty_matrix()
                matrix[row][start_col] = 1
                self.updateLEDMatrix(matrix)
                time.sleep(0.1)
            
            # Explosion
            center_row, center_col = 2, start_col
            matrix = create_empty_matrix()
            
            for radius in range(1, 4):
                matrix = create_empty_matrix()
                for dr in range(-radius, radius+1):
                    for dc in range(-radius, radius+1):
                        if dr*dr + dc*dc <= radius*radius:
                            r, c = center_row + dr, center_col + dc
                            if 0 <= r < 10 and 0 <= c < 10:
                                matrix[r][c] = 1
                
                self.updateLEDMatrix(matrix)
                time.sleep(0.2)
            
            time.sleep(0.5)
        
        return create_empty_matrix()

    def startPattern(self):
        pattern_name = self.pattern_combo.currentText()
        # Get speed from slider
        speed = self.speed_slider.value()
        
        # Add new patterns to the if-elif chain
        if pattern_name == "Spiral":
            pattern_func = self.spiral_pattern
        elif pattern_name == "Rainfall":
            pattern_func = self.rainfall_pattern
        elif pattern_name == "Fireworks":
            pattern_func = self.fireworks_pattern
        else:
            # Handle other patterns or set a default
            self.updateStatus(f"Pattern {pattern_name} not implemented")
            return
        
        # Create thread with speed
        self.pattern_thread = PatternThread(pattern_func, speed)
        self.pattern_thread.finished_signal.connect(self.onPatternFinished)
        self.pattern_thread.start()
        
        # Update UI
        self.start_pattern_button.setEnabled(False)
        self.stop_pattern_button.setEnabled(True)
        
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
        # Add color settings
        color_group = QGroupBox("LED Color Settings")
        color_layout = QVBoxLayout()
        
        # LED color button
        self.led_color = QColor(255, 255, 0)  # Default to yellow
        self.color_button = QPushButton("Change LED Color")
        self.color_button.clicked.connect(self.changeLEDColor)
        
        # Show current color
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(30, 30)
        self.updateColorPreview()
        
        color_button_layout = QHBoxLayout()
        color_button_layout.addWidget(self.color_button)
        color_button_layout.addWidget(self.color_preview)
        color_button_layout.addStretch()
        
        color_layout.addLayout(color_button_layout)
        color_group.setLayout(color_layout)
        
        # Add to main layout
        layout.addWidget(color_group)
        # Status
        self.arduino_status = QLabel("Status: Connected to COM5" if arduino else "Status: Not connected")
        arduino_layout.addWidget(self.arduino_status)
        
        arduino_group.setLayout(arduino_layout)
        layout.addWidget(arduino_group)
        
        # Display settings
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()
        # Add new method for color changing
    def changeLEDColor(self):
        color = QColorDialog.getColor(self.led_color, self)
        if color.isValid():
            self.led_color = color
            self.updateColorPreview()
            self.updateLEDColors()

    def updateColorPreview(self):
        self.color_preview.setStyleSheet(f"background-color: {self.led_color.name()}; border: 1px solid #888;")

    def updateLEDColors(self):
        # Update all active LED buttons in the manual grid
        for row in range(10):
            for col in range(10):
                button = self.manual_buttons[row][col]
                if button.state:
                    button.setStyleSheet(f"background-color: {self.led_color.name()}; border: 1px solid #888;")
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
        """Start the marquee animation"""
        # Get values from UI
        text = self.text_input.text()  # Changed from toPlainText() to text()
        speed = self.speed_spin.value()  # Changed from speed_slider to speed_spin
        
        # Check if text is empty
        if not text:
            self.updateStatus("Please enter text for the marquee")
            return
        
        # Default values for missing parameters
        font_path = "fonts/5x7.ttf"  # Default font path
        font_size = 12  # Default font size
        invert = False  # Default invert setting
        direction = "left"  # Default direction
        flip_horizontal = False  # Default flip setting
        loops = 0  # Default loops (0 = infinite)
        
        # Create and start the marquee thread
        self.marquee_thread = MarqueeThread(
            text, speed, self.arduino, font_path, font_size, invert, 
            direction, flip_horizontal, loops
        )
        self.marquee_thread.status_update.connect(self.updateStatus)
        self.marquee_thread.start()
        
        # Update UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # Update status
        self.updateStatus(f"Marquee started with text: {text}")

        
    
    def stopMarquee(self):
        """Stop the marquee animation"""
        if self.marquee_thread and self.marquee_thread.isRunning():
            self.marquee_thread.stop()
            self.marquee_thread.wait()
            self.updateStatus("Marquee stopped")
        
        # Update UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def onMarqueeFinished(self):
        """Called when marquee animation finishes"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.updateStatus("Marquee finished")
        
    def onPatternFinished(self):
        """Called when pattern animation finishes"""
        self.start_pattern_button.setEnabled(True)
        self.stop_pattern_button.setEnabled(False)
        self.updateStatus("Pattern finished")


    def updateStatus(self, message):
        """Update the status message in the status bar"""
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)
        else:
            print(message)  # Fallback to console if status_label doesn't exist
        
    def updateLEDMatrix(self, matrix):
        # Update the current matrix
        self.current_matrix = matrix
        
        # Update the LED buttons
        for r in range(10):
            for c in range(10):
                if r < len(matrix) and c < len(matrix[r]):
                    self.led_buttons[r][c].setState(matrix[r][c])
    
    def clearDisplay(self):
        """Clear the LED matrix display"""
        # Create an empty matrix (all LEDs off)
        empty_matrix = [[0 for _ in range(10)] for _ in range(10)]
        
        # Update the display
        self.updateLEDMatrix(empty_matrix)
        
        # Update status
        self.updateStatus("Display cleared")
    
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
# LED Button for the interactive grid
# Find the LEDButton class and modify the on_color
class LEDButton(QPushButton):
    def __init__(self, row, col, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.state = False
        self.setFixedSize(30, 30)
        self.setCheckable(True)
        self.clicked.connect(self.toggle_state)
        self.update_style()
    
    def toggle_state(self):
        self.state = not self.state
        self.update_style()
    
    def update_style(self):
        if self.state:
            # Change to yellow color
            self.setStyleSheet("background-color: #FFFF00; border: 1px solid #888;")
        else:
            self.setStyleSheet("background-color: #333333; border: 1px solid #888;")
    def setState(self, state):
        """Set the LED state"""
        self.state = state
        self.updateStyle()
    
    def setColor(self, color):
        """Set the LED color"""
        self.color = color
        self.updateStyle()

# Worker thread for running the marquee animation
class AnimationWorker(QThread):
    update_signal = pyqtSignal(list)
    
    def __init__(self, animation_type='scroll', speed=500, direction='left'):
        super().__init__()
        self.running = True
        self.animation_type = animation_type
        self.speed = speed  # milliseconds between frames
        self.direction = direction
        self.matrix = create_empty_matrix()
        self.frame = 0
        self.custom_frames = []
    
    def run(self):
        """Run the animation loop"""
        while self.running:
            if self.animation_type == 'scroll':
                self.scroll_animation()
            elif self.animation_type == 'blink':
                self.blink_animation()
            elif self.animation_type == 'wave':
                self.wave_animation()
            elif self.animation_type == 'rain':
                self.rain_animation()
            elif self.animation_type == 'spiral':
                self.spiral_animation()
            elif self.animation_type == 'custom':
                self.custom_animation()
            
            # Emit the updated matrix
            self.update_signal.emit(self.matrix)
            
            # Wait for next frame
            time.sleep(self.speed / 1000.0)
            self.frame += 1
    
    def scroll_animation(self):
        """Scroll animation - scrolls a pattern across the display"""
        # Shift the matrix in the specified direction
        if self.direction == 'left':
            for row in range(10):
                self.matrix[row] = self.matrix[row][1:] + [self.matrix[row][0]]
        elif self.direction == 'right':
            for row in range(10):
                self.matrix[row] = [self.matrix[row][-1]] + self.matrix[row][:-1]
        elif self.direction == 'up':
            first_row = self.matrix[0]
            for row in range(9):
                self.matrix[row] = self.matrix[row + 1]
            self.matrix[9] = first_row
        elif self.direction == 'down':
            last_row = self.matrix[9]
            for row in range(9, 0, -1):
                self.matrix[row] = self.matrix[row - 1]
            self.matrix[0] = last_row
    
    def blink_animation(self):
        """Blink animation - alternates between all on and all off"""
        if self.frame % 2 == 0:
            self.matrix = create_full_matrix()
        else:
            self.matrix = create_empty_matrix()
    
    def wave_animation(self):
        """Wave animation - creates a sine wave pattern"""
        self.matrix = create_empty_matrix()
        
        # Calculate wave position based on frame
        for col in range(10):
            # Calculate sine wave position
            wave_pos = int(4.5 + 4 * np.sin((col + self.frame) * 0.5))
            if 0 <= wave_pos < 10:
                self.matrix[wave_pos][col] = '1'
    
    def rain_animation(self):
        """Rain animation - random drops falling from top to bottom"""
        # Shift everything down one row
        for row in range(9, 0, -1):
            self.matrix[row] = self.matrix[row - 1].copy()
        
        # Generate new random top row
        self.matrix[0] = ['1' if np.random.random() < 0.3 else '0' for _ in range(10)]
    
    def spiral_animation(self):
        """Spiral animation - creates a rotating spiral pattern"""
        self.matrix = create_empty_matrix()
        
        # Define spiral coordinates
        spiral_points = []
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # right, down, left, up
        
        x, y = 4, 4  # Start at center
        dir_idx = 0
        steps = 1
        step_count = 0
        step_change = 0
        
        # Generate spiral coordinates
        for _ in range(50):  # Limit to prevent infinite loop
            spiral_points.append((x, y))
            
            # Move in current direction
            dx, dy = directions[dir_idx]
            x += dx
            y += dy
            step_count += 1
            
            # Check if we need to change direction
            if step_count == steps:
                dir_idx = (dir_idx + 1) % 4
                step_count = 0
                step_change += 1
                
                # Increase steps after completing a half circle
                if step_change == 2:
                    steps += 1
                    step_change = 0
            
            # Check if we're still in bounds
            if not (0 <= x < 10 and 0 <= y < 10):
                break
        
        # Light up LEDs based on frame
        for i, (x, y) in enumerate(spiral_points):
            if (i + self.frame) % len(spiral_points) < 5:  # Show 5 points at a time
                self.matrix[y][x] = '1'
    
    def custom_animation(self):
        """Custom animation - cycles through user-defined frames"""
        if not self.custom_frames:
            self.matrix = create_empty_matrix()
            return
            
        # Get the current frame from the custom frames
        current_frame_idx = self.frame % len(self.custom_frames)
        self.matrix = self.custom_frames[current_frame_idx]
    
    def set_animation(self, animation_type):
        """Set the animation type"""
        self.animation_type = animation_type
        self.frame = 0
    
    def set_speed(self, speed):
        """Set the animation speed"""
        self.speed = speed
    
    def set_direction(self, direction):
        """Set the animation direction"""
        self.direction = direction
    
    def set_custom_frames(self, frames):
        """Set custom animation frames"""
        self.custom_frames = frames
    
    def stop(self):
        """Stop the animation thread"""
        self.running = False
        self.wait()
    # Modify the PatternThread class to use the speed setting
    class PatternThread(QThread):
        update_signal = pyqtSignal(list)
        finished_signal = pyqtSignal()
        
        def __init__(self, pattern_func, speed=5):
            super().__init__()
            self.pattern_func = pattern_func
            self.running = True
            self.speed = speed
        
        def run(self):
            try:
                self.pattern_func()
                self.finished_signal.emit()
            except Exception as e:
                print(f"Pattern thread error: {str(e)}")
                self.finished_signal.emit()
        
        def stop(self):
            self.running = False

class LEDMatrixApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("10x10 LED Matrix Controller")
        self.setMinimumSize(600, 500)
        
        # Initialize matrix and buttons
        self.matrix = create_empty_matrix()
        self.buttons = []
        self.current_color = QColor(255, 0, 0)  # Default color: red
        self.drawing_mode = "pixel"  # Default drawing mode
        self.saved_patterns = []
        self.animation_worker = None
        
        # Create main widget and layout
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Create tabs for different modes
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Create tabs
        draw_tab = QWidget()
        animation_tab = QWidget()
        settings_tab = QWidget()
        
        tab_widget.addTab(draw_tab, "Draw")
        tab_widget.addTab(animation_tab, "Animation")
        tab_widget.addTab(settings_tab, "Settings")
        
        # Set up the Draw tab
        self.setup_draw_tab(draw_tab)
        
        # Set up the Animation tab
        self.setup_animation_tab(animation_tab)
        
        # Set up the Settings tab
        self.setup_settings_tab(settings_tab)
    
    def setup_draw_tab(self, tab):
        """Set up the Draw tab UI"""
        layout = QVBoxLayout(tab)
        
        # Create LED matrix grid
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(1)
        
        # Create 10x10 grid of LED buttons
        for row in range(10):
            button_row = []
            for col in range(10):
                button = LEDButton(row, col)
                grid_layout.addWidget(button, row, col)
                button_row.append(button)
            self.buttons.append(button_row)
        
        layout.addWidget(grid_layout)
        
        # Drawing tools
        tools_group = QGroupBox("Drawing Tools")
        tools_layout = QHBoxLayout()
        
        # Drawing mode selection
        mode_group = QButtonGroup(self)
        
        pixel_mode = QRadioButton("Pixel")
        pixel_mode.setChecked(True)
        pixel_mode.clicked.connect(lambda: self.set_drawing_mode("pixel"))
        
        line_mode = QRadioButton("Line")
        line_mode.clicked.connect(lambda: self.set_drawing_mode("line"))
        
        rect_mode = QRadioButton("Rectangle")
        rect_mode.clicked.connect(lambda: self.set_drawing_mode("rectangle"))
        
        circle_mode = QRadioButton("Circle")
        circle_mode.clicked.connect(lambda: self.set_drawing_mode("circle"))
        
        fill_mode = QRadioButton("Fill")
        fill_mode.clicked.connect(lambda: self.set_drawing_mode("fill"))
        
        mode_group.addButton(pixel_mode)
        mode_group.addButton(line_mode)
        mode_group.addButton(rect_mode)
        mode_group.addButton(circle_mode)
        mode_group.addButton(fill_mode)
        
        tools_layout.addWidget(pixel_mode)
        tools_layout.addWidget(line_mode)
        tools_layout.addWidget(rect_mode)
        tools_layout.addWidget(circle_mode)
        tools_layout.addWidget(fill_mode)
        
        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        # Clear button
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_matrix)
        
        # Fill button
        fill_button = QPushButton("Fill All")
        fill_button.clicked.connect(self.fill_matrix)
        
        # Invert button
        invert_button = QPushButton("Invert")
        invert_button.clicked.connect(self.invert_matrix)
        
        # Color button
        color_button = QPushButton("Color")
        color_button.clicked.connect(self.choose_color)
        
        # Save pattern button
        save_button = QPushButton("Save Pattern")
        save_button.clicked.connect(self.save_pattern)
        
        # Load pattern button
        load_button = QPushButton("Load Pattern")
        load_button.clicked.connect(self.load_pattern)
        
        # Send to Arduino button
        send_button = QPushButton("Send to Arduino")
        send_button.clicked.connect(self.send_to_arduino)
        
        controls_layout.addWidget(clear_button)
        controls_layout.addWidget(fill_button)
        controls_layout.addWidget(invert_button)
        controls_layout.addWidget(color_button)
        controls_layout.addWidget(save_button)
        controls_layout.addWidget(load_button)
        controls_layout.addWidget(send_button)
        
        layout.addLayout(controls_layout)
    
    def setup_animation_tab(self, tab):
        """Set up the Animation tab UI"""
        layout = QVBoxLayout(tab)
        
        # Animation selection
        animation_group = QGroupBox("Animation Type")
        animation_layout = QVBoxLayout()
        
        self.animation_combo = QComboBox()
        self.animation_combo.addItems(["scroll", "blink", "wave", "rain", "spiral", "custom"])
        animation_layout.addWidget(self.animation_combo)
        
        animation_group.setLayout(animation_layout)
        layout.addWidget(animation_group)
        
        # Animation settings
        settings_group = QGroupBox("Animation Settings")
        settings_layout = QGridLayout()
        
        # Speed control
        speed_label = QLabel("Speed:")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 1000)
        self.speed_slider.setValue(500)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(100)
        
        # Direction control
        direction_label = QLabel("Direction:")
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["left", "right", "up", "down"])
        
        settings_layout.addWidget(speed_label, 0, 0)
        settings_layout.addWidget(self.speed_slider, 0, 1)
        settings_layout.addWidget(direction_label, 1, 0)
        settings_layout.addWidget(self.direction_combo, 1, 1)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Custom animation controls
        custom_group = QGroupBox("Custom Animation")
        custom_layout = QVBoxLayout()
        
        # Add frame button
        add_frame_button = QPushButton("Add Current Pattern as Frame")
        add_frame_button.clicked.connect(self.add_animation_frame)
        
        # Clear frames button
        clear_frames_button = QPushButton("Clear All Frames")
        clear_frames_button.clicked.connect(self.clear_animation_frames)
        
        # Save animation button
        save_anim_button = QPushButton("Save Animation")
        save_anim_button.clicked.connect(self.save_animation)
        
        # Load animation button
        load_anim_button = QPushButton("Load Animation")
        load_anim_button.clicked.connect(self.load_animation)
        
        custom_layout.addWidget(add_frame_button)
        custom_layout.addWidget(clear_frames_button)
        custom_layout.addWidget(save_anim_button)
        custom_layout.addWidget(load_anim_button)
        
        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)
        
        # Animation control buttons
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Animation")
        self.start_button.clicked.connect(self.start_animation)
        
        self.stop_button = QPushButton("Stop Animation")
        self.stop_button.clicked.connect(self.stop_animation)
        self.stop_button.setEnabled(False)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        
        layout.addLayout(control_layout)
    
    def setup_settings_tab(self, tab):
        """Set up the Settings tab UI"""
        layout = QVBoxLayout(tab)
        
        # Serial port settings
        serial_group = QGroupBox("Serial Port Settings")
        serial_layout = QGridLayout()
        
        port_label = QLabel("Port:")
        self.port_combo = QComboBox()
        
        # Find available serial ports
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            self.port_combo.addItems([p.device for p in ports])
            
            # Set current port if connected
            if ser and ser.port in [p.device for p in ports]:
                self.port_combo.setCurrentText(ser.port)
        except:
            self.port_combo.addItem(PORT)
        
        baud_label = QLabel("Baud Rate:")
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText(str(BAUD_RATE))
        
        connect_button = QPushButton("Connect")
        connect_button.clicked.connect(self.connect_arduino)
        
        serial_layout.addWidget(port_label, 0, 0)
        serial_layout.addWidget(self.port_combo, 0, 1)
        serial_layout.addWidget(baud_label, 1, 0)
        serial_layout.addWidget(self.baud_combo, 1, 1)
        serial_layout.addWidget(connect_button, 2, 0, 1, 2)
        
        serial_group.setLayout(serial_layout)
        layout.addWidget(serial_group)
        
        # Display settings
        display_group = QGroupBox("Display Settings")
        display_layout = QGridLayout()
        
        brightness_label = QLabel("Brightness:")
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 255)
        self.brightness_slider.setValue(127)
        self.brightness_slider.valueChanged.connect(self.set_brightness)
        
        display_layout.addWidget(brightness_label, 0, 0)
        display_layout.addWidget(self.brightness_slider, 0, 1)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        # Test patterns
        test_group = QGroupBox("Test Patterns")
        test_layout = QHBoxLayout()
        
        test_all_button = QPushButton("Test All LEDs")
        test_all_button.clicked.connect(self.test_all_leds)
        
        test_sequence_button = QPushButton("Run Test Sequence")
        test_sequence_button.clicked.connect(self.run_test_sequence)
        
        test_layout.addWidget(test_all_button)
        test_layout.addWidget(test_sequence_button)
        
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
    
    def set_drawing_mode(self, mode):
        """Set the current drawing mode"""
        self.drawing_mode = mode
    
    def choose_color(self):
        """Open color picker and set the current color"""
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.current_color = color
    
    def clear_matrix(self):
        """Clear the LED matrix"""
        self.matrix = create_empty_matrix()
        self.update_buttons()
    
    def fill_matrix(self):
        """Fill the entire LED matrix"""
        self.matrix = create_full_matrix()
        self.update_buttons()
    
    def invert_matrix(self):
        """Invert the LED matrix"""
        for row in range(10):
            for col in range(10):
                self.matrix[row][col] = '0' if self.matrix[row][col] == '1' else '1'
        self.update_buttons()
    
    def update_buttons(self):
        """Update the button states based on the matrix"""
        for row in range(10):
            for col in range(10):
                state = 1 if self.matrix[row][col] == '1' else 0
                self.buttons[row][col].setState(state)
                if state == 1:
                    self.buttons[row][col].setColor(self.current_color)
    
    def update_matrix_from_buttons(self):
        """Update the matrix based on button states"""
        for row in range(10):
            for col in range(10):
                self.matrix[row][col] = '1' if self.buttons[row][col].state == 1 else '0'
    
    def send_to_arduino(self):
        """Send the current matrix to Arduino"""
        self.update_matrix_from_buttons()
        send_led_matrix(self.matrix)
    
    def save_pattern(self):
        """Save the current pattern to a file"""
        self.update_matrix_from_buttons()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Pattern", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.matrix, f)
                print(f"Pattern saved to {file_path}")
            except Exception as e:
                print(f"Error saving pattern: {e}")
    
    def load_pattern(self):
        """Load a pattern from a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Pattern", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    self.matrix = json.load(f)
                self.update_buttons()
                print(f"Pattern loaded from {file_path}")
            except Exception as e:
                print(f"Error loading pattern: {e}")
    
    def add_animation_frame(self):
        """Add the current pattern as a frame to the custom animation"""
        self.update_matrix_from_buttons()
        
        # Create a deep copy of the current matrix
        frame = [row.copy() for row in self.matrix]
        self.saved_patterns.append(frame)
        
        print(f"Frame added. Total frames: {len(self.saved_patterns)}")
    
    def clear_animation_frames(self):
        """Clear all frames from the custom animation"""
        self.saved_patterns = []
        print("All animation frames cleared")
    
    def save_animation(self):
        """Save the current animation frames to a file"""
        if not self.saved_patterns:
            print("No animation frames to save")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Animation", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.saved_patterns, f)
                print(f"Animation saved to {file_path}")
            except Exception as e:
                print(f"Error saving animation: {e}")
    
    def load_animation(self):
        """Load animation frames from a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Animation", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    self.saved_patterns = json.load(f)
                print(f"Animation loaded from {file_path} ({len(self.saved_patterns)} frames)")
            except Exception as e:
                print(f"Error loading animation: {e}")
    
    def start_animation(self):
        """Start the animation"""
        if self.animation_worker and self.animation_worker.isRunning():
            self.stop_animation()
        
        # Create and configure the animation worker
        self.animation_worker = AnimationWorker(
            animation_type=self.animation_combo.currentText(),
            speed=self.speed_slider.value(),
            direction=self.direction_combo.currentText()
        )
        
        # Set custom frames if using custom animation
        if self.animation_combo.currentText() == 'custom' and self.saved_patterns:
            self.animation_worker.set_custom_frames(self.saved_patterns)
        
        # Connect the update signal
        self.animation_worker.update_signal.connect(self.update_from_animation)
        
        # Start the animation
        self.animation_worker.start()
        
        # Update UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
    
    def stop_animation(self):
        """Stop the animation"""
        if self.animation_worker and self.animation_worker.isRunning():
            self.animation_worker.stop()
            self.animation_worker = None
        
        # Update UI
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def update_from_animation(self, matrix):
        """Update the display from the animation thread"""
        self.matrix = matrix
        self.update_buttons()
        send_led_matrix(matrix)
    
    def connect_arduino(self):
        """Connect to the Arduino with the selected port and baud rate"""
        global ser
        
        # Close existing connection
        if ser:
            ser.close()
            ser = None
        
        # Get selected port and baud rate
        port = self.port_combo.currentText()
        baud = int(self.baud_combo.currentText())
        
        # Try to connect
        try:
            ser = serial.Serial(port, baud, timeout=1)
            time.sleep(2)  # Wait for connection to establish
            print(f"Connected to Arduino on {port} at {baud} baud")
        except Exception as e:
            print(f"Failed to connect to Arduino: {e}")
            ser = None
    
    def set_brightness(self, value):
        """Set the LED brightness"""
        if ser:
            send_command(f"B{value}")
    
    def test_all_leds(self):
        """Test all LEDs by turning them on"""
        send_led_matrix(create_full_matrix())
        
        # Update the UI
        self.matrix = create_full_matrix()
        self.update_buttons()
    
    def run_test_sequence(self):
        """Run a test sequence on the LED matrix"""
        # Stop any running animation
        self.stop_animation()
        
        # Create and start a test sequence animation
        self.animation_worker = AnimationWorker(animation_type='blink', speed=500)
        self.animation_worker.update_signal.connect(self.update_from_animation)
        self.animation_worker.start()
        
        # Update UI
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # Schedule to stop after 5 seconds
        QTimer.singleShot(5000, self.stop_animation)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop any running animation
        self.stop_animation()
        
        # Close serial connection
        global ser
        if ser:
            ser.close()
            ser = None
        
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = LEDMatrixApp()
    window.show()
    sys.exit(app.exec_())



# Run the application
if __name__ == "__main__":
    window = MarqueeApp()
    sys.exit(app.exec_())