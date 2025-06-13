"""
Tasmota device simulator with improved async messaging and realistic power consumption.
"""

import asyncio
import logging
import random
import threading
import time
from datetime import datetime
from typing import Optional

from .legacy_models import StatusResponse, TelemetryData, CommandMessage, TasmotaDeviceConfig
from .messaging import AsyncTasmotaMessaging
from .power_profiles import power_profile_manager, DeviceCategory

logger = logging.getLogger(__name__)

class TasmotaDevice:
    """Simulates a Tasmota smart device with async messaging and realistic power consumption."""

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
        
        # Initialize realistic power profile
        self._setup_power_profile()
        
        # Background task handles
        self._status_task: Optional[asyncio.Task] = None
        self._telemetry_task: Optional[asyncio.Task] = None
        self._consumer_task: Optional[asyncio.Task] = None
    
    def _setup_power_profile(self):
        """Setup realistic power profile for the device."""
        # Try to determine device category from device name
        device_name = self.config.device_name.lower()
        category = None
        profile_name = None
        
        # Smart categorization based on device name
        if any(keyword in device_name for keyword in ['lamp', 'light', 'beleuchtung', 'led', 'bulb']):
            category = DeviceCategory.LIGHTING
            if 'led' in device_name or 'smart' in device_name:
                profile_name = "Smart Lampe"
            elif 'halogen' in device_name:
                profile_name = "Halogen Lampe"
            else:
                profile_name = "LED Lampe"
                
        elif any(keyword in device_name for keyword in ['heater', 'heizung', 'radiator', 'heating']):
            category = DeviceCategory.HEATING
            if 'lüfter' in device_name or 'fan' in device_name:
                profile_name = "Heizlüfter"
            elif 'infrarot' in device_name or 'infrared' in device_name:
                profile_name = "Infrarotheizer"
            else:
                profile_name = "Heizkörper"
                
        elif any(keyword in device_name for keyword in ['coffee', 'kaffee', 'toaster', 'kettle', 'wasserkocher']):
            category = DeviceCategory.APPLIANCE_SMALL
            if 'coffee' in device_name or 'kaffee' in device_name:
                profile_name = "Kaffeemaschine"
            elif 'kettle' in device_name or 'wasserkocher' in device_name:
                profile_name = "Wasserkocher"
            else:
                profile_name = "Toaster"
                
        elif any(keyword in device_name for keyword in ['microwave', 'mikrowelle', 'fridge', 'kühlschrank', 'dishwasher', 'geschirrspüler']):
            category = DeviceCategory.APPLIANCE_LARGE
            if 'microwave' in device_name or 'mikrowelle' in device_name:
                profile_name = "Mikrowelle"
            elif 'fridge' in device_name or 'kühlschrank' in device_name:
                profile_name = "Kühlschrank"
            else:
                profile_name = "Geschirrspüler"
                
        elif any(keyword in device_name for keyword in ['tv', 'computer', 'pc', 'monitor', 'router', 'modem']):
            category = DeviceCategory.ELECTRONICS
            if 'tv' in device_name or 'fernseher' in device_name:
                profile_name = "TV LED"
            elif any(keyword in device_name for keyword in ['computer', 'pc', 'desktop']):
                profile_name = "Computer Desktop"
            elif 'router' in device_name or 'modem' in device_name:
                profile_name = "Router/Modem"
                
        elif any(keyword in device_name for keyword in ['washing', 'waschmaschine', 'vacuum', 'staubsauger', 'fan', 'ventilator']):
            category = DeviceCategory.MOTOR
            if 'washing' in device_name or 'waschmaschine' in device_name:
                profile_name = "Waschmaschine"
            elif 'vacuum' in device_name or 'staubsauger' in device_name:
                profile_name = "Staubsauger"
            else:
                profile_name = "Ventilator"
                
        elif any(keyword in device_name for keyword in ['camera', 'kamera', 'hub', 'sensor']):
            category = DeviceCategory.ALWAYS_ON
            if 'camera' in device_name or 'kamera' in device_name:
                profile_name = "Überwachungskamera"
            else:
                profile_name = "Smart Hub"
        
        # Assign power profile
        profile = power_profile_manager.assign_profile_to_device(
            self.config.device_id, 
            profile_name=profile_name, 
            category=category
        )
        
        # Set initial power state based on profile
        initial_power = power_profile_manager.get_device_power_consumption(self.config.device_id)
        self.config.energy_consumption = initial_power
        
        logger.info(f"Device {self.config.device_id} assigned profile: {profile.name} ({profile.category.value})")
        logger.info(f"Initial power consumption: {initial_power:.1f}W")

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
        self._status_task = asyncio.create_task(self._status_publisher())
        self._telemetry_task = asyncio.create_task(self._telemetry_publisher())
        
        logger.info(f"Device {self.config.device_id} started successfully")
        return True

    async def _start_consuming(self):
        """Start consuming messages from RabbitMQ."""
        try:
            logger.info(f"Device {self.config.device_id} starting message consumer...")
            await self.messaging.start_consuming(self._handle_command)
            logger.info(f"Device {self.config.device_id} consumer task completed")
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
        """Update total energy consumption using realistic power profiles."""
        # Get current power consumption from power profile manager
        current_power = power_profile_manager.get_device_power_consumption(self.config.device_id)
        self.config.energy_consumption = current_power
        
        # Get total energy from power profile manager
        total_energy_from_profile = power_profile_manager.get_device_total_energy(self.config.device_id)
        
        # If profile manager has tracked energy, use it; otherwise keep existing total
        if total_energy_from_profile > 0:
            self.config.total_energy = total_energy_from_profile
            self._energy_accumulator = total_energy_from_profile

    async def _handle_command(self, command: CommandMessage):
        """Handle incoming commands."""
        try:
            logger.info(f"Device {self.config.device_id} received command: {command.command}")
            print(f"PRINT: Processing command in _handle_command: {command.command}", flush=True)
            logger.info(f"Processing command in _handle_command: {command.command}")
            print(f"PRINT: Command object: {command}", flush=True)
            logger.info(f"Command object: {command}")
        except Exception as e:
            logger.error(f"Error in _handle_command start: {e}")
            print(f"PRINT ERROR: {e}", flush=True)
            return
        
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
                logger.info(f"Device {self.config.device_id} attempting to publish status...")
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
        """Set device power state and update realistic energy consumption."""
        self.config.power_state = state
        
        # Update power state in profile manager and get realistic consumption
        new_consumption = power_profile_manager.set_device_power_state(self.config.device_id, state)
        self.config.energy_consumption = new_consumption
        
        # Get device info for logging
        device_info = power_profile_manager.get_device_info(self.config.device_id)
        profile_name = device_info.get('profile_name', 'Unknown')
        
        logger.info(f"Device {self.config.device_id} ({profile_name}) power state changed to {state}")
        logger.info(f"Realistic power consumption: {new_consumption:.1f}W")

    async def stop(self):
        """Stop the device simulator."""
        logger.info(f"Stopping device {self.config.device_id}")
        self.is_running = False
        
        # Cancel background tasks
        for task in [self._status_task, self._telemetry_task]:
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
    """Generate a realistic device configuration with smart power profiling."""
    import os
    
    # Create a temporary power profile manager to get initial values
    temp_profile_manager = power_profile_manager
    
    # Pre-assign a profile to get realistic initial values
    profile = temp_profile_manager.assign_profile_to_device(device_id, category=None)
    
    # Get initial power consumption
    initial_power = temp_profile_manager.get_device_power_consumption(device_id)
    initial_energy = temp_profile_manager.get_device_total_energy(device_id)
    
    # If no energy tracked yet, use a random historical value
    if initial_energy == 0:
        initial_energy = random.uniform(5.0, 500.0)  # Realistic historical consumption
    
    return TasmotaDeviceConfig(
        device_id=device_id,
        device_name=device_name,
        ip_address=ip_address,
        power_state=random.choice([True, False]),
        energy_consumption=initial_power,
        total_energy=initial_energy,
        firmware_version="12.5.0",
        rabbitmq_host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
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