#!/usr/bin/env python3
"""
Data models for Tasmota Device Simulator.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Device:
    """Represents a Tasmota device."""
    id: str
    name: str
    room: Optional[str] = None
    device_type: str = "switch"
    ip_address: Optional[str] = None
    port: int = 80
    prefix: str = "kitchen"
    status: str = "offline"
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    last_seen: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


@dataclass 
class Container:
    """Represents a Docker container mapping for a device."""
    device_id: str
    container_name: str
    docker_service_name: str
    host_port: int
    device_name: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


@dataclass
class DeviceStatus:
    """Represents device status/telemetry data."""
    device_id: str
    power_state: bool
    energy_consumption: Optional[float] = None
    total_energy: Optional[float] = None
    voltage: Optional[float] = None
    current: Optional[float] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class DockerComposeService:
    """Represents a service definition for docker-compose."""
    name: str
    device_id: str
    ip_address: str
    host_port: int
    environment: Dict[str, str] = field(default_factory=dict)
    
    def to_compose_dict(self) -> Dict[str, Any]:
        """Convert to docker-compose service definition."""
        return {
            "image": "tasmota-sim",
            "container_name": f"tasmota-device-{self.name}",
            "command": "python3 /app/run_device.py",
            "environment": {
                "DEVICE_ID": self.device_id,
                "DEVICE_NAME": self.name,
                "DEVICE_IP": self.ip_address,
                "AMQP_URL": "amqp://admin:admin123@rabbitmq:5672/",
                **self.environment
            },
            "ports": [
                f"{self.ip_address}:80:80",
                f"127.0.0.1:{self.host_port}:80"
            ],
            "networks": {
                "tasmota_net": {
                    "ipv4_address": self.ip_address
                }
            },
            "depends_on": ["rabbitmq"],
            "restart": "unless-stopped"
        } 