import sys
import time
import numpy as np
import sounddevice as sd
import serial
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                           QWidget, QLabel, QComboBox, QSlider, QPushButton)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

def create_empty_matrix():
    """Create an empty 10x10 matrix filled with '0's"""
    return [['0' for _ in range(10)] for _ in range(10)]

def find_stereo_mix_device():
    """Find the Stereo Mix device if available"""
    devices = sd.query_devices()
    print("Available devices:")
    for i, device in enumerate(devices):
        print(f"{i}: {device['name']} (in: {device['max_input_channels']}, out: {device['max_output_channels']})")
        if 'Stereo Mix' in device['name'] and device['max_input_channels'] > 0:
            print(f"Found Stereo Mix device: {device['name']}")
            return i
    return None

def find_arduino_port():
    """Find the Arduino port"""
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            # Try to connect to each port
            try:
                ser = serial.Serial(port.device, 9600, timeout=1)
                ser.close()
                return port.device
            except (OSError, serial.SerialException):
                continue
        return None
    except Exception as e:
        print(f"Error finding Arduino port: {e}")
        return None

class AudioProcessor(QThread):
    update_signal = pyqtSignal(list)
    
    def __init__(self, device=None, sensitivity=1.0, mode='spectrum'):
        super().__init__()
        self.device = device
        self.sensitivity = sensitivity
        self.mode = mode
        self.running = True
        self.stream = None
    
    def run(self):
        """Start audio processing"""
        try:
            self.stream = sd.InputStream(
                device=self.device,
                channels=2,
                callback=self.audio_callback,
                blocksize=1024,
                samplerate=44100
            )
            self.stream.start()
            
            # Keep the thread running
            while self.running:
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error initializing audio: {e}")
        finally:
            self.cleanup()
        
    def audio_callback(self, indata, frames, time, status):
        """Callback function for audio processing"""
        if status:
            print(f"Status: {status}")
            
        try:
            # Convert to mono if stereo
            data = indata.copy()
            if data.shape[1] > 1:
                data = np.mean(data, axis=1)
            
            # Flatten and normalize
            data = data.flatten()
            
            # Amplify the signal for better visualization
            data = data * 3.0  # Increase amplification
            
            if self.mode == 'spectrum':
                matrix = self.create_spectrum_visualization(data)
            elif self.mode == 'waveform':
                matrix = self.create_waveform_visualization(data)
            elif self.mode == 'pulse':
                matrix = self.create_pulse_visualization(data)
            elif self.mode == 'graph':  # New mode
                matrix = self.create_graph_visualization(data)
            else:
                matrix = create_empty_matrix()
            
            self.update_signal.emit(matrix)
        except Exception as e:
            print(f"Audio processing error: {e}")
    
    def set_sensitivity(self, value):
        """Set the sensitivity value"""
        self.sensitivity = value
    
    def set_mode(self, mode):
        """Set the visualization mode"""
        self.mode = mode
    
    def cleanup(self):
        """Clean up resources"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
    
    def stop(self):
        """Stop the thread"""
        self.running = False
        self.cleanup()
        self.wait()
    
    def create_spectrum_visualization(self, data):
        """Create a spectrum-like visualization (vertical bars)"""
        # Apply FFT to get frequency data
        fft_data = np.abs(np.fft.rfft(data))
        
        # Normalize and apply sensitivity
        fft_data = fft_data / np.max(fft_data) if np.max(fft_data) > 0 else fft_data
        fft_data = fft_data * self.sensitivity
        
        # Emphasize bass and mid frequencies (similar to FxSound's emphasis)
        bass_boost = 1.5  # Boost bass frequencies
        mid_boost = 1.2   # Boost mid frequencies
        
        # Divide spectrum into frequency regions
        bass_end = len(fft_data) // 16
        mid_end = len(fft_data) // 4
        
        # Apply boosts to different frequency ranges
        fft_data[:bass_end] *= bass_boost
        fft_data[bass_end:mid_end] *= mid_boost
        
        # Create frequency bands (10 bands for 10 columns)
        num_bands = 10
        bands = np.array_split(fft_data[:len(fft_data)//3], num_bands)  # Use lower frequencies
        band_energies = [np.mean(band) for band in bands]
        
        # Create the matrix
        matrix = create_empty_matrix()
        
        # Fill the matrix with vertical bars
        for col, energy in enumerate(band_energies):
            # Calculate height (0-10) with improved scaling
            height = min(10, int(energy * 12))  # Increased scaling factor
            
            # Fill the column from bottom to height
            for row in range(10 - height, 10):
                matrix[row][col] = '1'
        
        return matrix
            
    def create_waveform_visualization(self, data):
        """Create a waveform visualization (horizontal line)"""
        matrix = create_empty_matrix()
        
        # Divide the data into 10 segments
        segments = np.array_split(data, 10)
        
        for col, segment in enumerate(segments):
            # Calculate the average amplitude for this segment
            amplitude = np.mean(np.abs(segment)) * self.sensitivity * 10
            
            # Map to row (0-9)
            row = min(9, int(amplitude * 9))
            
            # Set the LED
            matrix[row][col] = '1'
        
        return matrix
    
    def create_pulse_visualization(self, data):
        """Create a pulse visualization (expanding circle)"""
        matrix = create_empty_matrix()
        
        # Calculate audio level
        rms = np.sqrt(np.mean(np.square(data)))
        level = min(5, int(rms * self.sensitivity * 20))
        
        # Create expanding circles based on audio level
        center_x, center_y = 4.5, 4.5  # Center of the 10x10 matrix
        
        for row in range(10):
            for col in range(10):
                # Calculate distance from center
                distance = np.sqrt((row - center_y)**2 + (col - center_x)**2)
                
                # Light up LEDs based on the distance and audio level
                if distance <= level:
                    matrix[row][col] = '1'
        
        return matrix
    
    def create_graph_visualization(self, data):
        """Create a graph-like visualization with peaks and valleys"""
        # Apply FFT to get frequency data
        fft_data = np.abs(np.fft.rfft(data))
        
        # Normalize and apply sensitivity
        fft_data = fft_data / np.max(fft_data) if np.max(fft_data) > 0 else fft_data
        fft_data = fft_data * self.sensitivity * 1.5  # Increased sensitivity
        
        # Apply frequency boosts
        bass_boost = 2.0
        mid_boost = 1.5
        
        # Divide spectrum into frequency regions
        bass_end = len(fft_data) // 16
        mid_end = len(fft_data) // 4
        
        # Apply boosts
        fft_data[:bass_end] *= bass_boost
        fft_data[bass_end:mid_end] *= mid_boost
        
        # Create frequency bands (10 bands for 10 columns)
        num_bands = 10
        bands = np.array_split(fft_data[:len(fft_data)//3], num_bands)
        band_energies = [np.mean(band) for band in bands]
        
        # Create the matrix
        matrix = create_empty_matrix()
        
        # Create a graph-like visualization
        for col, energy in enumerate(band_energies):
            # Calculate height (0-10)
            height = min(9, int(energy * 15))  # Higher scaling for more dynamic range
            
            # Draw the peak LED
            if 0 <= height < 10:
                matrix[9-height][col] = '1'
                
            # Draw a trail below the peak (fading effect)
            for i in range(1, 3):  # 2-LED trail
                trail_pos = height + i
                if trail_pos < 10:
                    intensity = 1.0 - (i * 0.3)  # Fade intensity
                    if random.random() < intensity:  # Probabilistic display for sparkle effect
                        matrix[9-trail_pos][col] = '1'
        
        return matrix

class MusicVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music Visualizer")
        self.setGeometry(100, 100, 400, 200)
        
        # Find Arduino port
        self.arduino_port = find_arduino_port()
        if self.arduino_port:
            try:
                self.arduino = serial.Serial(self.arduino_port, 9600)
                print(f"Connected to Arduino on {self.arduino_port}")
            except Exception as e:
                print(f"Error connecting to Arduino: {e}")
                self.arduino = None
        else:
            print("Arduino not found")
            self.arduino = None
        
        # Find Stereo Mix device
        self.device_id = find_stereo_mix_device()
        if self.device_id is None:
            print("Stereo Mix not found, using default input device")
            self.device_id = sd.default.device[0]
        
        # Get device info
        device_info = sd.query_devices(self.device_id)
        print(f"Using input device: {device_info['name']}")
        print(f"Device channels: {device_info['max_input_channels']}")
        
        # Initialize audio processor
        self.audio_processor = AudioProcessor(device=self.device_id)
        self.audio_processor.update_signal.connect(self.update_visualization)
        
        # Create UI
        self.init_ui()
        
        # Start audio processing
        self.audio_processor.start()
    
    def init_ui(self):
        """Initialize the UI"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout()
        
        # Mode selector
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Mode:")
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(['spectrum', 'waveform', 'pulse', 'graph'])
        self.mode_selector.setCurrentText('graph')  # Set graph as default
        self.mode_selector.currentTextChanged.connect(self.change_mode)
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_selector)
        
        # Sensitivity slider
        sensitivity_layout = QHBoxLayout()
        sensitivity_label = QLabel("Sensitivity:")
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setMinimum(1)
        self.sensitivity_slider.setMaximum(100)
        self.sensitivity_slider.setValue(50)
        self.sensitivity_slider.valueChanged.connect(self.change_sensitivity)
        
        sensitivity_layout.addWidget(sensitivity_label)
        sensitivity_layout.addWidget(self.sensitivity_slider)
        
        # Add layouts to main layout
        layout.addLayout(mode_layout)
        layout.addLayout(sensitivity_layout)
        
        main_widget.setLayout(layout)
    
    def change_mode(self, mode):
        """Change the visualization mode"""
        self.audio_processor.set_mode(mode)
    
    def change_sensitivity(self, value):
        """Change the sensitivity"""
        sensitivity = value / 50.0  # Map 1-100 to 0.02-2.0
        self.audio_processor.set_sensitivity(sensitivity)
    
    def update_visualization(self, matrix):
        """Update the visualization based on audio data"""
        if self.arduino:
            try:
                # Convert matrix to string
                matrix_str = ''.join([''.join(row) for row in matrix])
                
                # Send to Arduino
                self.arduino.write(matrix_str.encode())
                
            except Exception as e:
                print(f"Error sending to Arduino: {e}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.audio_processor.stop()
        if self.arduino:
            self.arduino.close()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MusicVisualizer()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()