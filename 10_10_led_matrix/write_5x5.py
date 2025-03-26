import serial
import time

arduino = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, timeout=1)


def send_command(cmd):
    """Send a command string to Arduino."""
    arduino.write(f"{cmd}\n".encode())
    time.sleep(0.1)
    return arduino.readline().decode().strip()

# Reset Arduino
print(send_command("R"))


# Send 10x10 LED Matrix Data
def send_led_matrix(matrix):
    """Send a 10x10 LED matrix as a 100-character string to Arduino."""
    data_str = 'W' + ''.join(str(cell) for row in matrix for cell in row)  # Flatten & add 'W'
    print("Sending Matrix Data:", data_str)
    print(send_command(data_str))

# Example 10x10 Boolean Matrix (Checkerboard Pattern)
led_matrix = [
    [1,0,1,0,1],
    [0,1,0,1,0],
    [1,0,1,0,1],
    [0,1,0,1,0],
    [1,0,1,0,1]
]

send_led_matrix(led_matrix)

arduino.close()

