import asyncio
from bleak import BleakClient
from djitellopy import Tello
import time
import logging


# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bluetooth setup
DEVICE_MAC_ADDRESS = "7D:77:C9:FE:ED:4E"  # Replace with your device's MAC address
CHARACTERISTIC_UUID = "2A56"  # UUID for the characteristic

flying = False

# Initialize Tello
tello = Tello()
tello.RESPONSE_TIMEOUT = 15  # Increase timeout for commands
tello.connect()
tello.streamon()
print(tello.get_battery())


async def handle_landing(client,characteristic):
    try:
        data = await client.read_gatt_char(characteristic)
        data_str = data.decode().strip()
        logger.debug(f"Received data: {data_str}")
            
        if data_str == "flex":
            logger.info("Landing gesture detected!")
            try:
                tello.land()
                logger.info("Tello is landing")
                await client.write_gatt_char(characteristic, "landing_confirmed".encode())
                logger.info("Sent landing confirmation")
                return True
            except Exception as e:
                logger.error(f"Landing failed: {e}")
                return False
    except Exception as e:
            logger.error(f"Error reading characteristic: {e}")
            return False
    

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



class BleakClientFixed(BleakClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cleanup_done = False

    async def connect(self, **kwargs):
        try:
            await super().connect(**kwargs)
        except Exception as e:
            self._cleanup_done = True
            raise e
        finally:
            self._cleanup_done = True

    def _cleanup(self):
        if self._cleanup_done:
            super()._cleanup()

async def connect_ble():
    for attempt in range(5):
        try:
            client = BleakClientFixed(DEVICE_MAC_ADDRESS)
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

async def main():
    client = await connect_ble()
    if not client:
        return

    try:
        characteristic = client.services.get_characteristic(CHARACTERISTIC_UUID)

        tello.takeoff()
        flying = True


        if flying:
            landing_success = await handle_landing(client, characteristic)
            logger.info(landing_success)
            if not landing_success:
                logger.error("Landing failed, what do i do ?????")

    except Exception as e:
        logger.error(f"An error occurred in the main loop: {e}")
    finally:
        try:
            tello.land()
            logger.info("Tello landing command sent")
            # Wait for the landing to complete
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Landing failed: {e}")
        
        tello.streamoff()
        logger.info("Video stream is off.")
        
        if client.is_connected:
            await client.disconnect()
        logger.info("Disconnected from BLE device")

if __name__ == "__main__":
    asyncio.run(main())