import os
import gpiozero
from dotenv import load_dotenv
from gpiozero import LED, OutputDevice
from fastapi import FastAPI
import schemas
import logging

load_dotenv()


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

MAX_SPEED = int(os.getenv("MAX_SPEED", 10000))
app = FastAPI()

class PinMock:
    def __init__(self, pin_number: int):
        self.pin = pin_number

    def on(self):
        logger.info(f"Pin {self.pin} turned on")

    def off(self):
        logger.info(f"Pin {self.pin} turned off")

    def blink(self, on_time: float, off_time: float):
        logger.info(f"Pin {self.pin} blink {on_time} off {off_time}")


# configure raspberry pi output pins
try:
    motor = LED(4)
    motor_enable = OutputDevice(27)
    direction = OutputDevice(17)
except gpiozero.BadPinFactory:
    logger.error("Couldn't setup GPIO pins. Assuming you are running on a dev machine")
    motor = PinMock(4)
    motor_enable = PinMock(27)
    direction = PinMock(17)

motor.blink(on_time=0.0001, off_time=0.0001)
@app.post("/on")
def motor_on():
    # Inverted pin
    motor_enable.off()

@app.post("/off")
def motor_off():
    # Inverted pin
    motor_enable.on()

@app.post("/speed")
def motor_direction(body: schemas.MotorSpeed):
    if body.direction == schemas.Direction.CLOCKWISE:
        direction.on()
    else:
        direction.off()

    on_off_time = 1 / (MAX_SPEED * body.speed)
    motor.blink(on_time=on_off_time, off_time=on_off_time)