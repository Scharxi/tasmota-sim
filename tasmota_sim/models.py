"""
Pydantic models for Tasmota device simulation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


class DeviceState(str, Enum):
    """Device power states."""
    ON = "ON"
    OFF = "OFF"


class TasmotaDeviceConfig(BaseModel):
    """Configuration for a Tasmota device."""
    device_id: str = Field(..., description="Unique device identifier")
    device_name: str = Field(..., description="Human-readable device name")
    ip_address: str = Field(..., description="IP address of the device")
    firmware_version: str = Field(default="12.5.0", description="Tasmota firmware version")
    power_state: bool = Field(default=False, description="Current power state")
    energy_consumption: float = Field(default=0.0, description="Current power consumption in watts")
    total_energy: float = Field(default=0.0, description="Total energy consumed in kWh")
    rabbitmq_host: str = Field(default="localhost", description="RabbitMQ host")
    rabbitmq_user: str = Field(default="admin", description="RabbitMQ user")
    rabbitmq_pass: str = Field(default="admin123", description="RabbitMQ password")


class TasmotaMessage(BaseModel):
    """Base message structure for Tasmota communication."""
    device_id: str = Field(..., description="Device identifier")
    command: str = Field(..., description="Command type")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Command payload")
    timestamp: Optional[str] = Field(default=None, description="Message timestamp")


class CommandMessage(BaseModel):
    """Command message structure for device communication."""
    device_id: str = Field(..., description="Device identifier")
    command: str = Field(..., description="Command type")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Command payload")
    timestamp: str = Field(..., description="Message timestamp")


class PowerCommand(BaseModel):
    """Power control command."""
    action: DeviceState = Field(..., description="Power action to perform")


class StatusResponse(BaseModel):
    """Device status response."""
    device_id: str
    device_name: str
    ip_address: str
    power_state: bool
    energy_consumption: float
    total_energy: float
    firmware_version: str
    uptime: int
    wifi_signal: int = Field(default=-45, description="WiFi signal strength in dBm")


class TelemetryData(BaseModel):
    """Telemetry data from device."""
    device_id: str
    power_state: bool
    energy: Dict[str, float] = Field(
        default_factory=lambda: {
            "power": 0.0,
            "apparent_power": 0.0,
            "reactive_power": 0.0,
            "factor": 1.0,
            "voltage": 230.0,
            "current": 0.0,
            "total": 0.0,
            "today": 0.0,
            "yesterday": 0.0
        }
    )
    timestamp: str 