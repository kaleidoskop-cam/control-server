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
PIN_MOTOR_ENABLE = int(os.getenv("PIN_MOTOR_ENABLE", 26))
PIN_MOTOR_STEP = int(os.getenv("PIN_MOTOR_STEP", 13))
PIN_MOTOR_DIRECTION = int(os.getenv("PIN_MOTOR_DIRECTION", 6))
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
    motor = LED(PIN_MOTOR_STEP)
    motor_enable = OutputDevice(PIN_MOTOR_ENABLE, active_high=False)
    direction = OutputDevice(PIN_MOTOR_DIRECTION)
except gpiozero.BadPinFactory:
    logger.error("Couldn't setup GPIO pins. Assuming you are running on a dev machine")
    motor = PinMock(PIN_MOTOR_STEP)
    motor_enable = PinMock(PIN_MOTOR_ENABLE)
    direction = PinMock(PIN_MOTOR_DIRECTION)

motor_enable.off()

@app.post("/on")
def motor_on():
    motor_enable.on()

@app.post("/off")
def motor_off():
    motor_enable.off()

@app.post("/speed")
def motor_direction(body: schemas.MotorSpeed):
    if body.direction == schemas.Direction.COUNTERCLOCKWISE:
        direction.on()
    else:
        direction.off()

    if body.speed == 0:
        motor_enable.off()
    else:
        motor_enable.on()
        on_off_time = 1 / (MAX_SPEED * body.speed)
        motor.blink(on_time=on_off_time, off_time=on_off_time)