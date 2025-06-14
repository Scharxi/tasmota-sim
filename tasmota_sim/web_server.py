from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any
import secrets
import socket
import os
import json
from datetime import datetime, timezone
from .power_profiles import power_profile_manager

app = FastAPI(title="Tasmota Simulator")
security = HTTPBasic()

# Default credentials (should be configurable in production)
DEFAULT_USERNAME = os.getenv("DEFAULT_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "test1234!")

# Get container information
CONTAINER_IP = os.getenv("CONTAINER_IP", socket.gethostbyname(socket.gethostname()))
DEVICE_NAME = os.getenv("DEVICE_NAME", "tasmota-sim")
DEVICE_ID = os.getenv("DEVICE_ID", "unknown_device")
DEVICE_IP = os.getenv("DEVICE_IP", CONTAINER_IP)

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
    device_id: str
    device_name: str
    power_state: bool
    energy_consumption: float
    total_energy: float
    profile_name: str
    profile_category: str
    voltage: float
    current: float

class EnergyData(BaseModel):
    """Model for energy data."""
    power: float
    apparent_power: float
    reactive_power: float
    factor: float
    voltage: float
    current: float
    total: float
    today: float
    yesterday: float

# Global state (in a real application, this would be persisted)
power_state = PowerState(POWER="OFF")
start_time = datetime.now(timezone.utc)

def get_realistic_device_data():
    """Get realistic device data from power profile manager."""
    try:
        device_info = power_profile_manager.get_device_info(DEVICE_ID)
        current_power = power_profile_manager.get_device_power_consumption(DEVICE_ID)
        total_energy = power_profile_manager.get_device_total_energy(DEVICE_ID)
        
        # Calculate voltage and current
        voltage = 230.0 + (hash(DEVICE_ID) % 10 - 5)  # 225-235V variation
        current = current_power / voltage if voltage > 0 else 0.0
        
        return {
            "power_state": device_info['power_state'],
            "energy_consumption": current_power,
            "total_energy": total_energy,
            "profile_name": device_info['profile_name'],
            "profile_category": device_info['profile_category'],
            "voltage": voltage,
            "current": current
        }
    except Exception:
        # Fallback if power profile manager fails
        return {
            "power_state": power_state.POWER == "ON",
            "energy_consumption": 15.0,
            "total_energy": 10.0,
            "profile_name": "Generic Device",
            "profile_category": "unknown",
            "voltage": 230.0,
            "current": 0.065
        }

def get_uptime():
    """Get uptime in seconds."""
    return int((datetime.now(timezone.utc) - start_time).total_seconds())

def get_status_response(level: int = 0) -> Dict[str, Any]:
    """Generate Tasmota-like status response based on level."""
    realistic_data = get_realistic_device_data()
    uptime = get_uptime()
    now = datetime.now(timezone.utc)
    
    if level == 1:  # Device parameters
        return {
            "Status": {
                "Module": 1,
                "DeviceName": DEVICE_NAME,
                "FriendlyName": [DEVICE_NAME],
                "Topic": DEVICE_ID,
                "ButtonTopic": "0",
                "Power": 1 if realistic_data["power_state"] else 0,
                "PowerOnState": 3,
                "LedState": 1,
                "LedMask": "FFFF",
                "SaveData": 1,
                "SaveState": 1,
                "SwitchTopic": "0",
                "SwitchMode": [0, 0, 0, 0, 0, 0, 0, 0],
                "ButtonRetain": 0,
                "SwitchRetain": 0,
                "SensorRetain": 0,
                "PowerRetain": 0,
                "InfoRetain": 0,
                "StateRetain": 0
            }
        }
    
    elif level == 2:  # Firmware information
        return {
            "StatusFWR": {
                "Version": "12.5.0(tasmota)",
                "BuildDateTime": "2023-12-01T10:00:00",
                "Boot": 31,
                "Core": "2_7_4",
                "SDK": "2.2.2-dev(38a443e)",
                "CpuFrequency": 80,
                "Hardware": "ESP8266EX",
                "CR": "394/699"
            }
        }
    
    elif level == 3:  # Logging and telemetry
        return {
            "StatusLOG": {
                "SerialLog": 2,
                "WebLog": 2,
                "MqttLog": 0,
                "SysLog": 0,
                "LogHost": "",
                "LogPort": 514,
                "SSId": ["WiFi-Network", ""],
                "TelePeriod": 300,
                "Resolution": "558180C0",
                "SetOption": ["00008009", "2805C80001000600003C5A0A192800000000", "00000080", "00006000", "00004000"]
            }
        }
    
    elif level == 4:  # Memory information
        return {
            "StatusMEM": {
                "ProgramSize": 595,
                "Free": 404,
                "Heap": 25,
                "ProgramFlashSize": 1024,
                "FlashSize": 1024,
                "FlashChipId": "1640E0",
                "FlashFrequency": 40,
                "FlashMode": 3,
                "Features": ["00000809", "8F9AC787", "04368001", "000000CF", "010013C0", "C000F981", "00004004", "00001000"],
                "Drivers": "1,2,3,4,5,6,7,8,9,10,12,16,18,19,20,21,22,24,26,27,29,30,35,37,45",
                "Sensors": "1,2,3,4,5,6"
            }
        }
    
    elif level == 5:  # Network information
        return {
            "StatusNET": {
                "Hostname": DEVICE_ID,
                "IPAddress": DEVICE_IP,
                "Gateway": "172.25.0.1",
                "Subnetmask": "255.255.0.0",
                "DNSServer1": "8.8.8.8",
                "DNSServer2": "8.8.4.4",
                "Mac": f"AA:BB:CC:DD:EE:{hash(DEVICE_ID) % 256:02X}",
                "Webserver": 2,
                "HTTP_API": 1,
                "WifiConfig": 4,
                "WifiPower": 17.0
            }
        }
    
    elif level == 6:  # MQTT information
        return {
            "StatusMQT": {
                "MqttHost": "172.25.0.10",
                "MqttPort": 5672,
                "MqttClientMask": DEVICE_ID,
                "MqttClient": DEVICE_ID,
                "MqttUser": "admin",
                "MqttCount": 1,
                "MAX_PACKET_SIZE": 1200,
                "KEEPALIVE": 30,
                "SOCKET_TIMEOUT": 4
            }
        }
    
    elif level == 7:  # Time information
        return {
            "StatusTIM": {
                "UTC": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "Local": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "StartDST": "2024-03-31T02:00:00",
                "EndDST": "2024-10-27T03:00:00",
                "Timezone": "+01:00",
                "Sunrise": "06:30",
                "Sunset": "18:45"
            }
        }
    
    elif level == 9:  # Power thresholds (for power monitoring modules)
        return {
            "StatusPTH": {
                "PowerLow": 0,
                "PowerHigh": 0,
                "VoltageLow": 0,
                "VoltageHigh": 0,
                "CurrentLow": 0,
                "CurrentHigh": 0
            }
        }
    
    elif level == 10:  # Sensor information
        return {
            "StatusSNS": {
                "Time": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "ENERGY": {
                    "TotalStartTime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "Total": realistic_data["total_energy"],
                    "Yesterday": realistic_data["total_energy"] * 0.08,
                    "Today": realistic_data["total_energy"] * 0.1,
                    "Period": int(realistic_data["energy_consumption"] * 5),  # 5-minute period
                    "Power": realistic_data["energy_consumption"],
                    "ApparentPower": realistic_data["energy_consumption"] * 1.05,
                    "ReactivePower": realistic_data["energy_consumption"] * 0.1,
                    "Factor": 0.95,
                    "Voltage": realistic_data["voltage"],
                    "Current": realistic_data["current"]
                }
            }
        }
    
    elif level == 11:  # TelePeriod state message
        return {
            "StatusSTS": {
                "Time": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "Uptime": f"0T{uptime//3600:02d}:{(uptime%3600)//60:02d}:{uptime%60:02d}",
                "UptimeSec": uptime,
                "Heap": 25,
                "SleepMode": "Dynamic",
                "Sleep": 50,
                "LoadAvg": 19,
                "MqttCount": 1,
                "POWER": "ON" if realistic_data["power_state"] else "OFF",
                "Wifi": {
                    "AP": 1,
                    "SSId": "WiFi-Network",
                    "BSSId": "AA:BB:CC:DD:EE:FF",
                    "Channel": 6,
                    "Mode": "11n",
                    "RSSI": hash(DEVICE_ID) % 30 + 50,  # -30 to -80 dBm
                    "Signal": -(hash(DEVICE_ID) % 30 + 50),
                    "LinkCount": 1,
                    "Downtime": "0T00:00:03"
                }
            }
        }
    
    elif level == 12:  # Crash dump (if available)
        return {
            "StatusCRASH": {
                "CrashDump": "No crash dump available",
                "StackTrace": []
            }
        }
    
    else:  # level == 0 or default - abbreviated status
        return {
            "Status": {
                "Module": 1,
                "DeviceName": DEVICE_NAME,
                "FriendlyName": [DEVICE_NAME],
                "Topic": DEVICE_ID,
                "ButtonTopic": "0",
                "Power": 1 if realistic_data["power_state"] else 0,
                "PowerOnState": 3,
                "LedState": 1,
                "SaveData": 1,
                "SaveState": 1,
                "SwitchTopic": "0",
                "ButtonRetain": 0,
                "PowerRetain": 0
            },
            "StatusPRM": {
                "Baudrate": 115200,
                "SerialConfig": "8N1",
                "GroupTopic": "tasmotas",
                "OtaUrl": "http://ota.tasmota.com/tasmota/release-12.5.0/tasmota.bin.gz",
                "RestartReason": "Software/System restart",
                "Uptime": f"0T{uptime//3600:02d}:{(uptime%3600)//60:02d}:{uptime%60:02d}",
                "StartupUTC": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "Sleep": 50,
                "CfgHolder": 4617,
                "BootCount": 45,
                "BCResetTime": "2020-02-13T15:08:27",
                "SaveCount": 164,
                "SaveAddress": "FB000"
            },
            "StatusFWR": {
                "Version": "12.5.0(tasmota)",
                "BuildDateTime": "2023-12-01T10:00:00",
                "Boot": 31,
                "Core": "2_7_4",
                "SDK": "2.2.2-dev(38a443e)",
                "CpuFrequency": 80,
                "Hardware": "ESP8266EX"
            },
            "StatusLOG": {
                "SerialLog": 2,
                "WebLog": 2,
                "MqttLog": 0,
                "SysLog": 0,
                "LogHost": "",
                "LogPort": 514,
                "SSId": ["WiFi-Network", ""],
                "TelePeriod": 300,
                "Resolution": "558180C0"
            },
            "StatusMEM": {
                "ProgramSize": 595,
                "Free": 404,
                "Heap": 25,
                "ProgramFlashSize": 1024,
                "FlashSize": 1024,
                "FlashChipId": "1640E0",
                "FlashFrequency": 40,
                "FlashMode": 3
            },
            "StatusNET": {
                "Hostname": DEVICE_ID,
                "IPAddress": DEVICE_IP,
                "Gateway": "172.25.0.1",
                "Subnetmask": "255.255.0.0",
                "DNSServer1": "8.8.8.8",
                "DNSServer2": "8.8.4.4",
                "Mac": f"AA:BB:CC:DD:EE:{hash(DEVICE_ID) % 256:02X}",
                "Webserver": 2,
                "HTTP_API": 1,
                "WifiConfig": 4,
                "WifiPower": 17.0
            },
            "StatusMQT": {
                "MqttHost": "172.25.0.10",
                "MqttPort": 5672,
                "MqttClientMask": DEVICE_ID,
                "MqttClient": DEVICE_ID,
                "MqttUser": "admin",
                "MqttCount": 1,
                "MAX_PACKET_SIZE": 1200,
                "KEEPALIVE": 30
            },
            "StatusTIM": {
                "UTC": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "Local": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "StartDST": "2024-03-31T02:00:00",
                "EndDST": "2024-10-27T03:00:00",
                "Timezone": "+01:00",
                "Sunrise": "06:30",
                "Sunset": "18:45"
            },
            "StatusSTS": {
                "Time": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "Uptime": f"0T{uptime//3600:02d}:{(uptime%3600)//60:02d}:{uptime%60:02d}",
                "UptimeSec": uptime,
                "Heap": 25,
                "SleepMode": "Dynamic",
                "Sleep": 50,
                "LoadAvg": 19,
                "MqttCount": 1,
                "POWER": "ON" if realistic_data["power_state"] else "OFF",
                "Wifi": {
                    "AP": 1,
                    "SSId": "WiFi-Network", 
                    "BSSId": "AA:BB:CC:DD:EE:FF",
                    "Channel": 6,
                    "Mode": "11n",
                    "RSSI": hash(DEVICE_ID) % 30 + 50,
                    "Signal": -(hash(DEVICE_ID) % 30 + 50),
                    "LinkCount": 1,
                    "Downtime": "0T00:00:03"
                }
            }
        }

@app.get("/cm")
async def command(
    cmnd: str = Query(..., description="Command to execute"),
    user: Optional[str] = None,
    password: Optional[str] = None,
    _: bool = Depends(verify_credentials)
):
    """
    Handle Tasmota-like commands.
    Examples: 
    - /cm?cmnd=Power%20TOGGLE
    - /cm?cmnd=Status
    - /cm?cmnd=Status%200
    - /cm?cmnd=Status%209
    """
    if not cmnd:
        raise HTTPException(status_code=400, detail="Command is required")

    # Parse command and parameter
    parts = cmnd.split()
    command = parts[0].upper()
    parameter = parts[1] if len(parts) > 1 else None

    # Handle Power commands
    if command == "POWER":
        if parameter and parameter.upper() == "TOGGLE":
            new_state = not (power_state.POWER == "ON")
            power_state.POWER = "ON" if new_state else "OFF"
        elif parameter and parameter.upper() in ["ON", "1", "TRUE"]:
            new_state = True
            power_state.POWER = "ON"
        elif parameter and parameter.upper() in ["OFF", "0", "FALSE"]:
            new_state = False
            power_state.POWER = "OFF"
        elif not parameter:
            # Just return current state
            return {"POWER": power_state.POWER}
        else:
            raise HTTPException(status_code=400, detail=f"Invalid power parameter: {parameter}")
        
        # Update power profile manager with new state
        power_profile_manager.set_device_power_state(DEVICE_ID, new_state)
        
        return {"POWER": power_state.POWER}
    
    # Handle Status commands
    elif command == "STATUS":
        try:
            level = int(parameter) if parameter else 0
            if level < 0 or level > 12:
                raise HTTPException(status_code=400, detail="Status level must be between 0 and 12")
            return get_status_response(level)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status level: {parameter}")
    
    # Add more command handlers here as needed
    
    raise HTTPException(status_code=400, detail=f"Unknown command: {command}")

@app.get("/", response_model=DeviceInfo)
async def root():
    """Root endpoint that returns comprehensive device info with realistic data."""
    realistic_data = get_realistic_device_data()
    
    return DeviceInfo(
        Device=DEVICE_NAME,
        Version="1.0.0",
        IPAddress=DEVICE_IP,
        Status="Online",
        device_id=DEVICE_ID,
        device_name=DEVICE_NAME,
        power_state=realistic_data["power_state"],
        energy_consumption=realistic_data["energy_consumption"],
        total_energy=realistic_data["total_energy"],
        profile_name=realistic_data["profile_name"],
        profile_category=realistic_data["profile_category"],
        voltage=realistic_data["voltage"],
        current=realistic_data["current"]
    )

@app.get("/status", response_model=DeviceInfo)
async def get_status():
    """Get device status (alias for root endpoint)."""
    return await root()

@app.get("/energy", response_model=EnergyData)
async def get_energy():
    """Get detailed energy consumption data."""
    realistic_data = get_realistic_device_data()
    
    power = realistic_data["energy_consumption"]
    voltage = realistic_data["voltage"]
    current = realistic_data["current"]
    total = realistic_data["total_energy"]
    
    return EnergyData(
        power=power,
        apparent_power=power * 1.05,  # Add some reactive power
        reactive_power=power * 0.1,
        factor=0.95,  # Power factor
        voltage=voltage,
        current=current,
        total=total,
        today=total * 0.1,  # Estimate today's consumption
        yesterday=total * 0.08  # Estimate yesterday's consumption
    )

@app.get("/power-profile")
async def get_power_profile():
    """Get detailed power profile information."""
    try:
        return power_profile_manager.get_device_info(DEVICE_ID)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting power profile: {str(e)}")

@app.post("/power/{state}")
async def set_power(state: str):
    """Set device power state via REST API."""
    state_lower = state.lower()
    
    if state_lower == "on":
        new_state = True
        power_state.POWER = "ON"
    elif state_lower == "off":
        new_state = False
        power_state.POWER = "OFF"
    elif state_lower == "toggle":
        new_state = not (power_state.POWER == "ON")
        power_state.POWER = "ON" if new_state else "OFF"
    else:
        raise HTTPException(status_code=400, detail="Invalid power state. Use 'on', 'off', or 'toggle'")
    
    # Update power profile manager
    power_profile_manager.set_device_power_state(DEVICE_ID, new_state)
    
    return {"power_state": new_state, "message": f"Power turned {state_lower}"} 