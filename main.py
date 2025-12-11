from typing import Union

from gpiozero import LED, OutputDevice
from fastapi import FastAPI

app = FastAPI()

# configure motor speed
motor = LED(4)
motor.blink(on_time=0.0001, off_time=0.0001)

motor_enable = OutputDevice(27)

@app.get("/on")
def motor_on():
    # Inverted pin
    motor_enable.off()

@app.get("/off")
def motor_off():
    # Inverted pin
    motor_enable.on()