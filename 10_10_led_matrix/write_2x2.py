


import serial
import time

arduino = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, timeout=1)
# time.sleep(2)  # Wait for Arduino to initialize

def send_command(cmd):
    arduino.write(f"{cmd}\n".encode())
    time.sleep(0.1)
    return arduino.readline().decode().strip()

print(send_command("R"))

# Reset Arduino
print(send_command("W1111"))

arduino.close()