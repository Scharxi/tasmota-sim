import asyncio
import sys
import threading
import os

# Add the app directory to Python path
sys.path.insert(0, "/app")

# Import required modules
from tasmota_sim.device import create_and_start_device
from tasmota_sim.web_server import app
import uvicorn

def run_web_server():
    port = int(os.getenv("PORT", "80"))
    uvicorn.run(app, host="0.0.0.0", port=port)

# Start web server in a separate thread
threading.Thread(target=run_web_server, daemon=True).start()

# Get device configuration from environment variables
device_id = os.getenv("DEVICE_ID", "kitchen_001")
device_name = os.getenv("DEVICE_NAME", "kitchen_001")
ip_address = os.getenv("IP_ADDRESS", "172.25.0.100")

# Start device simulator
asyncio.run(create_and_start_device(device_id, device_name, ip_address)) 