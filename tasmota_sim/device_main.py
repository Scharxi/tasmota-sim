#!/usr/bin/env python3
"""
Device simulator entry point for container deployment.
"""

import sys
import asyncio
import logging
from .device import create_and_start_device

def main():
    """Main entry point for device simulator in containers."""
    if len(sys.argv) != 4:
        print("Usage: python -m tasmota_sim.device_main <device_id> <device_name> <ip_address>")
        sys.exit(1)
    
    device_id = sys.argv[1]
    device_name = sys.argv[2]
    ip_address = sys.argv[3]
    
    # Setup logging for container
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting device simulator: {device_id} at {ip_address}")
    
    try:
        asyncio.run(create_and_start_device(device_id, device_name, ip_address))
    except KeyboardInterrupt:
        logger.info("Device simulator stopped by user")
    except Exception as e:
        logger.error(f"Device simulator error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 