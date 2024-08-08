import asyncio
from bleak import BleakClient
from djitellopy import Tello
import time
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bluetooth setup
DEVICE_MAC_ADDRESS = "cc:b6:3f:23:aa:1a"  # Replace with your device's MAC address
CHARACTERISTIC_UUID = "2A56"  # UUID for the characteristic

# Initialize Tello
tello = Tello()
tello.RESPONSE_TIMEOUT = 15  # Increase timeout for commands
tello.connect()
tello.streamon()
print(tello.get_battery())

logger.info("Tello connected and video stream is on.")

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
        tello.send_rc_control(roll_cmd * 5, pitch_cmd, vertical_cmd, yaw_cmd * 5)
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

async def connect_ble():
    for attempt in range(5):
        try:
            client = BleakClient(DEVICE_MAC_ADDRESS)
            await client.connect(timeout=15.0)
            logger.info(f"Connected to BLE device on attempt {attempt + 1}")
            return client
        except Exception as e:
            logger.error(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < 4:
                logger.info("Retrying in 5 seconds...")
                await asyncio.sleep(5)
    
    logger.error("Failed to connect after 5 attempts")
    return None

async def handle_take_off(client, characteristic):
    logger.info("Waiting for take-off gesture...")
    while True:
        try:
            data = await client.read_gatt_char(characteristic)
            data_str = data.decode().strip()
            logger.debug(f"Received data: {data_str}")
            
            if data_str == "flex":
                logger.info("Takeoff gesture detected!")
                try:
                    tello.takeoff()
                    logger.info("Tello took off")
                    await client.write_gatt_char(characteristic, "takeoff_confirmed".encode())
                    logger.info("Sent takeoff confirmation")
                    return True
                except Exception as e:
                    logger.error(f"Takeoff failed: {e}")
                    return False
        except Exception as e:
            logger.error(f"Error reading characteristic: {e}")
            return False
        await asyncio.sleep(0.1)

async def main():
    client = await connect_ble()
    if not client:
        return

    try:
        characteristic = client.services.get_characteristic(CHARACTERISTIC_UUID)
        
        await handle_take_off(client, characteristic)

        #takeoff_success = await handle_take_off(client, characteristic)
        #if not takeoff_success:
         #   logger.error("Takeoff failed. Exiting.")
         #   return

        logger.info("Takeoff successful. Switching to continuous data mode.")
        
        # Main control loop
        keep_alive_task = asyncio.create_task(keep_alive())
        start_time = time.time()
        
        for attempt in range(5):
            while time.time() - start_time < 1000:  # Fly for 200 seconds
                try:
                    await client.start_notify(CHARACTERISTIC_UUID, handle_data)
                    logger.info("Listening for data...")
                    await asyncio.sleep(200)  
                    await client.stop_notify(CHARACTERISTIC_UUID)
                    break
                except Exception as e:
                    logger.error(f"Error reading data: {e}")
                    await asyncio.sleep(0.1)
                    break
        
        keep_alive_task.cancel()

        #while time.time() - start_time < 1000:  # Fly for 200 seconds
         #   try:
          #      data = await client.read_gatt_char(characteristic)
           #     data_str = data.decode().strip()
            #    handle_data(0, data)  
           # except Exception as e:
            #    logger.error(f"Error reading data: {e}")
             #   break
           # await asyncio.sleep(0.1)
        
        #keep_alive_task.cancel()
                
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        try:
            tello.land()
            logger.info("Tello landed")
        except Exception as e:
            logger.error(f"Landing failed: {e}")
        
        tello.streamoff()
        logger.info("Video stream is off.")
        
        await client.disconnect()
        logger.info("Disconnected from BLE device")

if __name__ == "__main__":
    asyncio.run(main())