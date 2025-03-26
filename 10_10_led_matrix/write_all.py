import serial
import time

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
        response = arduino.readline().decode().strip()
        print(f"Arduino response: {response}")
        return response
    else:
        print(f"Would send: {cmd}")
        return "Arduino not connected"

def all_leds_on_direct():
    """Send a direct command to turn on all LEDs"""
    # This sends the 'A' command which should turn on all LEDs
    # if your Arduino sketch supports this command
    return send_command("A")

def all_leds_on_matrix():
    """Generate a pattern with all LEDs turned on using the matrix approach"""
    # Create a matrix of all 1's
    matrix = [[1 for _ in range(10)] for _ in range(10)]
    
    # Convert to string and send
    data_str = 'W' + ''.join(str(cell) for row in matrix for cell in row)
    print("Sending Matrix Data:", data_str)
    return send_command(data_str)

def main():
    # Reset the Arduino at startup
    print("Resetting Arduino...")
    send_command("R")
    time.sleep(0.5)
    
    # Try the direct approach first
    print("\nAttempting to turn on all LEDs using direct command...")
    all_leds_on_direct()
    time.sleep(1)
    
    # Then try the matrix approach
    print("\nAttempting to turn on all LEDs using matrix approach...")
    all_leds_on_matrix()
    
    print("\nAll LEDs should now be ON. Press Ctrl+C to exit.")
    
    try:
        # Keep the program running until interrupted
        while True:
            # Resend the command every 5 seconds to ensure LEDs stay on
            time.sleep(5)
            print("\nResending all LEDs ON command...")
            all_leds_on_matrix()
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up before exiting
        if arduino:
            arduino.close()
        print("Program terminated.")

if __name__ == "__main__":
    main()