import asyncio
from bleak import BleakClient
from djitellopy import Tello
import time
from collections import deque
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bluetooth setup
DEVICE_MAC_ADDRESS = "2DE737D7-89B3-F883-652A-F8F42578F76C"  # Replace with your device's MAC address
CHARACTERISTIC_UUID = "2A56"  # UUID for the characteristic

# Initialize Tello
tello = Tello()
tello.RESPONSE_TIMEOUT = 15  # Increase timeout for commands
tello.connect()
tello.streamon()
logger.info("BATTERY LEVEL HERE !!!")
print(tello.get_battery())

logger.info("Tello connected and video stream is on.")

# Moving average filter setup
window_size = 5
roll_window = deque(maxlen=window_size)
pitch_window = deque(maxlen=window_size)
yaw_window = deque(maxlen=window_size)

def map_value(value, in_min, in_max, out_min, out_max):
    mapped = (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return max(out_min, min(out_max, mapped))

def apply_deadzone(value, deadzone):
    if abs(value) < deadzone:
        return 0
    return value - deadzone if value > 0 else value + deadzone

last_command_time = time.time()


def handle_data(sender: int, data: bytearray):
    global last_command_time
    
    data_str = data.decode('utf-8').strip()
    parts = data_str.split()
    if len(parts) != 4:
        logger.warning(f"Received invalid data: {data_str}")
        return
    
    try:
        roll, pitch, yaw, vertical = map(float, parts)
    except ValueError as e:
        logger.error(f"Error converting data to float: {e}")
        return

    logger.debug(f"Parsed values - Roll: {roll}, Pitch: {pitch}, Yaw: {yaw}, Vertical: {vertical}")

    # Map values to Tello's command range (-100 to 100)
    roll_cmd = int(map_value(roll, -180, 180, -100, 100))
    pitch_cmd = int(map_value(pitch, -90, 90, -100, 100))
    yaw_cmd = int(map_value(yaw, -180, 180, -100, 100))
    vertical_cmd = int(map_value(vertical, -1, 1, -100, 100))

    # Apply deadzone
    deadzone = 10
    roll_cmd = apply_deadzone(roll_cmd, deadzone)
    pitch_cmd = apply_deadzone(pitch_cmd, deadzone)
    yaw_cmd = apply_deadzone(yaw_cmd, deadzone)

    logger.debug(f"Final commands after deadzone - Roll: {roll_cmd}, Pitch: {pitch_cmd}, Yaw: {yaw_cmd}, Vertical: {vertical_cmd}")

    # Send control commands to Tello
    try:
        tello.send_rc_control(roll_cmd , pitch_cmd, int(vertical_cmd / 2), yaw_cmd)
        last_command_time = time.time()
    except Exception as e:
        logger.error(f"Failed to send RC control: {e}")

async def keep_alive():
    while True:
        if time.time() - last_command_time > 5:
            try:
                tello.send_rc_control(0, 0, 0, 0)
                logger.debug("Sent keep-alive signal")
            except Exception as e:
                logger.error(f"Failed to send keep-alive signal: {e}")
        await asyncio.sleep(1)

async def main():
    try:
        tello.takeoff()
        logger.info("Tello took off")
    except Exception as e:
        logger.error(f"Takeoff failed: {e}")
        return

    await asyncio.sleep(5)  # Wait for 5 seconds after takeoff
    
    keep_alive_task = asyncio.create_task(keep_alive())

    for attempt in range(5):  # Retry up to 5 times
        try:
            async with BleakClient(DEVICE_MAC_ADDRESS, timeout=30.0) as client:
                await client.start_notify(CHARACTERISTIC_UUID, handle_data)
                logger.info("Listening for data...")
                await asyncio.sleep(200)  # Listen for data for 120 seconds
                await client.stop_notify(CHARACTERISTIC_UUID)
                break
        except Exception as e:
            logger.error(f"BLE connection attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(5)  # Wait before retrying

    keep_alive_task.cancel()
    
    try:
        tello.land()
        logger.info("Tello landed")
    except Exception as e:
        logger.error(f"Landing failed: {e}")

    tello.streamoff()
    logger.info("Video stream is off.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
        tello.land()
        tello.streamoff()
        logger.info("Tello landed and video stream is off.")