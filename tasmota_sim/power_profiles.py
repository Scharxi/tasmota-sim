#!/usr/bin/env python3
"""
Realistic power consumption profiles for different device types.
Simulates realistic power usage patterns based on device category and time of day.
"""

import random
import math
from datetime import datetime, time
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field


class DeviceCategory(Enum):
    """Device categories with different power profiles."""
    LIGHTING = "lighting"
    HEATING = "heating"
    APPLIANCE_SMALL = "appliance_small"
    APPLIANCE_LARGE = "appliance_large"
    ELECTRONICS = "electronics"
    MOTOR = "motor"
    ALWAYS_ON = "always_on"


@dataclass
class PowerProfile:
    """Power consumption profile for a device category."""
    category: DeviceCategory
    name: str
    base_watts_min: float  # Minimum power when ON
    base_watts_max: float  # Maximum power when ON
    standby_watts: float   # Standby power when OFF
    variation_factor: float = 0.1  # How much power varies (0.0-1.0)
    cycle_minutes: Optional[int] = None  # Cycling period in minutes
    time_of_day_factor: bool = True  # Whether consumption varies by time of day
    seasonal_factor: bool = False  # Whether consumption varies by season
    description: str = ""


# Predefined power profiles for different device types
POWER_PROFILES = {
    # Beleuchtung
    DeviceCategory.LIGHTING: [
        PowerProfile(
            category=DeviceCategory.LIGHTING,
            name="LED Lampe",
            base_watts_min=8.0,
            base_watts_max=15.0,
            standby_watts=0.2,
            variation_factor=0.05,
            description="Moderne LED-Beleuchtung"
        ),
        PowerProfile(
            category=DeviceCategory.LIGHTING,
            name="Halogen Lampe",
            base_watts_min=35.0,
            base_watts_max=50.0,
            standby_watts=0.5,
            variation_factor=0.03,
            description="Traditionelle Halogenbeleuchtung"
        ),
        PowerProfile(
            category=DeviceCategory.LIGHTING,
            name="Smart Lampe",
            base_watts_min=6.0,
            base_watts_max=18.0,
            standby_watts=1.5,
            variation_factor=0.15,
            description="Intelligente dimmbare LED-Lampe"
        ),
    ],
    
    # Heizung
    DeviceCategory.HEATING: [
        PowerProfile(
            category=DeviceCategory.HEATING,
            name="Heizlüfter",
            base_watts_min=1200.0,
            base_watts_max=2000.0,
            standby_watts=2.0,
            variation_factor=0.2,
            cycle_minutes=15,  # Zyklisch an/aus
            seasonal_factor=True,
            description="Elektrischer Heizlüfter"
        ),
        PowerProfile(
            category=DeviceCategory.HEATING,
            name="Heizkörper",
            base_watts_min=800.0,
            base_watts_max=1500.0,
            standby_watts=1.5,
            variation_factor=0.25,
            cycle_minutes=20,
            seasonal_factor=True,
            description="Elektrischer Radiator"
        ),
        PowerProfile(
            category=DeviceCategory.HEATING,
            name="Infrarotheizer",
            base_watts_min=600.0,
            base_watts_max=1200.0,
            standby_watts=1.0,
            variation_factor=0.15,
            cycle_minutes=25,
            seasonal_factor=True,
            description="Infrarot-Heizpanel"
        ),
    ],
    
    # Kleine Haushaltsgeräte
    DeviceCategory.APPLIANCE_SMALL: [
        PowerProfile(
            category=DeviceCategory.APPLIANCE_SMALL,
            name="Kaffeemaschine",
            base_watts_min=800.0,
            base_watts_max=1200.0,
            standby_watts=2.5,
            variation_factor=0.3,
            time_of_day_factor=True,
            description="Filterkaffeemaschine"
        ),
        PowerProfile(
            category=DeviceCategory.APPLIANCE_SMALL,
            name="Wasserkocher",
            base_watts_min=1800.0,
            base_watts_max=2200.0,
            standby_watts=0.8,
            variation_factor=0.1,
            description="Elektrischer Wasserkocher"
        ),
        PowerProfile(
            category=DeviceCategory.APPLIANCE_SMALL,
            name="Toaster",
            base_watts_min=800.0,
            base_watts_max=1400.0,
            standby_watts=1.2,
            variation_factor=0.2,
            description="2-Scheiben Toaster"
        ),
    ],
    
    # Große Haushaltsgeräte
    DeviceCategory.APPLIANCE_LARGE: [
        PowerProfile(
            category=DeviceCategory.APPLIANCE_LARGE,
            name="Mikrowelle",
            base_watts_min=1000.0,
            base_watts_max=1500.0,
            standby_watts=3.0,
            variation_factor=0.2,
            description="Mikrowellenherd"
        ),
        PowerProfile(
            category=DeviceCategory.APPLIANCE_LARGE,
            name="Kühlschrank",
            base_watts_min=120.0,
            base_watts_max=200.0,
            standby_watts=5.0,
            variation_factor=0.3,
            cycle_minutes=45,  # Kühlkompressor-Zyklen
            description="Kühl-Gefrierkombination"
        ),
        PowerProfile(
            category=DeviceCategory.APPLIANCE_LARGE,
            name="Geschirrspüler",
            base_watts_min=1800.0,
            base_watts_max=2200.0,
            standby_watts=4.0,
            variation_factor=0.4,
            description="Vollintegrierbarer Geschirrspüler"
        ),
    ],
    
    # Elektronik
    DeviceCategory.ELECTRONICS: [
        PowerProfile(
            category=DeviceCategory.ELECTRONICS,
            name="TV LED",
            base_watts_min=80.0,
            base_watts_max=150.0,
            standby_watts=0.8,
            variation_factor=0.2,
            time_of_day_factor=True,
            description="LED-Fernseher 55 Zoll"
        ),
        PowerProfile(
            category=DeviceCategory.ELECTRONICS,
            name="Computer Desktop",
            base_watts_min=200.0,
            base_watts_max=400.0,
            standby_watts=8.0,
            variation_factor=0.4,
            time_of_day_factor=True,
            description="Desktop-PC mit Monitor"
        ),
        PowerProfile(
            category=DeviceCategory.ELECTRONICS,
            name="Router/Modem",
            base_watts_min=8.0,
            base_watts_max=15.0,
            standby_watts=8.0,  # Always on
            variation_factor=0.1,
            description="WLAN-Router"
        ),
    ],
    
    # Motoren
    DeviceCategory.MOTOR: [
        PowerProfile(
            category=DeviceCategory.MOTOR,
            name="Waschmaschine",
            base_watts_min=1800.0,
            base_watts_max=2500.0,
            standby_watts=2.5,
            variation_factor=0.5,
            description="Frontlader-Waschmaschine"
        ),
        PowerProfile(
            category=DeviceCategory.MOTOR,
            name="Staubsauger",
            base_watts_min=1200.0,
            base_watts_max=1800.0,
            standby_watts=1.0,
            variation_factor=0.3,
            description="Bodenstaubsauger"
        ),
        PowerProfile(
            category=DeviceCategory.MOTOR,
            name="Ventilator",
            base_watts_min=25.0,
            base_watts_max=75.0,
            standby_watts=0.5,
            variation_factor=0.2,
            seasonal_factor=True,
            description="Deckenventilator"
        ),
    ],
    
    # Immer an
    DeviceCategory.ALWAYS_ON: [
        PowerProfile(
            category=DeviceCategory.ALWAYS_ON,
            name="Überwachungskamera",
            base_watts_min=3.0,
            base_watts_max=8.0,
            standby_watts=3.0,
            variation_factor=0.1,
            description="IP-Überwachungskamera"
        ),
        PowerProfile(
            category=DeviceCategory.ALWAYS_ON,
            name="Smart Hub",
            base_watts_min=2.0,
            base_watts_max=5.0,
            standby_watts=2.0,
            variation_factor=0.05,
            description="Smart Home Hub"
        ),
    ],
}


