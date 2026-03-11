import RPi.GPIO as GPIO
import time

RELAY_IN1 = 21
RELAY_IN2 = 20

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_IN1, GPIO.OUT)
GPIO.setup(RELAY_IN2, GPIO.OUT)

GPIO.output(RELAY_IN1, GPIO.HIGH)
GPIO.output(RELAY_IN2, GPIO.HIGH)

def start_charging():
    GPIO.output(RELAY_IN1, GPIO.LOW)
    GPIO.output(RELAY_IN2, GPIO.HIGH)
    print("charge start!")

def stop_charging():
    GPIO.output(RELAY_IN1, GPIO.LOW)
    GPIO.output(RELAY_IN2, GPIO.LOW)
    print("charge stop!")
    
def battery_only():
    GPIO.output(RELAY_IN1, GPIO.HIGH)
    GPIO.output(RELAY_IN2, GPIO.LOW)
    print("battery use")
    

def cleanup():
    GPIO.output(RELAY_IN1, GPIO.HIGH)
    GPIO.output(RELAY_IN2, GPIO.HIGH)
    GPIO.cleanup()
    print("relay module cleanup complete")

if __name__ == "__main__":
    try:
        while True:
            cmd = input("charge start(s) / charge stop(e) / battery only(b) / quit(q): ").strip().lower()
            if cmd == "s":
                start_charging()
            elif cmd == "e":
                stop_charging()
            elif cmd == "b":
                battery_only()
            elif cmd == "q":
                cleanup()
                break
            else:
                print("right input (s: start, e: stop, q: quit).")

    except KeyboardInterrupt:
        cleanup()
