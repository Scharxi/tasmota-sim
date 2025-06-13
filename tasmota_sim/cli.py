#!/usr/bin/env python3
"""
Simple working CLI for Tasmota simulator.
"""

import click
import asyncio
import os
import subprocess
import yaml
from rich.console import Console
from rich.table import Table
from pathlib import Path
import platform
import ipaddress

from .messaging import AsyncTasmotaMessaging
from .database import TasmotaDatabase
from .docker_generator import DockerComposeGenerator
from .models import Device, Container

console = Console()

# Async wrapper
def async_command(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

@click.group()
@click.option('--db-path', default='tasmota_devices.db', help='Path to SQLite database file')
@click.pass_context
def cli(ctx, db_path):
    """Tasmota Device Simulator CLI"""
    # Ensure context object exists
    ctx.ensure_object(dict)
    # Initialize database and store in context
    ctx.obj['db'] = TasmotaDatabase(db_path)
    ctx.obj['generator'] = DockerComposeGenerator(ctx.obj['db'])

@cli.command()
@click.argument('device_id')
@click.option('--no-wait', is_flag=True, help='Send command without waiting for response')
@async_command
async def status(device_id, no_wait):
    """Get device status."""
    console.print(f"[yellow]Connecting to RabbitMQ...[/yellow]")
    
    host = os.getenv("RABBITMQ_HOST", "localhost")
    user = os.getenv("RABBITMQ_USER", "admin")
    password = os.getenv("RABBITMQ_PASS", "admin123")
    
    messaging = AsyncTasmotaMessaging(host, user, password)
    
    try:
        if await messaging.connect():
            console.print("[green]✓[/green] Connected to RabbitMQ")
            
            # By default, always wait for response unless --no-wait is specified
            wait_for_response = not no_wait
            
            success = await messaging.send_command(device_id, 'status', {})
            
            if wait_for_response:
                # Set up listener for response after sending command
                response_received = asyncio.Event()
                response_data = {}
                
                def response_handler(routing_key, exchange, data):
                    if data.get('device_id') == device_id and exchange == 'tasmota.status':
                        response_data.update(data)
                        response_received.set()
                
                # Start listening 
                await messaging.setup_response_listener(response_handler)
            
            if success:
                console.print(f"[green]✓[/green] Requested status from device [cyan]{device_id}[/cyan]")
                
                if wait_for_response:
                    console.print("[yellow]Waiting for response...[/yellow]")
                    try:
                        await asyncio.wait_for(response_received.wait(), timeout=10.0)
                        # Display the response
                        console.print(f"\n[bold green]Status Response from {device_id}:[/bold green]")
                        power_state = response_data.get('power_state', False)
                        power_color = 'green' if power_state else 'red'
                        power_text = 'ON' if power_state else 'OFF'
                        
                        console.print(f"  Power State: [{power_color}]{power_text}[/{power_color}]")
                        console.print(f"  Energy Consumption: [yellow]{response_data.get('energy_consumption', 0):.1f}W[/yellow]")
                        console.print(f"  Total Energy: [blue]{response_data.get('total_energy', 0):.3f}kWh[/blue]")
                        console.print(f"  IP Address: [cyan]{response_data.get('ip_address', 'Unknown')}[/cyan]")
                        console.print(f"  Uptime: [magenta]{response_data.get('uptime', 0)}s[/magenta]")
                        
                        # Additional fields if available
                        if 'firmware_version' in response_data:
                            console.print(f"  Firmware: [blue]{response_data['firmware_version']}[/blue]")
                        if 'wifi_signal' in response_data:
                            console.print(f"  WiFi Signal: [cyan]{response_data['wifi_signal']}dBm[/cyan]")
                            
                    except asyncio.TimeoutError:
                        console.print("[red]✗[/red] Timeout waiting for response")
                else:
                    console.print("[yellow]Check device logs to see the response[/yellow]")
            else:
                console.print(f"[red]✗[/red] Failed to request status from device [cyan]{device_id}[/cyan]")
        else:
            console.print("[red]✗[/red] Failed to connect to RabbitMQ")
    finally:
        await messaging.close()

@cli.command()
@click.argument('device_id')
@click.argument('action', type=click.Choice(['on', 'off']))
@async_command
async def power(device_id, action):
    """Control device power state."""
    console.print(f"[yellow]Connecting to RabbitMQ...[/yellow]")
    
    host = os.getenv("RABBITMQ_HOST", "localhost")
    user = os.getenv("RABBITMQ_USER", "admin")
    password = os.getenv("RABBITMQ_PASS", "admin123")
    
    messaging = AsyncTasmotaMessaging(host, user, password)
    
    try:
        if await messaging.connect():
            console.print("[green]✓[/green] Connected to RabbitMQ")
            
            command = 'power_on' if action == 'on' else 'power_off'
            payload = {'state': action == 'on'}
            
            success = await messaging.send_command(device_id, command, payload)
            
            if success:
                console.print(f"[green]✓[/green] Sent power {action} command to device [cyan]{device_id}[/cyan]")
            else:
                console.print(f"[red]✗[/red] Failed to send command to device [cyan]{device_id}[/cyan]")
        else:
            console.print("[red]✗[/red] Failed to connect to RabbitMQ")
    finally:
        await messaging.close()

@cli.command()
@click.argument('device_id')
@click.option('--no-wait', is_flag=True, help='Send command without waiting for response')
@async_command
async def energy(device_id, no_wait):
    """Get device energy consumption data."""
    console.print(f"[yellow]Connecting to RabbitMQ...[/yellow]")
    
    host = os.getenv("RABBITMQ_HOST", "localhost")
    user = os.getenv("RABBITMQ_USER", "admin")
    password = os.getenv("RABBITMQ_PASS", "admin123")
    
    messaging = AsyncTasmotaMessaging(host, user, password)
    
    try:
        if await messaging.connect():
            console.print("[green]✓[/green] Connected to RabbitMQ")
            
            # By default, always wait for response unless --no-wait is specified
            wait_for_response = not no_wait
            
            success = await messaging.send_command(device_id, 'energy', {})
            
            if wait_for_response:
                # Set up listener for response after sending command
                response_received = asyncio.Event()
                response_data = {}
                
                def response_handler(routing_key, exchange, data):
                    if data.get('device_id') == device_id and exchange == 'tasmota.telemetry':
                        response_data.update(data)
                        response_received.set()
                
                # Start listening
                await messaging.setup_response_listener(response_handler)
            
            if success:
                console.print(f"[green]✓[/green] Requested energy data from device [cyan]{device_id}[/cyan]")
                
                if wait_for_response:
                    console.print("[yellow]Waiting for response...[/yellow]")
                    try:
                        await asyncio.wait_for(response_received.wait(), timeout=10.0)
                        # Display the response
                        console.print(f"\n[bold green]Energy Data from {device_id}:[/bold green]")
                        
                        power_state = response_data.get('power_state', False)
                        power_color = 'green' if power_state else 'red'
                        power_text = 'ON' if power_state else 'OFF'
                        console.print(f"  Power State: [{power_color}]{power_text}[/{power_color}]")
                        
                        energy = response_data.get('energy', {})
                        if energy:
                            console.print(f"  Current Power: [yellow]{energy.get('power', 0):.1f}W[/yellow]")
                            console.print(f"  Apparent Power: [cyan]{energy.get('apparent_power', 0):.1f}VA[/cyan]")
                            console.print(f"  Voltage: [blue]{energy.get('voltage', 0):.1f}V[/blue]")
                            console.print(f"  Current: [magenta]{energy.get('current', 0):.3f}A[/magenta]")
                            console.print(f"  Power Factor: [green]{energy.get('factor', 0):.2f}[/green]")
                            console.print(f"  Total Energy: [red]{energy.get('total', 0):.3f}kWh[/red]")
                            console.print(f"  Today: [yellow]{energy.get('today', 0):.3f}kWh[/yellow]")
                            console.print(f"  Yesterday: [dim]{energy.get('yesterday', 0):.3f}kWh[/dim]")
                        
                        if 'timestamp' in response_data:
                            console.print(f"  Timestamp: [dim]{response_data['timestamp']}[/dim]")
                            
                    except asyncio.TimeoutError:
                        console.print("[red]✗[/red] Timeout waiting for response")
                else:
                    console.print("[yellow]Check device logs to see the response[/yellow]")
            else:
                console.print(f"[red]✗[/red] Failed to request energy data from device [cyan]{device_id}[/cyan]")
        else:
            console.print("[red]✗[/red] Failed to connect to RabbitMQ")
    finally:
        await messaging.close()

def get_ip_alias_commands(ip_addresses):
    """Get platform-specific commands for IP alias management."""
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        setup_commands = [f"sudo ifconfig lo0 alias {ip} up" for ip in ip_addresses]
        remove_commands = [f"sudo ifconfig lo0 -alias {ip}" for ip in ip_addresses]
    elif system == "linux":
        setup_commands = [f"sudo ip addr add {ip}/32 dev lo" for ip in ip_addresses]
        remove_commands = [f"sudo ip addr del {ip}/32 dev lo" for ip in ip_addresses]
    else:  # Windows
        setup_commands = [f"netsh interface ipv4 add address \"Loopback Pseudo-Interface 1\" {ip} 255.255.255.255" for ip in ip_addresses]
        remove_commands = [f"netsh interface ipv4 delete address \"Loopback Pseudo-Interface 1\" {ip}" for ip in ip_addresses]
    
    return setup_commands, remove_commands

def setup_ip_aliases_func(ip_addresses):
    """Set up IP aliases for direct device access."""
    console.print("[yellow]Setting up IP aliases for Tasmota devices...[/yellow]")
    
    setup_commands, _ = get_ip_alias_commands(ip_addresses)
    
    success_count = 0
    for i, (ip, cmd) in enumerate(zip(ip_addresses, setup_commands)):
        try:
            console.print(f"[cyan]Setting up alias for {ip}...[/cyan]")
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            
            if result.returncode == 0:
                success_count += 1
                console.print(f"[green]✓[/green] IP alias {ip} created")
            else:
                console.print(f"[red]✗[/red] Failed to create alias {ip}: {result.stderr}")
                
        except Exception as e:
            console.print(f"[red]✗[/red] Error creating alias {ip}: {e}")
    
    if success_count > 0:
        console.print(f"\n[green]✓[/green] Created {success_count}/{len(ip_addresses)} IP aliases")
        console.print("\n[cyan]You can now access devices directly:[/cyan]")
        for i, ip in enumerate(ip_addresses):
            device_name = f"kitchen_{i+1:03d}"
            console.print(f"  • http://{ip} ({device_name})")
        
        console.print("\n[yellow]Example commands:[/yellow]")
        console.print(f"  curl http://{ip_addresses[0]}")
        console.print(f"  curl -u admin:test1234! 'http://{ip_addresses[0]}/cm?cmnd=Power%20ON'")
        
    return success_count == len(ip_addresses)

def remove_ip_aliases(ip_addresses):
    """Remove IP aliases."""
    console.print("[yellow]Removing IP aliases for Tasmota devices...[/yellow]")
    
    _, remove_commands = get_ip_alias_commands(ip_addresses)
    
    success_count = 0
    for ip, cmd in zip(ip_addresses, remove_commands):
        try:
            console.print(f"[cyan]Removing alias for {ip}...[/cyan]")
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            
            if result.returncode == 0:
                success_count += 1
                console.print(f"[green]✓[/green] IP alias {ip} removed")
            else:
                # Some aliases might not exist, so we don't treat this as critical error
                console.print(f"[yellow]•[/yellow] Alias {ip} was not active or already removed")
                success_count += 1  # Count as success
                
        except Exception as e:
            console.print(f"[red]✗[/red] Error removing alias {ip}: {e}")
    
    console.print(f"\n[green]✓[/green] Processed {success_count}/{len(ip_addresses)} IP aliases")
    return True

@cli.command("setup-ip-aliases")
@click.option('--count', help='Number of IP aliases to create (starting from 172.25.0.100) - if not provided, uses database')
@click.option('--base-ip', default='172.25.0.100', help='Base IP address to start from (only used with --count)')
@click.pass_context
def setup_ip_aliases_cmd(ctx, count, base_ip):
    """Set up IP aliases for direct device access - uses database or manual count."""
    db = ctx.obj['db']
    
    if count is not None:
        # Manual mode - use count and base_ip
        try:
            base_ip_obj = ipaddress.IPv4Address(base_ip)
            base_ip_int = int(base_ip_obj)
            ip_addresses = [str(ipaddress.IPv4Address(base_ip_int + i)) for i in range(count)]
            console.print(f"[yellow]Setting up {count} IP aliases starting from {base_ip}...[/yellow]")
        except ipaddress.AddressValueError:
            console.print(f"[red]✗[/red] Invalid base IP address: {base_ip}")
            return
    else:
        # Database mode - get IP addresses from database
        ip_addresses = db.get_all_ip_addresses()
        if not ip_addresses:
            console.print("[yellow]No devices found in database. Use 'create-devices' first or specify --count.[/yellow]")
            return
        console.print(f"[yellow]Setting up {len(ip_addresses)} IP aliases from database...[/yellow]")
        for ip in ip_addresses:
            console.print(f"  - {ip}")
    
    if setup_ip_aliases_func(ip_addresses):
        console.print(f"\n[green]✓[/green] Successfully set up all IP aliases!")
        console.print("[yellow]You can now start containers and access devices directly.[/yellow]")
    else:
        console.print(f"\n[red]✗[/red] Some IP aliases failed to set up. Check permissions.")

@cli.command("remove-ip-aliases") 
@click.option('--count', help='Number of IP aliases to remove (starting from 172.25.0.100) - if not provided, uses database')
@click.option('--base-ip', default='172.25.0.100', help='Base IP address to start from (only used with --count)')
@click.pass_context
def remove_ip_aliases_cmd(ctx, count, base_ip):
    """Remove IP aliases for device access - uses database or manual count."""
    db = ctx.obj['db']
    
    if count is not None:
        # Manual mode - use count and base_ip
        try:
            base_ip_obj = ipaddress.IPv4Address(base_ip)
            base_ip_int = int(base_ip_obj)
            ip_addresses = [str(ipaddress.IPv4Address(base_ip_int + i)) for i in range(count)]
            console.print(f"[yellow]Removing {count} IP aliases starting from {base_ip}...[/yellow]")
        except ipaddress.AddressValueError:
            console.print(f"[red]✗[/red] Invalid base IP address: {base_ip}")
            return
    else:
        # Database mode - get IP addresses from database
        ip_addresses = db.get_all_ip_addresses()
        if not ip_addresses:
            console.print("[yellow]No devices found in database. Use --count if you want to remove specific aliases.[/yellow]")
            return
        console.print(f"[yellow]Removing {len(ip_addresses)} IP aliases from database...[/yellow]")
        for ip in ip_addresses:
            console.print(f"  - {ip}")
    
    if remove_ip_aliases(ip_addresses):
        console.print(f"\n[green]✓[/green] Successfully removed IP aliases!")

# Docker Management Commands
@cli.command("create-devices")
@click.option('--count', default=3, help='Number of device containers to create')
@click.option('--prefix', default='kitchen', help='Device name prefix')
@click.option('--room', help='Room/group name for devices')
@click.option('--base-ip', default='172.25.0.100', help='Base IP address for devices')
@click.option('--force', is_flag=True, help='Overwrite existing devices and docker-compose.override.yml')
@click.option('--setup-ip-aliases', is_flag=True, help='Automatically set up IP aliases for direct access')
@click.pass_context
def create_devices(ctx, count, prefix, room, base_ip, force, setup_ip_aliases):
    """Create multiple device containers with database storage and docker-compose generation."""
    db = ctx.obj['db']
    generator = ctx.obj['generator']
    
    override_file = Path("docker-compose.override.yml")
    
    # Check for existing devices if not forcing
    existing_devices = db.list_devices()
    if existing_devices and not force:
        console.print(f"[yellow]Warning:[/yellow] {len(existing_devices)} devices already exist in database. Use --force to overwrite.")
        console.print("Existing devices:")
        for device in existing_devices:
            console.print(f"  - {device.name} ({device.id}) at {device.ip_address}")
        return
    
    console.print(f"[yellow]Creating {count} device containers with prefix '{prefix}'...[/yellow]")
    
    # Clear existing data if force is used
    if force and existing_devices:
        console.print("[yellow]Removing existing devices from database...[/yellow]")
        for device in existing_devices:
            db.delete_container(device.id)
            db.delete_device(device.id)
        console.print(f"[green]✓[/green] Cleared {len(existing_devices)} existing devices")
    
    # Create room if specified
    if room:
        if db.create_room(room, f"Auto-created room for {prefix} devices"):
            console.print(f"[green]✓[/green] Created room: {room}")
    
    # Parse base IP and create devices
    try:
        base_ip_obj = ipaddress.IPv4Address(base_ip)
        base_ip_int = int(base_ip_obj)
    except ipaddress.AddressValueError:
        console.print(f"[red]✗[/red] Invalid base IP address: {base_ip}")
        return
    
    created_devices = []
    ip_addresses = []
    
    for i in range(count):
        device_id = f"{prefix}_{i+1:03d}"
        device_name = device_id
        ip_address = str(ipaddress.IPv4Address(base_ip_int + i))
        host_port = 8081 + i
        service_name = f"device-{prefix}-{i+1:03d}"
        
        # Create device in database
        device = Device(
            id=device_id,
            name=device_name,
            room=room,
            device_type='switch',
            ip_address=ip_address,
            port=80,
            prefix=prefix,
            status='created'
        )
        
        if db.create_device(device):
            created_devices.append(device)
            ip_addresses.append(ip_address)
            
            # Create container mapping
            container = Container(
                device_id=device_id,
                container_name=f"tasmota-device-{device_name}",
                docker_service_name=service_name,
                host_port=host_port,
                device_name=device_name,
                ip_address=ip_address
            )
            
            if db.create_container(container):
                console.print(f"[green]✓[/green] Created device: {device_name} ({ip_address}:{host_port})")
            else:
                console.print(f"[red]✗[/red] Failed to create container mapping for {device_name}")
        else:
            console.print(f"[red]✗[/red] Failed to create device: {device_name}")
    
    if not created_devices:
        console.print("[red]✗[/red] No devices were created")
        return
    
    # Generate docker-compose.override.yml from database
    console.print(f"[yellow]Generating docker-compose.override.yml from database...[/yellow]")
    if generator.generate_override_file():
        console.print(f"[green]✓[/green] Generated {override_file} with {len(created_devices)} device services")
    else:
        console.print("[red]✗[/red] Failed to generate docker-compose.override.yml")
        return
    
    # Validate generated file
    if generator.validate_generated_file():
        console.print(f"[green]✓[/green] Docker-compose file validated successfully")
    
    # Setup IP aliases if requested
    if setup_ip_aliases:
        console.print(f"\n[yellow]Setting up IP aliases for direct access...[/yellow]")
        setup_success = setup_ip_aliases_func(ip_addresses)
        if setup_success:
            console.print(f"[green]✓[/green] IP aliases configured successfully!")
        else:
            console.print(f"[yellow]⚠[/yellow] Some IP aliases failed. You can run 'tasmota-sim setup-ip-aliases' later.")
    
    # Show summary
    console.print(f"\n[bold green]Created {len(created_devices)} devices:[/bold green]")
    console.print(f"[cyan]Device IDs:[/cyan] {prefix}_001 to {prefix}_{count:03d}")
    console.print(f"[cyan]IP Range:[/cyan] {ip_addresses[0]} to {ip_addresses[-1]}")
    console.print(f"[cyan]Web Ports:[/cyan] 8081 to {8080 + count}")
    if room:
        console.print(f"[cyan]Room:[/cyan] {room}")
    
    console.print("\n[yellow]Next steps:[/yellow]")
    if not setup_ip_aliases:
        console.print("1. Setup IP aliases: [cyan]tasmota-sim setup-ip-aliases[/cyan]")
        console.print("2. Start services: [cyan]docker-compose up -d[/cyan]")
    else:
        console.print("1. Start services: [cyan]docker-compose up -d[/cyan]")
    console.print("3. Test devices: [cyan]tasmota-sim status kitchen_001[/cyan]")
    console.print(f"4. Test web interface: [cyan]http://{ip_addresses[0]}/docs[/cyan]")
    console.print(f"5. Test direct IP access: [cyan]curl http://{ip_addresses[0]}[/cyan]")

@cli.command("docker-up")
@click.option('--detach', '-d', is_flag=True, default=True, help='Run containers in detached mode')
@click.option('--services-only', is_flag=True, help='Start only RabbitMQ service (no devices)')
def docker_up(detach, services_only):
    """Start Docker services."""
    console.print("[yellow]Starting Docker services...[/yellow]")
    
    try:
        # Always start base services first
        services_cmd = ['docker-compose', '-f', 'docker-compose.services.yml', 'up']
        if detach:
            services_cmd.append('-d')
            
        result = subprocess.run(services_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("[green]✓[/green] RabbitMQ service started")
            
            if not services_only:
                # Check if override file exists
                override_file = Path("docker-compose.override.yml")
                if override_file.exists():
                    console.print("[yellow]Starting device containers...[/yellow]")
                    
                    override_cmd = ['docker-compose', '-f', 'docker-compose.override.yml', 'up']
                    if detach:
                        override_cmd.append('-d')
                    
                    result = subprocess.run(override_cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        console.print("[green]✓[/green] Device containers started")
                    else:
                        console.print(f"[red]✗[/red] Failed to start device containers: {result.stderr}")
                else:
                    console.print("[yellow]No device containers configured. Use 'create-devices' first.[/yellow]")
            
        else:
            console.print(f"[red]✗[/red] Failed to start services: {result.stderr}")
            
    except FileNotFoundError:
        console.print("[red]✗[/red] docker-compose not found. Please install Docker Compose.")
    except Exception as e:
        console.print(f"[red]✗[/red] Error starting Docker services: {e}")

@cli.command("docker-down")
@click.option('--volumes', '-v', is_flag=True, help='Remove volumes as well')
def docker_down(volumes):
    """Stop Docker services."""
    console.print("[yellow]Stopping Docker services...[/yellow]")
    
    try:
        # Stop override containers first
        override_file = Path("docker-compose.override.yml")
        if override_file.exists():
            cmd = ['docker-compose', '-f', 'docker-compose.override.yml', 'down']
            if volumes:
                cmd.append('-v')
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                console.print("[green]✓[/green] Device containers stopped")
            else:
                console.print(f"[yellow]Warning:[/yellow] {result.stderr}")
        
        # Stop services
        cmd = ['docker-compose', '-f', 'docker-compose.services.yml', 'down']
        if volumes:
            cmd.append('-v')
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("[green]✓[/green] All services stopped")
            if volumes:
                console.print("[green]✓[/green] Volumes removed")
        else:
            console.print(f"[red]✗[/red] Error stopping services: {result.stderr}")
            
    except Exception as e:
        console.print(f"[red]✗[/red] Error stopping Docker services: {e}")

@cli.command("list-devices")
@click.option('--status', is_flag=True, help='Show running status')
@click.option('--room', help='Filter by room')
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.pass_context
def list_devices(ctx, status, room, output_json):
    """List devices from database."""
    import json
    
    db = ctx.obj['db']
    
    try:
        # Get devices from database
        devices = db.list_devices(room=room)
        
        if not devices:
            if room:
                console.print(f"[yellow]No devices found in room '{room}'[/yellow]")
            else:
                console.print("[yellow]No devices found in database. Use 'create-devices' first.[/yellow]")
            return
        
        if output_json:
            # Output as JSON
            device_data = []
            for device in devices:
                device_dict = {
                    'id': device.id,
                    'name': device.name,
                    'room': device.room,
                    'device_type': device.device_type,
                    'ip_address': device.ip_address,
                    'port': device.port,
                    'status': device.status,
                    'created_at': device.created_at,
                    'last_seen': device.last_seen
                }
                device_data.append(device_dict)
            
            print(json.dumps(device_data, indent=2))
            return
        
        # Display as table
        console.print(f"[green]Devices in Database ({len(devices)} total):[/green]")
        
        table = Table()
        table.add_column("Device ID")
        table.add_column("Name")
        table.add_column("Room")
        table.add_column("Type")
        table.add_column("IP Address")
        table.add_column("Status")
        table.add_column("Created")
        
        for device in devices:
            # Color code status
            status_color = {
                'online': 'green',
                'offline': 'red',
                'created': 'yellow',
                'unknown': 'dim'
            }.get(device.status, 'white')
            
            table.add_row(
                device.id,
                device.name,
                device.room or '-',
                device.device_type,
                device.ip_address or '-',
                f"[{status_color}]{device.status}[/{status_color}]",
                device.created_at[:19] if device.created_at else '-'  # Remove microseconds
            )
        
        console.print(table)
        
        # Show container status if requested
        if status:
            console.print("\n[green]Container Status:[/green]")
            containers = db.get_containers()
            
            if containers:
                container_table = Table()
                container_table.add_column("Service Name")
                container_table.add_column("Container Name")
                container_table.add_column("Host Port")
                container_table.add_column("Docker Status")
                
                for container in containers:
                    # Check Docker container status
                    try:
                        result = subprocess.run(['docker', 'ps', '-a', '--filter', f'name={container.container_name}', '--format', 'table {{.Status}}'], 
                                              capture_output=True, text=True)
                        docker_status = "Unknown"
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')
                            if len(lines) > 1:
                                docker_status = lines[1]
                    except:
                        docker_status = "Error"
                    
                    container_table.add_row(
                        container.docker_service_name,
                        container.container_name,
                        str(container.host_port),
                        docker_status
                    )
                
                console.print(container_table)
            else:
                console.print("[yellow]No containers configured[/yellow]")
                
    except Exception as e:
        console.print(f"[red]✗[/red] Error listing devices: {e}")


# Database management commands
@cli.command("db-stats")
@click.pass_context
def db_stats(ctx):
    """Show database statistics."""
    db = ctx.obj['db']
    
    try:
        stats = db.get_database_stats()
        
        console.print("[green]Database Statistics:[/green]")
        
        table = Table()
        table.add_column("Category")
        table.add_column("Count")
        
        table.add_row("Total Devices", str(stats.get('total_devices', 0)))
        table.add_row("Total Containers", str(stats.get('total_containers', 0)))
        table.add_row("Total Rooms", str(stats.get('total_rooms', 0)))
        table.add_row("Status Entries", str(stats.get('total_status_entries', 0)))
        
        # Device status breakdown
        for key, value in stats.items():
            if key.startswith('devices_'):
                status = key.replace('devices_', '')
                table.add_row(f"Devices ({status})", str(value))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error getting database stats: {e}")


@cli.command("regenerate-compose")
@click.pass_context
def regenerate_compose(ctx):
    """Regenerate docker-compose.override.yml from database."""
    db = ctx.obj['db']
    generator = ctx.obj['generator']
    
    try:
        containers = db.get_containers()
        if not containers:
            console.print("[yellow]No containers found in database. Use 'create-devices' first.[/yellow]")
            return
        
        console.print(f"[yellow]Regenerating docker-compose.override.yml from {len(containers)} database entries...[/yellow]")
        
        if generator.generate_override_file():
            console.print(f"[green]✓[/green] Successfully regenerated docker-compose.override.yml")
            
            if generator.validate_generated_file():
                console.print(f"[green]✓[/green] Generated file validated successfully")
        else:
            console.print("[red]✗[/red] Failed to regenerate docker-compose.override.yml")
            
    except Exception as e:
        console.print(f"[red]✗[/red] Error regenerating compose file: {e}")


@cli.command("sync-database")
@click.option('--compose-file', default='docker-compose.override.yml', help='Docker compose file to sync from')
@click.pass_context
def sync_database(ctx, compose_file):
    """Sync database with existing docker-compose file (for migration)."""
    db = ctx.obj['db']
    generator = ctx.obj['generator']
    
    try:
        console.print(f"[yellow]Syncing database with {compose_file}...[/yellow]")
        
        if generator.sync_database_with_compose_file(compose_file):
            console.print(f"[green]✓[/green] Successfully synced database with compose file")
            
            # Show stats after sync
            stats = db.get_database_stats()
            console.print(f"[cyan]Database now contains {stats.get('total_devices', 0)} devices and {stats.get('total_containers', 0)} containers[/cyan]")
        else:
            console.print("[red]✗[/red] Failed to sync database")
            
    except Exception as e:
        console.print(f"[red]✗[/red] Error syncing database: {e}")


@cli.command("delete-device")
@click.argument('device_id')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def delete_device(ctx, device_id, force):
    """Delete a device from database and regenerate compose file."""
    db = ctx.obj['db']
    generator = ctx.obj['generator']
    
    try:
        # Check if device exists
        device = db.get_device(device_id)
        if not device:
            console.print(f"[red]✗[/red] Device '{device_id}' not found in database")
            return
        
        # Confirm deletion
        if not force:
            console.print(f"[yellow]About to delete device:[/yellow]")
            console.print(f"  ID: {device.id}")
            console.print(f"  Name: {device.name}")
            console.print(f"  IP: {device.ip_address}")
            console.print(f"  Room: {device.room or 'None'}")
            
            if not click.confirm("Are you sure you want to delete this device?"):
                console.print("[yellow]Deletion cancelled[/yellow]")
                return
        
        # Delete container mapping first
        if db.delete_container(device_id):
            console.print(f"[green]✓[/green] Removed container mapping for {device_id}")
        
        # Delete device
        if db.delete_device(device_id):
            console.print(f"[green]✓[/green] Deleted device {device_id}")
            
            # Regenerate compose file
            console.print("[yellow]Regenerating docker-compose.override.yml...[/yellow]")
            if generator.generate_override_file():
                console.print(f"[green]✓[/green] Updated docker-compose.override.yml")
            else:
                console.print("[yellow]⚠[/yellow] Failed to regenerate compose file")
        else:
            console.print(f"[red]✗[/red] Failed to delete device {device_id}")
            
    except Exception as e:
        console.print(f"[red]✗[/red] Error deleting device: {e}")


@cli.command("list-rooms")
@click.pass_context
def list_rooms(ctx):
    """List all rooms and their device counts."""
    db = ctx.obj['db']
    
    try:
        rooms = db.list_rooms()
        
        if not rooms:
            console.print("[yellow]No rooms found in database[/yellow]")
            return
        
        console.print(f"[green]Rooms in Database ({len(rooms)} total):[/green]")
        
        table = Table()
        table.add_column("Room Name")
        table.add_column("Description")
        table.add_column("Device Count")
        table.add_column("Created")
        
        for room in rooms:
            table.add_row(
                room['name'],
                room['description'] or '-',
                str(room['device_count']),
                room['created_at'][:19] if room['created_at'] else '-'
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error listing rooms: {e}")

@cli.command("docker-logs")
@click.argument('service', required=False)
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--tail', default=50, help='Number of lines to show from end of logs')
@click.option('--all', is_flag=True, help='Show logs for all services')
def docker_logs(service, follow, tail, all):
    """Show Docker service logs."""
    try:
        if all:
            # Show logs for all services
            console.print("[yellow]Showing logs for all services...[/yellow]")
            cmd = ['docker-compose', '-f', 'docker-compose.services.yml']
            
            override_file = Path("docker-compose.override.yml")
            if override_file.exists():
                cmd.extend(['-f', 'docker-compose.override.yml'])
            
            cmd.append('logs')
            if follow:
                cmd.append('-f')
            cmd.extend(['--tail', str(tail)])
            
        elif service:
            # Show logs for specific service
            console.print(f"[yellow]Showing logs for {service}...[/yellow]")
            cmd = ['docker-compose', '-f', 'docker-compose.services.yml']
            
            override_file = Path("docker-compose.override.yml")
            if override_file.exists():
                cmd.extend(['-f', 'docker-compose.override.yml'])
                
            cmd.append('logs')
            if follow:
                cmd.append('-f')
            cmd.extend(['--tail', str(tail), service])
        else:
            console.print("[yellow]Showing logs for RabbitMQ...[/yellow]")
            cmd = ['docker-compose', '-f', 'docker-compose.services.yml', 'logs']
            if follow:
                cmd.append('-f')
            cmd.extend(['--tail', str(tail), 'rabbitmq'])
        
        if follow:
            console.print("[dim]Press Ctrl+C to stop following logs[/dim]")
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped following logs[/yellow]")
    except Exception as e:
        console.print(f"[red]✗[/red] Error showing logs: {e}")

@cli.command("docker-restart")
@click.argument('service', required=False)
@click.option('--all', is_flag=True, help='Restart all services')
def docker_restart(service, all):
    """Restart Docker services."""
    try:
        if all:
            console.print("[yellow]Restarting all services...[/yellow]")
            
            # Restart services
            cmd = ['docker-compose', '-f', 'docker-compose.services.yml', 'restart']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print("[green]✓[/green] Services restarted")
            else:
                console.print(f"[red]✗[/red] Error restarting services: {result.stderr}")
            
            # Restart devices if they exist
            override_file = Path("docker-compose.override.yml")
            if override_file.exists():
                cmd = ['docker-compose', '-f', 'docker-compose.override.yml', 'restart']
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    console.print("[green]✓[/green] Device containers restarted")
                else:
                    console.print(f"[red]✗[/red] Error restarting devices: {result.stderr}")
                    
        elif service:
            console.print(f"[yellow]Restarting {service}...[/yellow]")
            
            # Try services file first
            cmd = ['docker-compose', '-f', 'docker-compose.services.yml', 'restart', service]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Try override file
                override_file = Path("docker-compose.override.yml")
                if override_file.exists():
                    cmd = ['docker-compose', '-f', 'docker-compose.override.yml', 'restart', service]
                    result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print(f"[green]✓[/green] {service} restarted")
            else:
                console.print(f"[red]✗[/red] Error restarting {service}: {result.stderr}")
        else:
            console.print("[yellow]Restarting RabbitMQ...[/yellow]")
            cmd = ['docker-compose', '-f', 'docker-compose.services.yml', 'restart', 'rabbitmq']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print("[green]✓[/green] RabbitMQ restarted")
            else:
                console.print(f"[red]✗[/red] Error restarting RabbitMQ: {result.stderr}")
                
    except Exception as e:
        console.print(f"[red]✗[/red] Error restarting service: {e}")

@cli.command("docker-clean")
@click.option('--force', is_flag=True, help='Force removal without confirmation')
def docker_clean(force):
    """Clean up unused Docker resources."""
    try:
        if not force:
            console.print("[yellow]This will remove:[/yellow]")
            console.print("- Stopped containers")
            console.print("- Unused networks")
            console.print("- Dangling images")
            
            if not click.confirm("Continue?"):
                console.print("[yellow]Cancelled[/yellow]")
                return
        
        console.print("[yellow]Cleaning up Docker resources...[/yellow]")
        
        # Remove stopped containers
        result = subprocess.run(['docker', 'container', 'prune', '-f'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[green]✓[/green] Removed stopped containers")
        
        # Remove unused networks
        result = subprocess.run(['docker', 'network', 'prune', '-f'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[green]✓[/green] Removed unused networks")
        
        # Remove dangling images
        result = subprocess.run(['docker', 'image', 'prune', '-f'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[green]✓[/green] Removed dangling images")
        
        console.print("[green]✓[/green] Docker cleanup completed")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Error during cleanup: {e}")

@cli.command()
def docker_status():
    """Show Docker service status."""
    try:
        console.print("[green]Docker Services Status:[/green]")
        
        # Check services
        result = subprocess.run(['docker-compose', '-f', 'docker-compose.services.yml', 'ps'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            console.print("\n[cyan]Core Services:[/cyan]")
            console.print(result.stdout)
        
        # Check devices if override exists
        override_file = Path("docker-compose.override.yml")
        if override_file.exists():
            result = subprocess.run(['docker-compose', '-f', 'docker-compose.override.yml', 'ps'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                console.print("\n[cyan]Device Containers:[/cyan]")
                console.print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗[/red] Failed to get Docker status: {e}")

if __name__ == '__main__':
    cli() 