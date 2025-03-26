import serial
import time
import random
import math
import keyboard
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

def send_led_matrix(matrix):
    """Send a 10x10 LED matrix as a 100-character string to Arduino."""
    # Convert any boolean values to integers (0 or 1)
    data_str = 'W' + ''.join(str(int(cell)) if isinstance(cell, bool) else str(cell) 
                             for row in matrix for cell in row)  # Flatten & add 'W'
    print("Sending Matrix Data:", data_str)
    return send_command(data_str)

def create_empty_matrix():
    """Create an empty 10x10 matrix (all LEDs off)"""
    return [[0 for _ in range(10)] for _ in range(10)]

def create_full_matrix():
    """Create a full 10x10 matrix (all LEDs on)"""
    return [[1 for _ in range(10)] for _ in range(10)]

# ===== ANIMATION EFFECTS =====

def effect_blink_all(cycles=5, speed=0.3):
    """Simple blinking effect - all LEDs on/off"""
    print("Running: Blink All")
    for _ in range(cycles):
        send_led_matrix(create_full_matrix())
        time.sleep(speed)
        send_led_matrix(create_empty_matrix())
        time.sleep(speed)
    # End with all LEDs on
    send_led_matrix(create_full_matrix())

def effect_random_sparkle(duration=5, density=0.3, speed=0.1):
    """Random sparkling effect"""
    print("Running: Random Sparkle")
    start_time = time.time()
    while time.time() - start_time < duration:
        matrix = create_empty_matrix()
        # Set random LEDs on based on density
        for y in range(10):
            for x in range(10):
                if random.random() < density:
                    matrix[y][x] = 1
        send_led_matrix(matrix)
        time.sleep(speed)

def effect_wave(cycles=3, speed=0.1):
    """Wave effect moving across the matrix"""
    print("Running: Wave Effect")
    for _ in range(cycles):
        # Wave moving from left to right
        for offset in range(20):  # Wider than the matrix for smooth transition
            matrix = create_empty_matrix()
            for y in range(10):
                for x in range(10):
                    # Create a sine wave pattern
                    if (x + offset) % 20 < 10:  # Only light up half the wave
                        wave_height = int(5 + 4 * math.sin((x + offset) * math.pi / 5))
                        if y == wave_height:
                            matrix[y][x] = 1
            send_led_matrix(matrix)
            time.sleep(speed)

def effect_rain(duration=5, speed=0.1, density=0.2):
    """Rain effect - droplets falling from top to bottom"""
    print("Running: Rain Effect")
    # Initialize raindrops at random positions at the top
    raindrops = []
    start_time = time.time()
    
    while time.time() - start_time < duration:
        # Chance to create new raindrops
        if random.random() < density:
            raindrops.append([0, random.randint(0, 9)])  # [row, col]
        
        # Update raindrop positions
        matrix = create_empty_matrix()
        new_raindrops = []
        for drop in raindrops:
            row, col = drop
            if row < 10:  # If still on screen
                matrix[row][col] = 1
                new_raindrops.append([row + 1, col])  # Move down
        
        raindrops = new_raindrops
        send_led_matrix(matrix)
        time.sleep(speed)

def effect_snake(length=5, cycles=2, speed=0.2):
    """Snake moving around the matrix"""
    print("Running: Snake Effect")
    # Directions: 0=right, 1=down, 2=left, 3=up
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    
    for _ in range(cycles):
        # Start with a snake in the middle
        snake = [(5, 5)]
        direction = 0  # Start moving right
        
        # Move the snake around
        for _ in range(50):  # Number of moves
            matrix = create_empty_matrix()
            
            # Draw the snake
            for segment in snake:
                y, x = segment
                if 0 <= y < 10 and 0 <= x < 10:
                    matrix[y][x] = 1
            
            # Move the snake
            head_y, head_x = snake[0]
            dy, dx = directions[direction]
            new_head = (head_y + dy, head_x + dx)
            
            # Check if we need to change direction (hit wall or about to)
            new_y, new_x = new_head
            if new_y < 0 or new_y >= 10 or new_x < 0 or new_x >= 10:
                # Change direction
                direction = (direction + 1) % 4
                dy, dx = directions[direction]
                new_head = (head_y + dy, head_x + dx)
            
            # Add new head
            snake.insert(0, new_head)
            
            # Remove tail if snake is too long
            if len(snake) > length:
                snake.pop()
            
            send_led_matrix(matrix)
            time.sleep(speed)

