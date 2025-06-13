#!/usr/bin/env python3
"""
Simple working CLI for Tasmota simulator.
"""

import click
import asyncio
import os
from rich.console import Console

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
            
            if wait_for_response:
                # Set up listener for response
                response_received = asyncio.Event()
                response_data = {}
                
                def response_handler(routing_key, exchange, data):
                    if data.get('device_id') == device_id and exchange == 'tasmota.status':
                        response_data.update(data)
                        response_received.set()
                
                # Start listening
                await messaging.setup_response_listener(response_handler)
            
            success = await messaging.send_command(device_id, 'status', {})
            
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
            
            if wait_for_response:
                # Set up listener for response
                response_received = asyncio.Event()
                response_data = {}
                
                def response_handler(routing_key, exchange, data):
                    if data.get('device_id') == device_id and exchange == 'tasmota.telemetry':
                        response_data.update(data)
                        response_received.set()
                
                # Start listening
                await messaging.setup_response_listener(response_handler)
            
            success = await messaging.send_command(device_id, 'energy', {})
            
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

@cli.command()
def docker_status():
    """Show Docker service status."""
    import subprocess
    try:
        result = subprocess.run(['docker-compose', 'ps'], 
                              capture_output=True, text=True, check=True)
        console.print("[green]Docker Services:[/green]")
        console.print(result.stdout)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗[/red] Failed to get Docker status: {e}")

if __name__ == '__main__':
    cli() 