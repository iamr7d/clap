import serial
import time
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Control a 10x10 LED matrix via Arduino.")
parser.add_argument("row", type=int, help="Row number (0-9)")
args = parser.parse_args()
row = int (args.row /10)
col =  (args.row%10)

arduino = serial.Serial(port='COM5', baudrate=9600, timeout=1)

def send_command(cmd):
    arduino.write(f"{cmd}\n".encode())
    time.sleep(0.1)
    return arduino.readline().decode().strip()

# Reset Arduino
print(send_command("R"))

# Set Value 1 at the specified Row and Column
command = f"S1{row}{col}"
print(send_command(command))

arduino.close()
