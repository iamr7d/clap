import serial
import time

arduino = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, timeout=1)
time.sleep(2)  # Wait for Arduino to initialize

def send_command(cmd):
    arduino.write(f"{cmd}\n".encode())
    time.sleep(0.1)
    return arduino.readline().decode().strip()

# Reset Arduino
print(send_command("R"))

# Set Value 1 at Row 2, Column 3
print(send_command("S123"))

arduino.close()
