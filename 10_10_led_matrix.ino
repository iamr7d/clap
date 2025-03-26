#define CLOCK_PIN 10
#define RESET_PIN 11

class LedMatrix {
  public:
    LedMatrix (int clockPin, int resetPin, 
               int row0_pin, int row1_pin, int row2_pin, int row3_pin, int row4_pin, 
               int row5_pin, int row6_pin, int row7_pin, int row8_pin, int row9_pin) {
      _clockPin = clockPin;
      _resetPin = resetPin;
      _rowPins[0] = row0_pin;
      _rowPins[1] = row1_pin;
      _rowPins[2] = row2_pin;
      _rowPins[3] = row3_pin;
      _rowPins[4] = row4_pin;
      _rowPins[5] = row5_pin;
      _rowPins[6] = row6_pin;
      _rowPins[7] = row7_pin;
      _rowPins[8] = row8_pin;
      _rowPins[9] = row9_pin;
    }

    void setup() {
      pinMode(_clockPin, OUTPUT);
      pinMode(_resetPin, OUTPUT);

      for (int pin = 0; pin <= 9; pin++) {
        pinMode(_rowPins[pin], OUTPUT);
      }
    }

    void reset() {
      digitalWrite(_resetPin, HIGH);
      digitalWrite(_resetPin, LOW);
    }

    void setRow(int row) {
      digitalWrite(row, LOW);
    }

    void select_column(int column) {

      for (int _column = 0; _column < column; _column++) 
        clock();
      
    }

    void set(int row, int column) {
      select_column(column);
      digitalWrite(_rowPins[row], LOW);
    }

    void clock()
    {
      digitalWrite(_clockPin, LOW);
      digitalWrite(_clockPin, HIGH);
    }
    void clear()
    {
      for (int row = 0; row <= 9; row++) {
        digitalWrite(_rowPins[row], HIGH);
      }
      reset();
    }

  private:
    int _clockPin;
    int _resetPin;
    int _rowPins[10];
};

LedMatrix matrix (CLOCK_PIN, RESET_PIN, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9);

/*
  Driver class is used to set the matrix value
  and display the matrix value from the string get from the serial port

  reset chareter will be r 

  a string of chareters 100 will come with  (0,0) to (10,10)
  
  a count will be tere and if it faills  systerm will reste and 
  sent bad agnoleggemeneyt\
  
  */
  
  
// Driver //
int gRow = 0, gColumn = 0;

  int reset_cb ()
  {
    matrix.reset();
    matrix.clear();
    Serial.println("reset");
    gRow = 0;
    gColumn = 0;
    return -1;
  }
  

  int set_cb()
  {
    
    // matrix.set(int r, int  c);
    // gRow = r; 
    // gColumn = c;
    
    return -1;
  }
  
  int data_string[10];
  
  int read()
  {
     int cnt = 0;
    if (Serial.available() > 0) {

      char incomingByte = Serial.read();
      data_string[cnt++] = incomingByte;

      if (incomingByte == 'r') {
        reset_cb();
      }
      
      if (incomingByte == 's') {
        set_cb();
      }
      if(cnt > 10)
      {
        Serial.println(*data_string);
        cnt = 0;
      }
    }
    return -1;
  }
  

  int _matrix_value[10][10];


  // driver 


// void setup() {
  
//   matrix.setup();
//   matrix.clear();

//   Serial.begin(9600);
// }


// void loop() { 
//   matrix.reset();
//   matrix.clear();
   
//   matrix.set(0, 0);
//   matrix.clear();
//   matrix.set(3, 3);
//   matrix.clear();
//   matrix.set (gRow,gColumn);
//   matrix.clear();

//   read();

// }
int ledMatrix[10][10];  // Store LED states

int mode_selectin_state = 0;

int set_char()
{
  for (int i = 0; i < 100; i++) 
  {
    int row = i / 10;
    int col = i % 10;
   
    if(ledMatrix[row][col] == 1)
    {
      matrix.set(row, col);
      matrix.clear(); 
    }
  }
}

void setup() {
    Serial.begin(9600);
    Serial.println("Arduino Ready");
    matrix.setup();
    matrix.clear();

    for (int i = 0; i < 10; i++) {
      for (int j = 0; j < 10; j++) {
        ledMatrix[i][j] = 0;
      }
    }
}

void loop() {
    if (Serial.available()) {
        String command = Serial.readStringUntil('\n'); // Read input

        if (command.length() > 0) {
            char action = command[0]; // First character (R or S)

            if (action == 'R') {
                Serial.println("Resetting Arduino...");
                delay(100);
                // asm volatile ("jmp 0"); // Software reset

                mode_selectin_state = 0;

                for (int i = 0; i < 10; i++) {
                  for (int j = 0; j < 10; j++) {
                    ledMatrix[i][j] = 0;
      }
    }

            }
            else if (action == 'S' && command.length() == 4) {
                int value = command[1] - '0';  // Convert ASCII to integer
                int row = command[2] - '0';
                int col = command[3] - '0';

                gRow = row; 
                gColumn = col;

                Serial.print("Set Value: ");
                Serial.print(value);
                Serial.print(" at Row: ");
                Serial.print(row);
                Serial.print(" Column: ");
                Serial.println(col);

                mode_selectin_state = 1;
            }
            else if (action == 'W' && command.length() == 101)
            {
              for (int i = 0; i < 100; i++) {
                int row = 0 + i / 10;
                int col = 0 + i % 10;
                ledMatrix[row][col] = command[i + 1] - '0';  // Convert char to int
                
              }
              mode_selectin_state = 2;

              Serial.println("Matrix Updated!");

            }
            else if (action == 'W' && command.length() == 26)
            {
              for (int i = 0; i < 25; i++) {
                int row = 5 + i / 5;
                int col = 5 + i % 5;
                ledMatrix[row][col] = command[i + 1] - '0';  // Convert char to int
                
              }
              mode_selectin_state = 2;

              Serial.println("Matrix Updated!");

            }
            else if (action == 'W' && command.length() == 5)
            {
              for (int i = 0; i < 4; i++) {
                int row = 8 + i / 2;
                int col = 8 + i % 2;
                ledMatrix[row][col] = command[i + 1] - '0';  // Convert char to int
                
              }
              mode_selectin_state = 2;

              Serial.println("Matrix Updated!");

            }
            else {
                Serial.println("Invalid Command!");
            }
        }
    }

    matrix.clear();
    if (mode_selectin_state == 1)
        matrix.set(gRow, gColumn);
    if(mode_selectin_state == 2)
      set_char();
}
