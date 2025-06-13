#!/usr/bin/env python3
"""
Main entry point for container deployment.
Starts both the web server and device simulator.
"""

import asyncio
import sys
import threading
import uvicorn
from .device import create_and_start_device
from .web_server import app

def run_web_server():
    """Run the FastAPI web server."""
    uvicorn.run(app, host="0.0.0.0", port=80)

async def main():
    """Main entry point."""
    if len(sys.argv) != 4:
        print("Usage: python -m tasmota_sim.container_main <device_id> <device_name> <ip_address>")
        sys.exit(1)
    
    device_id = sys.argv[1]
    device_name = sys.argv[2]
    ip_address = sys.argv[3]
    
    # Start web server in a separate thread
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    # Start device simulator
    await create_and_start_device(device_id, device_name, ip_address)

if __name__ == "__main__":
    asyncio.run(main()) 