@dataclass
class DevicePowerState:
    """Current power state and consumption tracking for a device."""
    device_id: str
    profile: PowerProfile
    power_state: bool = False
    current_watts: float = 0.0
    cycle_position: float = 0.0  # For cycling devices (0.0-1.0)
    last_update: datetime = field(default_factory=datetime.now)
    total_energy_kwh: float = 0.0
    
    def update_power_consumption(self) -> float:
        """Update and return current power consumption based on profile and time."""
        now = datetime.now()
        time_since_last = (now - self.last_update).total_seconds()
        
        if not self.power_state:
            # Device is OFF - use standby power
            self.current_watts = self._add_variation(self.profile.standby_watts)
        else:
            # Device is ON - calculate active power
            base_power = self._calculate_base_power()
            time_factor = self._get_time_of_day_factor() if self.profile.time_of_day_factor else 1.0
            seasonal_factor = self._get_seasonal_factor() if self.profile.seasonal_factor else 1.0
            cycle_factor = self._get_cycle_factor()
            
            # Combine all factors
            power = base_power * time_factor * seasonal_factor * cycle_factor
            self.current_watts = self._add_variation(power)
        
        # Update energy consumption
        if time_since_last > 0:
            energy_kwh = (self.current_watts * time_since_last) / (1000 * 3600)  # W*s to kWh
            self.total_energy_kwh += energy_kwh
        
        self.last_update = now
        return self.current_watts
    
    def _calculate_base_power(self) -> float:
        """Calculate base power consumption."""
        # Use a weighted random between min and max
        return random.uniform(self.profile.base_watts_min, self.profile.base_watts_max)
    
    def _add_variation(self, base_power: float) -> float:
        """Add random variation to power consumption."""
        variation_range = base_power * self.profile.variation_factor
        variation = random.uniform(-variation_range, variation_range)
        return max(0.0, base_power + variation)
    
    def _get_time_of_day_factor(self) -> float:
        """Get time-of-day factor (morning/evening peaks)."""
        current_hour = datetime.now().hour
        
        # Different patterns for different device categories
        if self.profile.category in [DeviceCategory.LIGHTING]:
            # Lighting: peaks in evening and early morning
            if 6 <= current_hour <= 8 or 17 <= current_hour <= 23:
                return 1.2  # Higher consumption during usage times
            elif 0 <= current_hour <= 5:
                return 0.3  # Lower consumption at night
            else:
                return 0.7  # Moderate consumption during day
                
        elif self.profile.category in [DeviceCategory.APPLIANCE_SMALL]:
            # Small appliances: peaks at meal times
            if current_hour in [7, 8, 12, 13, 18, 19]:
                return 1.3  # Meal times
            elif 0 <= current_hour <= 6:
                return 0.2  # Night
            else:
                return 1.0
                
        elif self.profile.category in [DeviceCategory.ELECTRONICS]:
            # Electronics: higher in evening
            if 18 <= current_hour <= 23:
                return 1.4  # Evening entertainment
            elif 9 <= current_hour <= 17:
                return 1.1  # Work hours
            elif 0 <= current_hour <= 6:
                return 0.3  # Night
            else:
                return 1.0
        
        return 1.0  # Default factor
    
    def _get_seasonal_factor(self) -> float:
        """Get seasonal factor (higher heating in winter)."""
        if self.profile.category == DeviceCategory.HEATING:
            month = datetime.now().month
            if month in [12, 1, 2]:  # Winter
                return 1.5
            elif month in [3, 11]:   # Spring/Fall
                return 1.2
            elif month in [6, 7, 8]: # Summer
                return 0.3
            else:
                return 1.0
        elif self.profile.category == DeviceCategory.MOTOR and "ventilator" in self.profile.name.lower():
            # Fans: higher in summer
            month = datetime.now().month
            if month in [6, 7, 8]:   # Summer
                return 1.4
            elif month in [5, 9]:    # Late spring/early fall
                return 1.1
            else:
                return 0.6
        
        return 1.0
    
    def _get_cycle_factor(self) -> float:
        """Get cycling factor for devices that turn on/off periodically."""
        if not self.profile.cycle_minutes:
            return 1.0
        
        # Update cycle position
        minutes_since_update = (datetime.now() - self.last_update).total_seconds() / 60
        cycle_increment = minutes_since_update / self.profile.cycle_minutes
        self.cycle_position = (self.cycle_position + cycle_increment) % 1.0
        
        # Generate cycling pattern (sine wave with some randomness)
        cycle_value = math.sin(self.cycle_position * 2 * math.pi)
        
        # For heating devices: longer ON periods, shorter OFF periods
        if self.profile.category == DeviceCategory.HEATING:
            # Transform sine wave to favor ON state
            if cycle_value > -0.3:  # ON for about 70% of the cycle
                return 1.0 + (cycle_value * 0.2)  # Vary between 0.8 and 1.2
            else:
                return 0.1  # Minimal consumption when "OFF" in cycle
        
        # For cooling devices (like fridges): moderate cycling
        elif "kühl" in self.profile.name.lower() or "fridge" in self.profile.name.lower():
            if cycle_value > 0:
                return 1.0 + (cycle_value * 0.3)  # Compressor running
            else:
                return 0.3  # Compressor off, just fans/lights
        
        # Default cycling pattern
        return max(0.2, 1.0 + (cycle_value * 0.4))


