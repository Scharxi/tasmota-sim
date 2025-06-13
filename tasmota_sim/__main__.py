#!/usr/bin/env python3
"""
Entry point for the Tasmota simulator package.
"""

import sys
import asyncio
from .cli import cli
from .device import create_and_start_device

def main():
    """Main entry point for CLI."""
    cli()

if __name__ == "__main__":
    # Check if we're being called as a device simulator
    if len(sys.argv) >= 4 and sys.argv[1] != '--help' and not sys.argv[1].startswith('-'):
        # Device mode: python -m tasmota_sim.device device_id device_name ip_address
        device_id = sys.argv[1]
        device_name = sys.argv[2]
        ip_address = sys.argv[3]
        
        print(f"Starting device simulator: {device_id}")
        asyncio.run(create_and_start_device(device_id, device_name, ip_address))
    else:
        # CLI mode
        main() 