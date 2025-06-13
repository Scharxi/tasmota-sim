# Realistische Stromverbrauchsprofile

Das Tasmota-Simulator-System verwendet jetzt realistische Stromverbrauchsprofile, die auf echten Gerätekategorien und -verhaltensweisen basieren.

## 🎯 Features

### Gerätekategorien

Das System unterstützt folgende Hauptkategorien:

| Kategorie | Beispiele | Typischer Verbrauch | Besonderheiten |
|-----------|-----------|-------------------|----------------|
| **Beleuchtung** | LED, Halogen, Smart Lampen | 6-50W | Tageszeit-abhängig |
| **Heizung** | Heizlüfter, Radiatoren | 600-2000W | Saisonal, zyklisch |
| **Kleine Geräte** | Kaffeemaschine, Toaster | 800-2200W | Mahlzeit-abhängig |
| **Große Geräte** | Mikrowelle, Kühlschrank | 120-2200W | Zyklische Kompressoren |
| **Elektronik** | TV, Computer, Router | 8-400W | Nutzungszeit-abhängig |
| **Motoren** | Waschmaschine, Staubsauger | 25-2500W | Variable Last |
| **Dauerbetrieb** | Kameras, Smart Hubs | 2-8W | Konstant aktiv |

### Realistische Verhaltensweisen

#### 🕐 Tageszeit-abhängiger Verbrauch
- **Beleuchtung**: Höherer Verbrauch morgens (6-8h) und abends (17-23h)
- **Elektronik**: Peak-Zeiten am Abend (18-23h)
- **Kleine Geräte**: Erhöhte Aktivität zu Mahlzeiten (7h, 12h, 18h)

#### 🌡️ Saisonale Faktoren
- **Heizung**: 1.5x Verbrauch im Winter, 0.3x im Sommer
- **Ventilatoren**: 1.4x Verbrauch im Sommer, 0.6x im Winter

#### 🔄 Zyklisches Verhalten
- **Heizgeräte**: 15-25min Zyklen mit 70% Einschaltzeit
- **Kühlschränke**: 45min Zyklen mit variierender Kompressorlast
- **Waschmaschinen**: Variable Lastprofile je nach Programm

#### 📊 Dynamische Variation
- Realistische Schwankungen basierend auf Geräteart (5-50% Variation)
- Spannungsschwankungen (230V ±5V)
- Temperatur- und umgebungsbedingte Faktoren

## 🛠️ Verwendung

### Automatische Profilzuweisung

Das System erkennt automatisch Gerätekategorien basierend auf dem Gerätenamen:

```bash
# Beispiele für automatische Erkennung:
kitchen_coffee_maker     → Kaffeemaschine (kleine Geräte)
living_room_heater       → Heizlüfter (Heizung)
bedroom_led_lamp         → LED Lampe (Beleuchtung)
basement_washing_machine → Waschmaschine (Motor)
```

### CLI-Befehle

#### Verfügbare Profile anzeigen
```bash
tasmota-sim list-power-profiles
```

#### Geräte-Strominfo anzeigen
```bash
tasmota-sim device-power-info kitchen_001
```

#### Manuelles Profil zuweisen
```bash
# Nach Name zuweisen
tasmota-sim assign-power-profile kitchen_001 --profile-name "Kaffeemaschine"

# Nach Kategorie zuweisen
tasmota-sim assign-power-profile living_001 --category heating
```

#### Live-Simulation
```bash
# 60 Sekunden Simulation mit 5s Updates
tasmota-sim simulate-power-usage kitchen_001 --duration 60 --interval 5
```

### Programmierung

```python
from tasmota_sim.power_profiles import power_profile_manager, DeviceCategory

# Profil zuweisen
profile = power_profile_manager.assign_profile_to_device(
    "device_001", 
    profile_name="Heizlüfter"
)

# Aktuellen Verbrauch abrufen
power = power_profile_manager.get_device_power_consumption("device_001")

# Gerätestatus setzen
new_power = power_profile_manager.set_device_power_state("device_001", True)

# Detaillierte Info abrufen
info = power_profile_manager.get_device_info("device_001")
```

## 📈 Verbrauchsbeispiele

### Heizlüfter (Winter, Abends)
```
Zeit    | Verbrauch | Status
--------|-----------|--------
18:00   | 1850W     | EIN (Aufheizen)
18:15   | 0W        | AUS (Zyklus)
18:20   | 1620W     | EIN (Nachheizen)
18:35   | 0W        | AUS (Zyklus)
```

### LED Lampe (Abends)
```
Zeit    | Verbrauch | Status
--------|-----------|--------
17:00   | 12.5W     | EIN (Peak-Zeit)
19:00   | 13.2W     | EIN (Variation)
23:00   | 11.8W     | EIN (späte Stunde)
01:00   | 0.2W      | AUS (Standby)
```

### Kühlschrank (Dauerbetrieb)
```
Zeit    | Verbrauch | Status
--------|-----------|--------
12:00   | 165W      | EIN (Kompressor)
12:45   | 45W       | AUS (nur Lüfter)
13:30   | 180W      | EIN (Kompressor)
14:15   | 40W       | AUS (nur Lüfter)
```

## 🔧 Konfiguration

### Neue Profile hinzufügen

Bearbeiten Sie `tasmota_sim/power_profiles.py`:

```python
PowerProfile(
    category=DeviceCategory.ELECTRONICS,
    name="Gaming PC",
    base_watts_min=300.0,
    base_watts_max=650.0,
    standby_watts=15.0,
    variation_factor=0.3,
    time_of_day_factor=True,
    description="High-End Gaming Computer"
)
```

### Anpassbare Parameter

- `base_watts_min/max`: Leistungsbereich bei Betrieb
- `standby_watts`: Standby-Verbrauch
- `variation_factor`: Schwankungsbereich (0.0-1.0)
- `cycle_minutes`: Zykluszeit für automatisches An/Aus
- `time_of_day_factor`: Tageszeit-Abhängigkeit aktivieren
- `seasonal_factor`: Saisonale Abhängigkeit aktivieren

## 📊 Monitoring

### Web-Interface Integration

Die realistischen Verbrauchswerte werden automatisch über das Web-Interface und die API bereitgestellt:

```bash
# Direkter Zugriff auf Device-Status
curl http://172.25.0.100/

# Tasmota-Commands mit realistischen Werten
curl -u admin:test1234! "http://172.25.0.100/cm?cmnd=Power%20ON"
```

### RabbitMQ Messages

Alle Telemetrie- und Status-Nachrichten enthalten die realistischen Verbrauchswerte:

```json
{
  "device_id": "kitchen_001",
  "power_state": true,
  "energy": {
    "power": 1245.3,
    "voltage": 228.5,
    "current": 5.449,
    "total": 125.847
  }
}
```

## 🎯 Vorteile

1. **Realistische Simulation**: Echte Verbrauchsmuster statt zufällige Werte
2. **Zeitabhängige Variation**: Verbrauch ändert sich realistisch über den Tag
3. **Gerätespezifisches Verhalten**: Jeder Gerätetyp verhält sich charakteristisch
4. **Automatische Erkennung**: Intelligente Profilzuweisung basierend auf Namen
5. **Einfache Erweiterung**: Neue Profile und Kategorien einfach hinzufügbar
6. **CLI-Tools**: Umfassende Befehle zur Verwaltung und Simulation

Das System macht den Tasmota-Simulator deutlich realistischer für Tests, Entwicklung und Demonstrationen von Smart Home Systemen. 