def effect_marquee_text(text="HELLO", speed=0.2, loops=2):
    """Scrolling marquee text effect"""
    print(f"Running: Marquee Text '{text}'")
    
    # Create a wide image to hold the scrolling text
    width = 10 + len(text) * 8  # Each character is roughly 6-8 pixels wide
    img = Image.new('1', (width, 10), 0)
    draw = ImageDraw.Draw(img)
    
    # Try to load a font
    try:
        font = ImageFont.truetype("arial.ttf", 9)
    except:
        font = ImageFont.load_default()
    
    # Draw the text
    draw.text((10, 0), text, fill=1, font=font)
    
    # Scroll the text
    for loop in range(loops):
        for offset in range(width):
            matrix = create_empty_matrix()
            
            # Extract the visible portion
            for y in range(10):
                for x in range(10):
                    if 0 <= x + offset < width:
                        try:
                            matrix[y][x] = 1 if img.getpixel((x + offset, y)) else 0
                        except:
                            matrix[y][x] = 0
            
            send_led_matrix(matrix)
            time.sleep(speed)

def effect_fireworks(duration=10, speed=0.1):
    """Fireworks effect - rockets and explosions"""
    print("Running: Fireworks Effect")
    start_time = time.time()
    
    # Track active rockets and explosions
    rockets = []
    explosions = []
    
    while time.time() - start_time < duration:
        matrix = create_empty_matrix()
        
        # Chance to create new rocket
        if random.random() < 0.1 and len(rockets) < 3:
            rockets.append([9, random.randint(0, 9), random.uniform(0.5, 1.0)])  # [row, col, speed]
        
        # Update rockets
        new_rockets = []
        for rocket in rockets:
            row, col, rocket_speed = rocket
            if row > 0:  # If still rising
                matrix[int(row)][col] = 1
                new_rockets.append([row - rocket_speed, col, rocket_speed])
            else:
                # Rocket reached top, create explosion
                explosions.append([0, col, 0])  # [age, center_col, center_row]
        
        rockets = new_rockets
        
        # Update explosions
        new_explosions = []
        for explosion in explosions:
            age, center_x, center_y = explosion
            if age < 5:  # Explosion lifetime
                # Draw explosion particles
                radius = age + 1
                for dy in range(-radius, radius+1):
                    for dx in range(-radius, radius+1):
                        # Create circular pattern
                        if dx*dx + dy*dy <= radius*radius:
                            y, x = int(center_y + dy), int(center_x + dx)
                            if 0 <= y < 10 and 0 <= x < 10:
                                # Fade out with age
                                if random.random() > age/5:
                                    matrix[y][x] = 1
                
                new_explosions.append([age + 0.5, center_x, center_y])
        
        explosions = new_explosions
        
        send_led_matrix(matrix)
        time.sleep(speed)

