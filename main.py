import os
import gpiozero
from dotenv import load_dotenv
from gpiozero import OutputDevice
from fastapi import FastAPI
import schemas
from time import sleep
from rpi_hardware_pwm import HardwarePWM, HardwarePWMException

import logging

from schemas import SystemVersionResponse

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

def safe_init_pwm(channel, hz) -> HardwarePWM:
    # For this function to work, put this into /boot/firmware/config.txt
    #
    # # Enable both PWM and route them to Port 18 and 13
    # dtoverlay=pwm-2chan,pin=18,func=2,pin2=13,func2=4

    MAX_RETRIES = 10
    attempts = 0

    while True:
        try:
            return HardwarePWM(pwm_channel=channel, hz=hz)
        except PermissionError as e:
            # Weird issue: The first time the intialization is done, we get a permission error.
            # According to an LLM, this could be due to a race condition: The library is writing
            # to `/sys/class/pwm/pwmchip0/export`, which creates folders for controlling the PWM.
            # udev kicks in and changes the permission of the folders, but the library is faster and
            # tries to access the folder before the permissions have been adjusted
            sleep(0.1)
            attempts += 1
            if attempts > MAX_RETRIES:
                raise e


def create_hardware_mock(name):
    """Creates a mock that logs every call made to it."""
    mock = MagicMock()

    # This side_effect logic will trigger whenever the mock is called as a function
    mock.side_effect = lambda *args, **kwargs: logger.info(
        f"Called {name} with args={args}, kwargs={kwargs}"
    )

    # To log method calls (like .on() or .off()), we use a side_effect on the mock's children
    def log_method_call(attr):
        def wrapper(*args, **kwargs):
            logger.info(f"Called {name}.{attr}() with args={args}, kwargs={kwargs}")

        return wrapper

    # We can use a property to intercept method access if we want high detail,
    # but for simple debugging, MagicMock usually suffices.
    mock.configure_mock(**{
        'on.side_effect': log_method_call('on'),
        'off.side_effect': log_method_call('off'),
        'start.side_effect': log_method_call('start'),
        'stop.side_effect': log_method_call('stop'),
        'change_frequency.side_effect': log_method_call('change_frequency'),
        'change_duty_cycle.side_effect': log_method_call('change_duty_cycle'),
    })
    return mock

PIN_MOTOR_ENABLE = int(os.getenv("PIN_MOTOR_ENABLE", 26))
PIN_MOTOR_STEP = int(os.getenv("PIN_MOTOR_STEP", 13))
PIN_MOTOR_DIRECTION = int(os.getenv("PIN_MOTOR_DIRECTION", 6))
SYSTEMD_SERVICE_NAME = os.getenv("SYSTEMD_SERVICE_NAME", "kaleido-control-server.service")
app = FastAPI(title="Kaleido Raspberry Motor Controller")

# configure raspberry pi output pins
try:
    light_gpio = safe_init_pwm(0, 1000)
    motor_gpio = safe_init_pwm(1, 100)

    motor_enable = OutputDevice(PIN_MOTOR_ENABLE, active_high=False)
    direction = OutputDevice(PIN_MOTOR_DIRECTION)
except (gpiozero.BadPinFactory, HardwarePWMException) as e:
    logger.error(e)
    logger.error("Couldn't setup GPIO pins. Assuming you are running on a dev machine")
    from unittest.mock import MagicMock
    light_gpio = create_hardware_mock("Light")
    motor_gpio = create_hardware_mock("Motor")
    motor_enable = create_hardware_mock("MotorEnable")
    direction = create_hardware_mock("Direction")

motor_enable.off()
light_gpio.start(15)
motor_gpio.stop()

@app.post("/motor")
def motor(body: schemas.Motor):
    """
    Change the speed of the motor. The frequency is given in Hz. Positive values turn the motor clockwise,
    negative values counterclockwise. A frequency of 0 stops the motor.
    """
    if body.frequency < 0:
        direction.on()
    else:
        direction.off()

    if body.frequency == 0:
        motor_enable.off()
        motor_gpio.stop()
    else:
        # Duty cycle is irrelevant for motor_gpio speed.
        # The motor driver only counts the edge transitions.
        # Therefore, the duty cycle only requires to be >0 and <100
        motor_gpio.start(50)
        motor_gpio.change_frequency(abs(body.frequency))
        motor_enable.on()

@app.post("/light")
def light(body: schemas.Light):
    """
    Change the brightness of the light. Brightness is given in percent (0-100).
    """
    light_gpio.change_duty_cycle(body.brightness)

@app.post("/system/update", status_code=204)
def system_update():
    """
    Update the system by pulling the latest changes from git.
    Requires hot reloading to be enabled for changes to take effect.
    """
    import subprocess

    logger.info("Starting system update...")
    subprocess.run(["git", "pull"], check=True)
    logger.info("System update completed successfully.")

    return 204

@app.get("/system/version")
def system_version() -> SystemVersionResponse:
    """
    Get the current git commit hash of the running code.
    """
    import subprocess

    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True)
        commit_hash = result.stdout.strip()
        return SystemVersionResponse(commit_hash=commit_hash)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get git commit hash: {e}")
        return 500