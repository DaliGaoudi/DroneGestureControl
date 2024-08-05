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
DEVICE_MAC_ADDRESS = "cc:b6:3f:23:aa:1a"  # Replace with your device's MAC address
CHARACTERISTIC_UUID = "2A56"  # UUID for the characteristic


def map_value(value, in_min, in_max, out_min, out_max):
    mapped = (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return max(out_min, min(out_max, mapped))

def apply_deadzone(value, deadzone):
    if abs(value) < deadzone:
        return 0
    return value - deadzone if value > 0 else value + deadzone

last_command_time = time.time()

def handle_data(sender: int, data: bytearray):
    global roll_window, pitch_window, yaw_window, last_command_time
    
    data_str = data.decode('utf-8').strip()
    parts = data_str.split()
    if len(parts) != 4:
        logger.warning(f"Received invalid data: {data_str}")
        return
    
    #logger.debug(f"Received raw data: {data_str}")
    
    try:
        roll, pitch, yaw,vertical = map(float, parts)
    except ValueError as e:
        logger.error(f"Error converting data to float: {e}")
        return

    logger.debug(f"Parsed values - Roll: {roll}, Pitch: {pitch}, Yaw: {yaw}, Vertical: {vertical}")

    # Calculate moving averages
    avg_roll = pitch
    avg_pitch = roll
    avg_yaw = yaw

    # Map values to Tello's command range (-100 to 100)
    roll_cmd = int(map_value(avg_roll, -180, 180, -100, 100))
    pitch_cmd = int(map_value(avg_pitch, -90, 90, -100, 100))
    yaw_cmd = int(map_value(avg_yaw, -180, 180, -100, 100))
    vertical_cmd = vertical * 100
    #vertical_cmd = int(map_value(vertical, -4,4,-100,100))
    print(f"Vertical: {vertical_cmd}")
    #logger.debug(f"Mapped commands - Roll: {roll_cmd}, Pitch: {pitch_cmd}, Yaw: {yaw_cmd}, Vertical: {vertical_cmd}")

    # Apply deadzone
    deadzone = 10
    roll_cmd = apply_deadzone(roll_cmd, deadzone)
    pitch_cmd = apply_deadzone(pitch_cmd, deadzone)
    yaw_cmd = apply_deadzone(yaw_cmd, deadzone)
    #vertical_cmd = apply_deadzone(vertical,deadzone)

    logger.debug(f"Final commands after deadzone - Roll: {roll_cmd}, Pitch: {pitch_cmd}, Yaw: {yaw_cmd}, vertical: {vertical_cmd}" )

    # Send control commands to Tello
    try:
        #roll + pitch
        #tello.send_rc_control(roll_cmd * 5, pitch_cmd,vertical_cmd, yaw_cmd * 5)

        #yaw only   
        logger.info(f"Commands sent: Roll: {roll_cmd}, Pitch: {pitch_cmd}, Yaw: {abs(yaw_cmd)}, Vertical: {abs(vertical_cmd)}")
        last_command_time = time.time()
    except Exception as e:
        logger.error(f"Failed to send RC control: {e}")

async def main():
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

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")