"""
Tasmota device simulator with improved async messaging.
"""

import asyncio
import logging
import random
import threading
import time
from datetime import datetime
from typing import Optional

from .models import TasmotaDeviceConfig, StatusResponse, TelemetryData, CommandMessage
from .messaging import AsyncTasmotaMessaging

logger = logging.getLogger(__name__)

class TasmotaDevice:
    """Simulates a Tasmota smart device with async messaging."""

    def __init__(self, config: TasmotaDeviceConfig):
        self.config = config
        self.messaging = AsyncTasmotaMessaging(
            host=config.rabbitmq_host,
            user=config.rabbitmq_user,
            password=config.rabbitmq_pass
        )
        
        self.start_time = datetime.now()
        self.last_telemetry = datetime.now()
        self.is_running = False
        self._energy_accumulator = 0.0
        
        # Background task handles
        self._status_task: Optional[asyncio.Task] = None
        self._telemetry_task: Optional[asyncio.Task] = None
        self._consumer_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the device simulator."""
        logger.info(f"Starting device {self.config.device_id}")
        
        # Connect to RabbitMQ
        if not await self.messaging.connect():
            logger.error(f"Failed to connect device {self.config.device_id} to RabbitMQ")
            return False
        
        # Setup device queue for commands
        if not await self.messaging.setup_device_queue(self.config.device_id, self._handle_command):
            logger.error(f"Failed to setup command queue for device {self.config.device_id}")
            return False
        
        self.is_running = True
        
        # Start background tasks
        self._consumer_task = asyncio.create_task(self._start_consuming())
        self._status_task = asyncio.create_task(self._status_publisher())
        self._telemetry_task = asyncio.create_task(self._telemetry_publisher())
        
        logger.info(f"Device {self.config.device_id} started successfully")
        return True

    async def _start_consuming(self):
        """Start consuming messages from RabbitMQ."""
        try:
            await self.messaging.start_consuming(self._handle_command)
        except Exception as e:
            logger.error(f"Error in message consumer for device {self.config.device_id}: {e}")

    async def _status_publisher(self):
        """Background loop for periodic status updates."""
        while self.is_running:
            try:
                await self._publish_status()
                await asyncio.sleep(30)  # Publish status every 30 seconds
            except Exception as e:
                logger.error(f"Error in status publisher for device {self.config.device_id}: {e}")
                await asyncio.sleep(30)

    async def _telemetry_publisher(self):
        """Background loop for periodic telemetry updates."""
        while self.is_running:
            try:
                await self._publish_telemetry()
                await asyncio.sleep(10)  # Publish telemetry every 10 seconds
            except Exception as e:
                logger.error(f"Error in telemetry publisher for device {self.config.device_id}: {e}")
                await asyncio.sleep(10)

    async def _publish_status(self):
        """Publish current device status."""
        uptime = int((datetime.now() - self.start_time).total_seconds())
        
        status = StatusResponse(
            device_id=self.config.device_id,
            device_name=self.config.device_name,
            ip_address=self.config.ip_address,
            power_state=self.config.power_state,
            energy_consumption=self.config.energy_consumption,
            total_energy=self.config.total_energy,
            firmware_version=self.config.firmware_version,
            uptime=uptime,
            wifi_signal=random.randint(-60, -30)  # Simulate WiFi signal variation
        )
        
        success = await self.messaging.publish_status(self.config.device_id, status)
        if not success:
            logger.warning(f"Failed to publish status for device {self.config.device_id}")

    async def _publish_telemetry(self):
        """Publish telemetry data."""
        # Update total energy consumption
        self._update_energy()
        
        # Calculate current based on power and voltage
        voltage = 230.0 + random.uniform(-5.0, 5.0)  # Simulate voltage variation
        current = self.config.energy_consumption / voltage if voltage > 0 else 0.0
        
        # Calculate daily energy (simplified)
        now = datetime.now()
        today_energy = self._energy_accumulator if now.date() == self.start_time.date() else 0.0
        
        telemetry = TelemetryData(
            device_id=self.config.device_id,
            power_state=self.config.power_state,
            energy={
                "power": round(self.config.energy_consumption, 2),
                "apparent_power": round(self.config.energy_consumption * 1.05, 2),  # Add some reactive power
                "reactive_power": round(self.config.energy_consumption * 0.1, 2),
                "factor": round(random.uniform(0.85, 0.95), 2),  # Power factor
                "voltage": round(voltage, 1),
                "current": round(current, 3),
                "total": round(self.config.total_energy, 3),
                "today": round(today_energy, 3),
                "yesterday": round(random.uniform(0.1, 2.0), 3)  # Mock yesterday's consumption
            },
            timestamp=datetime.now().isoformat()
        )
        
        success = await self.messaging.publish_telemetry(self.config.device_id, telemetry)
        if success:
            self.last_telemetry = datetime.now()
        else:
            logger.warning(f"Failed to publish telemetry for device {self.config.device_id}")

    def _update_energy(self):
        """Update total energy consumption based on current power state."""
        if self.config.power_state:
            # Calculate energy consumed since last update
            time_diff = (datetime.now() - self.last_telemetry).total_seconds() / 3600  # hours
            energy_consumed = self.config.energy_consumption * time_diff / 1000  # kWh
            
            self.config.total_energy += energy_consumed
            self._energy_accumulator += energy_consumed

    async def _handle_command(self, command: CommandMessage):
        """Handle incoming commands."""
        logger.info(f"Device {self.config.device_id} received command: {command.command}")
        
        try:
            if command.command == "power_on":
                self._set_power_state(True)
                # Send immediate status response
                await self._publish_status()
            elif command.command == "power_off":
                self._set_power_state(False)
                # Send immediate status response
                await self._publish_status()
            elif command.command == "status":
                # Send immediate status response
                await self._publish_status()
                logger.info(f"Device {self.config.device_id} sent status response")
            elif command.command == "energy":
                # Send immediate telemetry response
                await self._publish_telemetry()
                logger.info(f"Device {self.config.device_id} sent energy response")
            else:
                logger.warning(f"Unknown command: {command.command}")
                
        except Exception as e:
            logger.error(f"Error handling command {command.command}: {e}")

    def _set_power_state(self, state: bool):
        """Set device power state and update energy consumption."""
        self.config.power_state = state
        
        if state:
            # Random consumption between 15-85W when on
            self.config.energy_consumption = random.uniform(15.0, 85.0)
        else:
            # Standby consumption ~0.5W
            self.config.energy_consumption = random.uniform(0.3, 0.8)
        
        logger.info(f"Device {self.config.device_id} power state changed to {state}, consumption: {self.config.energy_consumption:.1f}W")

    async def stop(self):
        """Stop the device simulator."""
        logger.info(f"Stopping device {self.config.device_id}")
        self.is_running = False
        
        # Cancel background tasks
        for task in [self._status_task, self._telemetry_task, self._consumer_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close messaging connection
        await self.messaging.close()
        logger.info(f"Device {self.config.device_id} stopped")

def generate_device_config(device_id: str, device_name: str, ip_address: str) -> TasmotaDeviceConfig:
    """Generate a realistic device configuration."""
    import os
    
    return TasmotaDeviceConfig(
        device_id=device_id,
        device_name=device_name,
        ip_address=ip_address,
        power_state=random.choice([True, False]),
        energy_consumption=random.uniform(15.0, 85.0) if random.choice([True, False]) else random.uniform(0.3, 0.8),
        total_energy=random.uniform(10.0, 1000.0),  # Previous total consumption
        firmware_version="12.5.0",
        rabbitmq_host=os.getenv("RABBITMQ_HOST", "localhost"),
        rabbitmq_user=os.getenv("RABBITMQ_USER", "admin"),
        rabbitmq_pass=os.getenv("RABBITMQ_PASS", "admin123")
    )

async def create_and_start_device(device_id: str, device_name: str, ip_address: str):
    """Create and start a device simulator - main entry point for containers."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Generate device configuration
    config = generate_device_config(device_id, device_name, ip_address)
    
    # Create and start device
    device = TasmotaDevice(config)
    
    try:
        if await device.start():
            logger.info(f"Device {device_id} running. Press Ctrl+C to stop.")
            
            # Keep running until interrupted
            while device.is_running:
                await asyncio.sleep(1)
                
        else:
            logger.error(f"Failed to start device {device_id}")
            
    except KeyboardInterrupt:
        logger.info(f"Received interrupt signal for device {device_id}")
    except Exception as e:
        logger.error(f"Error running device {device_id}: {e}")
    finally:
        await device.stop() 