def effect_heartbeat(cycles=5, speed=0.1):
    """Heartbeat effect - pulsing heart"""
    print("Running: Heartbeat Effect")
    
    # Define a heart shape
    heart_small = [
        [0,0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0,0],
        [0,0,1,1,0,0,1,1,0,0],
        [0,1,1,1,1,1,1,1,1,0],
        [0,1,1,1,1,1,1,1,1,0],
        [0,0,1,1,1,1,1,1,0,0],
        [0,0,0,1,1,1,1,0,0,0],
        [0,0,0,0,1,1,0,0,0,0],
        [0,0,0,0,0,0,0,0,0,0],
        [0,0,0,0,0,0,0,0,0,0]
    ]
    
    heart_large = [
        [0,0,0,0,0,0,0,0,0,0],
        [0,1,1,0,0,0,0,1,1,0],
        [1,1,1,1,0,0,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1],
        [1,1,1,1,1,1,1,1,1,1],
        [0,1,1,1,1,1,1,1,1,0],
        [0,0,1,1,1,1,1,1,0,0],
        [0,0,0,1,1,1,1,0,0,0],
        [0,0,0,0,1,1,0,0,0,0],
        [0,0,0,0,0,0,0,0,0,0]
    ]
    
    for _ in range(cycles):
        # First beat
        send_led_matrix(heart_small)
        time.sleep(speed)
        send_led_matrix(heart_large)
        time.sleep(speed)
        send_led_matrix(heart_small)
        time.sleep(speed * 3)  # Pause between beats
        
        # Second beat
        send_led_matrix(heart_small)
        time.sleep(speed)
        send_led_matrix(heart_large)
        time.sleep(speed)
        send_led_matrix(heart_small)
        time.sleep(speed * 5)  # Longer pause after second beat

def effect_spiral(cycles=3, speed=0.1):
    """Spiral effect - drawing from outside to inside and back"""
    print("Running: Spiral Effect")
    
    for _ in range(cycles):
        # Define spiral path (coordinates from outside to center)
        spiral_path = []
        for layer in range(5):  # 5 layers in a 10x10 grid
            # Top edge (right to left)
            for x in range(9-layer, layer-1, -1):
                spiral_path.append((layer, x))
            
            # Left edge (top to bottom)
            for y in range(layer+1, 10-layer):
                spiral_path.append((y, layer))
            
            # Bottom edge (left to right)
            for x in range(layer+1, 10-layer):
                spiral_path.append((9-layer, x))
            
            # Right edge (bottom to top)
            for y in range(8-layer, layer, -1):
                spiral_path.append((y, 9-layer))
        
        # Animate spiral in
        matrix = create_empty_matrix()
        for pos in spiral_path:
            y, x = pos
            matrix[y][x] = 1
            send_led_matrix(matrix)
            time.sleep(speed)
        
        # Animate spiral out
        for pos in reversed(spiral_path):
            y, x = pos
            matrix[y][x] = 0
            send_led_matrix(matrix)
            time.sleep(speed)

def effect_matrix_rain(duration=10, speed=0.1, density=0.1):
    """Matrix-style digital rain effect"""
    print("Running: Matrix Digital Rain")
    start_time = time.time()
    
    # Initialize rain streams
    streams = [[] for _ in range(10)]  # One potential stream per column
    
    while time.time() - start_time < duration:
        matrix = create_empty_matrix()
        
        # Chance to create new streams
        for col in range(10):
            if not streams[col] and random.random() < density:
                # Start a new stream with random length
                length = random.randint(3, 8)
                streams[col] = [-1] * length  # Start above the display
        
        # Update and draw streams
        for col, stream in enumerate(streams):
            if stream:
                # Move stream down
                stream = [pos + 1 for pos in stream]
                
                # Remove positions that have gone off screen
                while stream and stream[0] >= 10:
                    stream.pop(0)
                
                # Draw the stream with fading effect
                for i, pos in enumerate(stream):
                    if 0 <= pos < 10:
                        # Brighter at the head, fading toward tail
                        if i == len(stream) - 1 or random.random() > 0.3:
                            matrix[pos][col] = 1
                
                streams[col] = stream
        
        send_led_matrix(matrix)
        time.sleep(speed)

