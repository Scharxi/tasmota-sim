#!/usr/bin/env python3
"""
Database module for Tasmota Device Simulator.
Handles SQLite database operations for device management.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .models import Device, DeviceStatus, Container


class TasmotaDatabase:
    """SQLite database handler for Tasmota simulator."""
    
    def __init__(self, db_path: str = "tasmota_devices.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables."""
        with self.get_connection() as conn:
            conn.executescript("""
                -- Devices table
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    room TEXT,
                    device_type TEXT DEFAULT 'switch',
                    ip_address TEXT UNIQUE,
                    port INTEGER DEFAULT 80,
                    prefix TEXT DEFAULT 'kitchen',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP,
                    status TEXT DEFAULT 'offline',
                    config_json TEXT  -- Additional configuration as JSON
                );
                
                -- Container mapping
                CREATE TABLE IF NOT EXISTS containers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT REFERENCES devices(id) ON DELETE CASCADE,
                    container_name TEXT UNIQUE,
                    docker_service_name TEXT,
                    host_port INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(device_id)
                );
                
                -- Device status history
                CREATE TABLE IF NOT EXISTS device_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT REFERENCES devices(id) ON DELETE CASCADE,
                    power_state BOOLEAN,
                    energy_consumption REAL,
                    total_energy REAL,
                    voltage REAL,
                    current REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Rooms/Groups
                CREATE TABLE IF NOT EXISTS rooms (
                    name TEXT PRIMARY KEY,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Indexes for better performance
                CREATE INDEX IF NOT EXISTS idx_devices_room ON devices(room);
                CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
                CREATE INDEX IF NOT EXISTS idx_device_status_timestamp ON device_status(timestamp);
                CREATE INDEX IF NOT EXISTS idx_containers_device_id ON containers(device_id);
            """)
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def create_device(self, device: Device) -> bool:
        """Create a new device in the database."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO devices (
                        id, name, room, device_type, ip_address, port, prefix, 
                        status, config_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    device.id,
                    device.name,
                    device.room,
                    device.device_type,
                    device.ip_address,
                    device.port,
                    device.prefix,
                    device.status,
                    json.dumps(device.config) if device.config else None
                ))
            return True
        except sqlite3.IntegrityError:
            return False  # Device already exists
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """Get a device by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM devices WHERE id = ?", (device_id,)
            ).fetchone()
            
            if row:
                return Device(
                    id=row['id'],
                    name=row['name'],
                    room=row['room'],
                    device_type=row['device_type'],
                    ip_address=row['ip_address'],
                    port=row['port'],
                    prefix=row['prefix'],
                    status=row['status'],
                    config=json.loads(row['config_json']) if row['config_json'] else {},
                    created_at=row['created_at'],
                    last_seen=row['last_seen']
                )
            return None
    
    def list_devices(self, room: Optional[str] = None, status: Optional[str] = None) -> List[Device]:
        """List devices with optional filtering."""
        query = "SELECT * FROM devices WHERE 1=1"
        params = []
        
        if room:
            query += " AND room = ?"
            params.append(room)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at"
        
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            
            devices = []
            for row in rows:
                devices.append(Device(
                    id=row['id'],
                    name=row['name'],
                    room=row['room'],
                    device_type=row['device_type'],
                    ip_address=row['ip_address'],
                    port=row['port'],
                    prefix=row['prefix'],
                    status=row['status'],
                    config=json.loads(row['config_json']) if row['config_json'] else {},
                    created_at=row['created_at'],
                    last_seen=row['last_seen']
                ))
            
            return devices
    
    def update_device_status(self, device_id: str, status: str, last_seen: Optional[str] = None):
        """Update device status and last seen timestamp."""
        if last_seen is None:
            last_seen = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE devices 
                SET status = ?, last_seen = ? 
                WHERE id = ?
            """, (status, last_seen, device_id))
    
    def delete_device(self, device_id: str) -> bool:
        """Delete a device and its related data."""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
            return cursor.rowcount > 0
    
    def create_container(self, container: Container) -> bool:
        """Create container mapping for a device."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO containers (
                        device_id, container_name, docker_service_name, host_port
                    ) VALUES (?, ?, ?, ?)
                """, (
                    container.device_id,
                    container.container_name,
                    container.docker_service_name,
                    container.host_port
                ))
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_containers(self, device_id: Optional[str] = None) -> List[Container]:
        """Get container mappings."""
        query = """
            SELECT c.*, d.name as device_name, d.ip_address 
            FROM containers c 
            JOIN devices d ON c.device_id = d.id
        """
        params = []
        
        if device_id:
            query += " WHERE c.device_id = ?"
            params.append(device_id)
        
        query += " ORDER BY c.created_at"
        
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            
            containers = []
            for row in rows:
                containers.append(Container(
                    device_id=row['device_id'],
                    container_name=row['container_name'],
                    docker_service_name=row['docker_service_name'],
                    host_port=row['host_port'],
                    device_name=row['device_name'],
                    ip_address=row['ip_address'],
                    created_at=row['created_at']
                ))
            
            return containers
    
    def delete_container(self, device_id: str) -> bool:
        """Delete container mapping for a device."""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM containers WHERE device_id = ?", (device_id,))
            return cursor.rowcount > 0
    
    def add_device_status(self, status: DeviceStatus):
        """Add device status/telemetry entry."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO device_status (
                    device_id, power_state, energy_consumption, 
                    total_energy, voltage, current
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                status.device_id,
                status.power_state,
                status.energy_consumption,
                status.total_energy,
                status.voltage,
                status.current
            ))
    
    def get_device_status_history(self, device_id: str, limit: int = 100) -> List[DeviceStatus]:
        """Get device status history."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM device_status 
                WHERE device_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (device_id, limit)).fetchall()
            
            history = []
            for row in rows:
                history.append(DeviceStatus(
                    device_id=row['device_id'],
                    power_state=bool(row['power_state']),
                    energy_consumption=row['energy_consumption'],
                    total_energy=row['total_energy'],
                    voltage=row['voltage'],
                    current=row['current'],
                    timestamp=row['timestamp']
                ))
            
            return history
    
    def create_room(self, name: str, description: str = "") -> bool:
        """Create a room/group."""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO rooms (name, description) VALUES (?, ?)
                """, (name, description))
            return True
        except sqlite3.IntegrityError:
            return False
    
    def list_rooms(self) -> List[Dict[str, Any]]:
        """List all rooms."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT r.*, COUNT(d.id) as device_count 
                FROM rooms r 
                LEFT JOIN devices d ON r.name = d.room 
                GROUP BY r.name 
                ORDER BY r.created_at
            """).fetchall()
            
            rooms = []
            for row in rows:
                rooms.append({
                    'name': row['name'],
                    'description': row['description'],
                    'device_count': row['device_count'],
                    'created_at': row['created_at']
                })
            
            return rooms
    
    def get_all_ip_addresses(self) -> List[str]:
        """Get all device IP addresses for IP alias management."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT ip_address FROM devices WHERE ip_address IS NOT NULL ORDER BY ip_address"
            ).fetchall()
            
            return [row['ip_address'] for row in rows]
    
    def cleanup_orphaned_containers(self):
        """Remove container entries for devices that no longer exist."""
        with self.get_connection() as conn:
            conn.execute("""
                DELETE FROM containers 
                WHERE device_id NOT IN (SELECT id FROM devices)
            """)
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        with self.get_connection() as conn:
            stats = {}
            
            # Count devices by status
            rows = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM devices 
                GROUP BY status
            """).fetchall()
            
            for row in rows:
                stats[f"devices_{row['status']}"] = row['count']
            
            # Total counts
            stats['total_devices'] = conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
            stats['total_containers'] = conn.execute("SELECT COUNT(*) FROM containers").fetchone()[0]
            stats['total_rooms'] = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
            stats['total_status_entries'] = conn.execute("SELECT COUNT(*) FROM device_status").fetchone()[0]
            
            return stats 