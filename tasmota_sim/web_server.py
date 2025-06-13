from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional
import secrets
import socket
import os

app = FastAPI(title="Tasmota Simulator")
security = HTTPBasic()

# Default credentials (should be configurable in production)
DEFAULT_USERNAME = os.getenv("DEFAULT_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "test1234!")

# Get container information
CONTAINER_IP = os.getenv("CONTAINER_IP", socket.gethostbyname(socket.gethostname()))
DEVICE_NAME = os.getenv("DEVICE_NAME", "tasmota-sim")

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """Verify basic auth credentials."""
    is_username_correct = secrets.compare_digest(credentials.username, DEFAULT_USERNAME)
    is_password_correct = secrets.compare_digest(credentials.password, DEFAULT_PASSWORD)
    return is_username_correct and is_password_correct

class PowerState(BaseModel):
    """Model for power state."""
    POWER: str

class DeviceInfo(BaseModel):
    """Model for device information."""
    Device: str
    Version: str
    IPAddress: str
    Status: str

# Global state (in a real application, this would be persisted)
power_state = PowerState(POWER="OFF")

@app.get("/cm")
async def command(
    cmnd: str = Query(..., description="Command to execute"),
    user: Optional[str] = None,
    password: Optional[str] = None,
    _: bool = Depends(verify_credentials)
):
    """
    Handle Tasmota-like commands.
    Example: /cm?cmnd=Power%20TOGGLE
    """
    if not cmnd:
        raise HTTPException(status_code=400, detail="Command is required")

    # Parse command and parameter
    parts = cmnd.split()
    command = parts[0].upper()
    parameter = parts[1].upper() if len(parts) > 1 else None

    # Handle Power commands
    if command == "POWER":
        if parameter == "TOGGLE":
            power_state.POWER = "OFF" if power_state.POWER == "ON" else "ON"
        elif parameter in ["ON", "1", "TRUE"]:
            power_state.POWER = "ON"
        elif parameter in ["OFF", "0", "FALSE"]:
            power_state.POWER = "OFF"
        else:
            raise HTTPException(status_code=400, detail=f"Invalid power parameter: {parameter}")
        
        return {"POWER": power_state.POWER}
    
    # Add more command handlers here as needed
    
    raise HTTPException(status_code=400, detail=f"Unknown command: {command}")

@app.get("/")
async def root():
    """Root endpoint that returns basic device info."""
    return DeviceInfo(
        Device=DEVICE_NAME,
        Version="1.0.0",
        IPAddress=CONTAINER_IP,
        Status="Online"
    ).model_dump() 