def effect_game_of_life(iterations=50, speed=0.2):
    """Conway's Game of Life simulation"""
    print("Running: Conway's Game of Life")
    
    # Initialize with random cells
    matrix = create_empty_matrix()
    for y in range(10):
        for x in range(10):
            matrix[y][x] = 1 if random.random() < 0.3 else 0
    
    send_led_matrix(matrix)
    time.sleep(speed)
    
    # Run the simulation
    for _ in range(iterations):
        new_matrix = create_empty_matrix()
        
        for y in range(10):
            for x in range(10):
                # Count neighbors (including wrapping around edges)
                neighbors = 0
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = (x + dx) % 10, (y + dy) % 10
                        neighbors += matrix[ny][nx]
                
                # Apply Conway's rules
                if matrix[y][x] == 1:
                    # Live cell
                    if neighbors < 2 or neighbors > 3:
                        new_matrix[y][x] = 0  # Dies
                    else:
                        new_matrix[y][x] = 1  # Survives
                else:
                    # Dead cell
                    if neighbors == 3:
                        new_matrix[y][x] = 1  # Becomes alive
        
        matrix = new_matrix
        send_led_matrix(matrix)
        time.sleep(speed)

def run_demo():
    """Run a demo of all effects"""
    print("Starting LED Matrix Animation Demo")
    print("Press ESC to exit at any time")
    
    # Reset the Arduino
    send_command("R")
    time.sleep(0.5)
    
    try:
        while True:
            if keyboard.is_pressed('esc'):
                break
                
            # Run each effect
            effect_blink_all(cycles=3, speed=0.2)
            if keyboard.is_pressed('esc'): break
            
            effect_random_sparkle(duration=5, density=0.3, speed=0.1)
            if keyboard.is_pressed('esc'): break
            
            effect_wave(cycles=2, speed=0.1)
            if keyboard.is_pressed('esc'): break
            
            effect_rain(duration=5, speed=0.1)
            if keyboard.is_pressed('esc'): break
            
            effect_snake(length=5, cycles=1, speed=0.2)
            if keyboard.is_pressed('esc'): break
            
            effect_marquee_text(text="10x10 LED", speed=0.15, loops=1)
            if keyboard.is_pressed('esc'): break
            
            effect_fireworks(duration=7, speed=0.1)
            if keyboard.is_pressed('esc'): break
            
            effect_heartbeat(cycles=3, speed=0.1)
            if keyboard.is_pressed('esc'): break
            
            effect_spiral(cycles=2, speed=0.05)
            if keyboard.is_pressed('esc'): break
            
            effect_matrix_rain(duration=7, speed=0.1)
            if keyboard.is_pressed('esc'): break
            
            effect_game_of_life(iterations=30, speed=0.2)
            if keyboard.is_pressed('esc'): break
            
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up
        if arduino:
            arduino.close()
        print("Animation demo terminated")

def show_menu():
    """Display interactive menu for selecting animations"""
    menu_options = [
        ("1", "Blink All", effect_blink_all),
        ("2", "Random Sparkle", effect_random_sparkle),
        ("3", "Wave Effect", effect_wave),
        ("4", "Rain Effect", effect_rain),
        ("5", "Snake", effect_snake),
        ("6", "Marquee Text", effect_marquee_text),
        ("7", "Fireworks", effect_fireworks),
        ("8", "Heartbeat", effect_heartbeat),
        ("9", "Spiral", effect_spiral),
        ("0", "Matrix Digital Rain", effect_matrix_rain),
        ("L", "Game of Life", effect_game_of_life),
        ("D", "Run Demo (all effects)", run_demo),
        ("Q", "Quit", None)
    ]
    
    while True:
        print("\n===== 10x10 LED MATRIX ANIMATIONS =====")
        for key, name, _ in menu_options:
            print(f"{key}: {name}")
        
        choice = input("\nSelect an animation (or Q to quit): ").upper()
        
        if choice == 'Q':
            break
            
        for key, name, func in menu_options:
            if choice == key:
                if func:
                    try:
                        func()
                    except Exception as e:
                        print(f"Error running animation: {e}")
                break
        else:
            print("Invalid selection. Please try again.")

def main():
    # Reset the Arduino at startup
    send_command("R")
    time.sleep(0.5)
    
    show_menu()
    
    # Clean up
    if arduino:
        arduino.close()
    print("Program terminated.")

if __name__ == "__main__":
    main()