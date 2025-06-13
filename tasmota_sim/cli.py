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

from .messaging import AsyncTasmotaMessaging

console = Console()

# Async wrapper
def async_command(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

@click.group()
def cli():
    """Tasmota Device Simulator CLI"""
    pass

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
@click.option('--count', default=3, help='Number of IP aliases to create (starting from 172.25.0.100)')
@click.option('--base-ip', default='172.25.0.100', help='Base IP address to start from')
def setup_ip_aliases_cmd(count, base_ip):
    """Set up IP aliases for direct device access."""
    # Parse base IP and generate list
    ip_parts = base_ip.split('.')
    base_num = int(ip_parts[3])
    ip_prefix = '.'.join(ip_parts[:3])
    
    ip_addresses = [f"{ip_prefix}.{base_num + i}" for i in range(count)]
    
    if setup_ip_aliases_func(ip_addresses):
        console.print(f"\n[green]✓[/green] Successfully set up all IP aliases!")
        console.print("[yellow]You can now start containers and access devices directly.[/yellow]")
    else:
        console.print(f"\n[red]✗[/red] Some IP aliases failed to set up. Check permissions.")

@cli.command("remove-ip-aliases") 
@click.option('--count', default=3, help='Number of IP aliases to remove (starting from 172.25.0.100)')
@click.option('--base-ip', default='172.25.0.100', help='Base IP address to start from')
def remove_ip_aliases_cmd(count, base_ip):
    """Remove IP aliases for device access."""
    # Parse base IP and generate list
    ip_parts = base_ip.split('.')
    base_num = int(ip_parts[3])
    ip_prefix = '.'.join(ip_parts[:3])
    
    ip_addresses = [f"{ip_prefix}.{base_num + i}" for i in range(count)]
    
    if remove_ip_aliases(ip_addresses):
        console.print(f"\n[green]✓[/green] Successfully removed IP aliases!")

# Docker Management Commands
@cli.command("create-devices")
@click.option('--count', default=3, help='Number of device containers to create')
@click.option('--prefix', default='kitchen', help='Device name prefix')
@click.option('--force', is_flag=True, help='Overwrite existing docker-compose.override.yml')
@click.option('--setup-ip-aliases', is_flag=True, help='Automatically set up IP aliases for direct access')
def create_devices(count, prefix, force, setup_ip_aliases):
    """Create multiple device containers with optional IP alias setup."""
    override_file = Path("docker-compose.override.yml")
    
    if override_file.exists() and not force:
        console.print(f"[yellow]Warning:[/yellow] {override_file} already exists. Use --force to overwrite.")
        return
    
    console.print(f"[yellow]Creating {count} device containers with prefix '{prefix}'...[/yellow]")
    
    # Generate docker-compose override file
    services = {}
    base_ip = 100
    ip_addresses = []
    
    for i in range(1, count + 1):
        device_id = f"{prefix}_{i:03d}"
        container_name = f"tasmota-device-{i}"
        ip_address = f"172.25.0.{base_ip + i - 1}"
        ip_addresses.append(ip_address)
        
        services[container_name] = {
            'build': '.',
            'container_name': container_name,
            'command': 'python3 /app/run_device.py',
            'environment': [
                'RABBITMQ_HOST=172.25.0.10',
                'RABBITMQ_USER=admin',
                'RABBITMQ_PASS=admin123',
                f'DEVICE_ID={device_id}',
                f'DEVICE_NAME={device_id}',
                f'IP_ADDRESS={ip_address}',
                f'CONTAINER_IP={ip_address}',
                'DEFAULT_USERNAME=admin',
                'DEFAULT_PASSWORD=test1234!',
                'PORT=80'
            ],
            'networks': {
                'tasmota_net': {
                    'ipv4_address': ip_address
                }
            },
            'ports': [
                f"{ip_address}:80:80",  # Direct IP access
                f"{8080 + i}:80"        # Localhost port access
            ],
            'restart': 'unless-stopped'
        }
    
    # Create complete docker-compose override structure  
    docker_compose = {
        'networks': {
            'tasmota_net': {
                'driver': 'bridge',
                'ipam': {
                    'config': [
                        {'subnet': '172.25.0.0/16'}
                    ]
                }
            }
        },
        'services': services
    }
    
    # Write the file
    try:
        with open(override_file, 'w') as f:
            yaml.dump(docker_compose, f, default_flow_style=False, indent=2)
        
        console.print(f"[green]✓[/green] Created {override_file} with {count} device containers")
        console.print(f"[cyan]Device IDs:[/cyan] {prefix}_001 to {prefix}_{count:03d}")
        console.print(f"[cyan]IP Range:[/cyan] 172.25.0.{base_ip} to 172.25.0.{base_ip + count - 1}")
        console.print(f"[cyan]Web Ports:[/cyan] 8081 to {8080 + count}")
        
        # Setup IP aliases if requested
        if setup_ip_aliases:
            console.print(f"\n[yellow]Setting up IP aliases for direct access...[/yellow]")
            setup_success = setup_ip_aliases_func(ip_addresses)
            if setup_success:
                console.print(f"[green]✓[/green] IP aliases configured successfully!")
            else:
                console.print(f"[yellow]⚠[/yellow] Some IP aliases failed. You can run 'tasmota-sim setup-ip-aliases --count {count}' later.")
        
        console.print("\n[yellow]Next steps:[/yellow]")
        if not setup_ip_aliases:
            console.print(f"1. Setup IP aliases: [cyan]tasmota-sim setup-ip-aliases --count {count}[/cyan]")
            console.print("2. Start services: [cyan]docker-compose up -d[/cyan]")
        else:
            console.print("1. Start services: [cyan]docker-compose up -d[/cyan]")
        console.print("3. Test devices: [cyan]tasmota-sim status kitchen_001[/cyan]")
        console.print(f"4. Test web interface: [cyan]http://{ip_addresses[0]}/docs[/cyan]")
        console.print(f"5. Test direct IP access: [cyan]curl http://{ip_addresses[0]}[/cyan]")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to create {override_file}: {e}")

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
def list_devices(status):
    """List device containers."""
    try:
        if status:
            # Show container status
            result = subprocess.run(['docker', 'ps', '-a', '--filter', 'name=tasmota-device'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                console.print("[green]Device Container Status:[/green]")
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    # Create table
                    table = Table()
                    headers = lines[0].split()
                    for header in headers:
                        table.add_column(header)
                    
                    for line in lines[1:]:
                        if 'tasmota-device' in line:
                            table.add_row(*line.split())
                    
                    console.print(table)
                else:
                    console.print("[yellow]No device containers found[/yellow]")
            else:
                console.print(f"[red]✗[/red] Error getting container status: {result.stderr}")
        else:
            # List configured devices from override file
            override_file = Path("docker-compose.override.yml")
            if override_file.exists():
                with open(override_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                console.print("[green]Configured Device Containers:[/green]")
                services = config.get('services', {})
                
                table = Table()
                table.add_column("Container Name")
                table.add_column("Device ID")
                table.add_column("IP Address")
                
                for service_name, service_config in services.items():
                    if 'tasmota-device' in service_name:
                        env_vars = service_config.get('environment', [])
                        device_id = ip_address = "Unknown"
                        
                        for env in env_vars:
                            if env.startswith('DEVICE_ID='):
                                device_id = env.split('=', 1)[1]
                            elif env.startswith('IP_ADDRESS='):
                                ip_address = env.split('=', 1)[1]
                        
                        table.add_row(service_name, device_id, ip_address)
                
                console.print(table)
            else:
                console.print("[yellow]No devices configured. Use 'create-devices' first.[/yellow]")
                
    except Exception as e:
        console.print(f"[red]✗[/red] Error listing devices: {e}")

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