class PowerProfileManager:
    """Manages power profiles and device power states."""
    
    def __init__(self):
        self.device_states: Dict[str, DevicePowerState] = {}
    
    def get_random_profile(self, category: Optional[DeviceCategory] = None) -> PowerProfile:
        """Get a random power profile, optionally filtered by category."""
        if category:
            profiles = POWER_PROFILES.get(category, [])
            if not profiles:
                # Fallback to a simple profile
                return PowerProfile(
                    category=category,
                    name="Generic Device",
                    base_watts_min=10.0,
                    base_watts_max=50.0,
                    standby_watts=1.0
                )
        else:
            # Choose random category and profile
            all_profiles = []
            for profile_list in POWER_PROFILES.values():
                all_profiles.extend(profile_list)
            profiles = all_profiles
        
        return random.choice(profiles)
    
    def assign_profile_to_device(self, device_id: str, profile_name: Optional[str] = None, 
                               category: Optional[DeviceCategory] = None) -> PowerProfile:
        """Assign a power profile to a device."""
        # Try to find specific profile by name
        if profile_name:
            for profile_list in POWER_PROFILES.values():
                for profile in profile_list:
                    if profile.name.lower() == profile_name.lower():
                        self._create_device_state(device_id, profile)
                        return profile
        
        # Get random profile from category or overall
        profile = self.get_random_profile(category)
        self._create_device_state(device_id, profile)
        return profile
    
    def _create_device_state(self, device_id: str, profile: PowerProfile):
        """Create device power state tracking."""
        self.device_states[device_id] = DevicePowerState(
            device_id=device_id,
            profile=profile,
            power_state=random.choice([True, False]),  # Random initial state
            current_watts=profile.standby_watts
        )
    
    def set_device_power_state(self, device_id: str, power_state: bool) -> float:
        """Set device power state and return current consumption."""
        if device_id not in self.device_states:
            # Assign random profile if not exists
            self.assign_profile_to_device(device_id)
        
        device_state = self.device_states[device_id]
        device_state.power_state = power_state
        return device_state.update_power_consumption()
    
    def get_device_power_consumption(self, device_id: str) -> float:
        """Get current power consumption for a device."""
        if device_id not in self.device_states:
            # Assign random profile if not exists
            self.assign_profile_to_device(device_id)
        
        return self.device_states[device_id].update_power_consumption()
    
    def get_device_total_energy(self, device_id: str) -> float:
        """Get total energy consumption for a device."""
        if device_id not in self.device_states:
            return 0.0
        
        # Update consumption first
        self.device_states[device_id].update_power_consumption()
        return self.device_states[device_id].total_energy_kwh
    
    def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """Get detailed device information including profile."""
        if device_id not in self.device_states:
            self.assign_profile_to_device(device_id)
        
        state = self.device_states[device_id]
        current_power = state.update_power_consumption()
        
        return {
            "device_id": device_id,
            "profile_name": state.profile.name,
            "profile_category": state.profile.category.value,
            "profile_description": state.profile.description,
            "power_state": state.power_state,
            "current_watts": current_power,
            "total_energy_kwh": state.total_energy_kwh,
            "standby_watts": state.profile.standby_watts,
            "max_watts": state.profile.base_watts_max,
            "min_watts": state.profile.base_watts_min,
            "has_cycling": state.profile.cycle_minutes is not None,
            "time_dependent": state.profile.time_of_day_factor,
            "seasonal_dependent": state.profile.seasonal_factor
        }
    
    def list_available_profiles(self) -> List[Dict[str, Any]]:
        """List all available power profiles."""
        profiles = []
        for category, profile_list in POWER_PROFILES.items():
            for profile in profile_list:
                profiles.append({
                    "name": profile.name,
                    "category": category.value,
                    "description": profile.description,
                    "min_watts": profile.base_watts_min,
                    "max_watts": profile.base_watts_max,
                    "standby_watts": profile.standby_watts,
                    "has_cycling": profile.cycle_minutes is not None,
                    "time_dependent": profile.time_of_day_factor,
                    "seasonal_dependent": profile.seasonal_factor
                })
        return profiles


# Global instance
power_profile_manager = PowerProfileManager() 