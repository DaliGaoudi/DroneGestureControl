import asyncio
from bleak import BleakScanner

async def scan_ble_devices():
    print("Scanning for Bluetooth devices...")
    devices = await BleakScanner.discover()
    if devices:
        print("Found devices:")
        for device in devices:
            print(f"Device Name: {device.name}, MAC Address: {device.address}")
    else:
        print("No Bluetooth devices found.")

if __name__ == "__main__":
    asyncio.run(scan_ble_devices())
    

#2DE737D7-89B3-F883-652A-F8F42578F76C
