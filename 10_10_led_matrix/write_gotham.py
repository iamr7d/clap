import keyboard
import serial
import time
import os
from PIL import Image, ImageDraw, ImageFont

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

def generate_character_pattern(char, font_path="C:/Users/rahul/OneDrive/Desktop/10_10_led_matrix/10_10_led_matrix/Gotham-Font/Gotham-Black.otf"):
    """Generate a 10x10 LED pattern for a character using Gotham font"""
    # Create a blank image with black background (0)
    img = Image.new('1', (10, 10), 0)
    draw = ImageDraw.Draw(img)
    
    # Check if font file exists
    if not os.path.exists(font_path):
        print(f"Warning: Font file {font_path} not found. Using default font.")
        # Try to find the font in common locations
        common_paths = [
            "C:/Windows/Fonts/Gotham-Bold.ttf",
            os.path.join(os.path.dirname(__file__), "Gotham-Font/Gotham-Black.otf"),
            "Gotham-Black.otf"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                font_path = path
                print(f"Found font at: {path}")
                break
        
        # If still not found, use a default font
        if not os.path.exists(font_path):
            try:
                font = ImageFont.truetype("Arial Bold", 12)  # Increased default font size
            except:
                font = ImageFont.load_default()
    
    # Load the Gotham font with increased size
    try:
        # Adjust font size based on character type
        font_size = 12
        if char.isalpha():
            font_size = 10  # Smaller size for letters
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        print(f"Error loading font: {e}. Using default.")
        font = ImageFont.load_default()
    
    # Calculate text size and position to center it
    try:
        # For newer Pillow versions
        text_width, text_height = draw.textbbox((0, 0), str(char), font=font)[2:4]
    except AttributeError:
        # For older Pillow versions
        text_width, text_height = draw.textsize(str(char), font=font)
    
    # Center the text with adjusted vertical position
    position = ((10 - text_width) // 2, (10 - text_height) // 2 - 2)  # Adjusted vertical position
    
    # Draw the character in white (1)
    draw.text(position, str(char), fill=1, font=font)
    
    # Flip the image horizontally to correct the display
    img = img.transpose(Image.FLIP_LEFT_RIGHT)
    
    # Convert image to matrix (list of lists)
    matrix = []
    for y in range(10):
        row = []
        for x in range(10):
            # Get pixel value (0 or 1)
            pixel = img.getpixel((x, y))
            row.append(pixel)
        matrix.append(row)
    
    return matrix

def send_led_matrix(matrix):
    """Send a 10x10 LED matrix as a 100-character string to Arduino."""
    data_str = 'W' + ''.join(str(cell) for row in matrix for cell in row)  # Flatten & add 'W'
    print("Sending Matrix Data:", data_str)
    print(send_command(data_str))

def all_leds_on():
    """Generate a pattern with all LEDs turned on"""
    return [[1 for _ in range(10)] for _ in range(10)]

def display_character(char):
    """Display a character on the LED matrix with animation"""
    # Reset the Arduino
    send_command("R")
    time.sleep(0.1)
    
    # First show all LEDs on
    all_on_pattern = all_leds_on()
    send_led_matrix(all_on_pattern)
    print("All LEDs ON")
    time.sleep(0.5)  # Keep all LEDs on for 0.5 seconds
    
    try:
        # Try to generate pattern using Gotham font
        pattern = generate_character_pattern(char)
        print(f"Using Gotham font for character '{char}'")
    except Exception as e:
        # Fall back if font rendering fails
        print(f"Font rendering failed: {e}. Cannot display character.")
        return
    
    # Send the pattern to the Arduino
    send_led_matrix(pattern)
    print(f"Displaying character: '{char}'")

def on_key_press(event):
    """Handle key press events"""
    # Allow numbers and letters
    if event.name in "0123456789" or (len(event.name) == 1 and event.name.isalpha()):
        display_character(event.name)

def main():
    # Reset the Arduino at startup
    send_command("R")
    print("Character display ready. Press any number (0-9) or letter key...")
    
    # Register key press event handler
    keyboard.on_press(on_key_press)
    
    # Keep the program running
    try:
        keyboard.wait('esc')  # Wait until 'esc' is pressed to exit
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up before exiting
        keyboard.unhook_all()
        if arduino:
            arduino.close()
        print("Program terminated.")

if __name__ == "__main__":
    main()