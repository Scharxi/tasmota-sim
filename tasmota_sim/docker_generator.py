#!/usr/bin/env python3
"""
Docker Compose configuration generator for Tasmota Device Simulator.
Generates docker-compose.override.yml based on database entries.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List
from .database import TasmotaDatabase
from .models import DockerComposeService


class DockerComposeGenerator:
    """Generates docker-compose configuration from database."""
    
    def __init__(self, db: TasmotaDatabase):
        self.db = db
    
    def generate_override_file(self, output_path: str = "docker-compose.override.yml") -> bool:
        """Generate docker-compose.override.yml from database entries."""
        try:
            # Get all containers from database
            containers = self.db.get_containers()
            
            if not containers:
                print("No containers found in database. Creating minimal override file.")
                self._create_minimal_override(output_path)
                return True
            
            # Generate docker-compose structure
            compose_config = self._generate_compose_config(containers)
            
            # Write to file
            with open(output_path, 'w') as f:
                yaml.dump(compose_config, f, default_flow_style=False, indent=2)
            
            print(f"Generated {output_path} with {len(containers)} device services")
            return True
            
        except Exception as e:
            print(f"Error generating docker-compose override: {e}")
            return False
    
    def _generate_compose_config(self, containers) -> Dict[str, Any]:
        """Generate the complete docker-compose configuration."""
        services = {}
        
        # Add device services
        for container in containers:
            service = DockerComposeService(
                name=container.docker_service_name,
                device_id=container.device_id,
                ip_address=container.ip_address,
                host_port=container.host_port,
                environment={
                    "DEVICE_NAME": container.device_name or container.device_id
                }
            )
            services[container.docker_service_name] = service.to_compose_dict()
        
        return {
            "services": services,
            "networks": {
                "tasmota_net": {
                    "driver": "bridge",
                    "ipam": {
                        "config": [
                            {
                                "subnet": "172.25.0.0/16",
                                "gateway": "172.25.0.1"
                            }
                        ]
                    }
                }
            },
            "volumes": {
                "rabbitmq_data": None
            }
        }
    
    def _create_minimal_override(self, output_path: str):
        """Create minimal override file when no devices exist."""
        minimal_config = {
            "services": {},
            "networks": {
                "tasmota_net": {
                    "driver": "bridge",
                    "ipam": {
                        "config": [
                            {
                                "subnet": "172.25.0.0/16",
                                "gateway": "172.25.0.1"
                            }
                        ]
                    }
                }
            },
            "volumes": {
                "rabbitmq_data": None
            }
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(minimal_config, f, default_flow_style=False, indent=2)
    
    def validate_generated_file(self, file_path: str = "docker-compose.override.yml") -> bool:
        """Validate the generated docker-compose file."""
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Basic validation (version is no longer required)
            
            if 'services' not in config:
                print("Missing services in docker-compose file")
                return False
            
            if 'networks' not in config:
                print("Missing networks in docker-compose file")
                return False
            
            # Validate each service
            for service_name, service_config in config.get('services', {}).items():
                if not self._validate_service_config(service_name, service_config):
                    return False
            
            print(f"Docker-compose file {file_path} is valid")
            return True
            
        except Exception as e:
            print(f"Error validating docker-compose file: {e}")
            return False
    
    def _validate_service_config(self, service_name: str, config: Dict[str, Any]) -> bool:
        """Validate a single service configuration."""
        required_fields = ['image', 'container_name', 'environment', 'ports', 'networks']
        
        for field in required_fields:
            if field not in config:
                print(f"Service {service_name} missing required field: {field}")
                return False
        
        # Validate environment variables
        env = config.get('environment', {})
        required_env = ['DEVICE_ID', 'DEVICE_NAME', 'DEVICE_IP', 'AMQP_URL']
        
        for env_var in required_env:
            if env_var not in env:
                print(f"Service {service_name} missing required environment variable: {env_var}")
                return False
        
        # Validate ports format
        ports = config.get('ports', [])
        if not isinstance(ports, list) or len(ports) != 2:
            print(f"Service {service_name} has invalid ports configuration")
            return False
        
        # Validate network configuration
        networks = config.get('networks', {})
        if 'tasmota_net' not in networks:
            print(f"Service {service_name} missing tasmota_net configuration")
            return False
        
        return True
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services defined in database."""
        containers = self.db.get_containers()
        devices = self.db.list_devices()
        
        status = {
            'total_devices': len(devices),
            'total_containers': len(containers),
            'services': [],
            'ip_addresses': []
        }
        
        for container in containers:
            # Find corresponding device
            device = next((d for d in devices if d.id == container.device_id), None)
            
            service_info = {
                'service_name': container.docker_service_name,
                'device_id': container.device_id,
                'device_name': container.device_name,
                'ip_address': container.ip_address,
                'host_port': container.host_port,
                'device_status': device.status if device else 'unknown'
            }
            
            status['services'].append(service_info)
            if container.ip_address:
                status['ip_addresses'].append(container.ip_address)
        
        return status
    
    def sync_database_with_compose_file(self, compose_file: str = "docker-compose.override.yml") -> bool:
        """Sync database with existing docker-compose file (for migration)."""
        try:
            if not Path(compose_file).exists():
                print(f"Compose file {compose_file} does not exist")
                return False
            
            with open(compose_file, 'r') as f:
                config = yaml.safe_load(f)
            
            services = config.get('services', {})
            synced_count = 0
            
            for service_name, service_config in services.items():
                if not service_name.startswith('device-'):
                    continue  # Skip non-device services
                
                env = service_config.get('environment', {})
                
                # Extract device information
                device_id = env.get('DEVICE_ID')
                device_name = env.get('DEVICE_NAME', device_id)
                device_ip = env.get('DEVICE_IP')
                
                if not device_id:
                    continue
                
                # Extract host port from ports configuration
                ports = service_config.get('ports', [])
                host_port = None
                
                for port_mapping in ports:
                    if isinstance(port_mapping, str) and '127.0.0.1:' in port_mapping:
                        # Format: "127.0.0.1:8081:80"
                        host_port = int(port_mapping.split(':')[1])
                        break
                
                if not host_port:
                    continue
                
                # Create device in database if it doesn't exist
                from .models import Device, Container
                
                device = Device(
                    id=device_id,
                    name=device_name,
                    ip_address=device_ip,
                    status='unknown'
                )
                
                if self.db.create_device(device):
                    print(f"Created device: {device_name} ({device_id})")
                
                # Create container mapping
                container = Container(
                    device_id=device_id,
                    container_name=service_config.get('container_name', f'tasmota-device-{device_name}'),
                    docker_service_name=service_name,
                    host_port=host_port,
                    device_name=device_name,
                    ip_address=device_ip
                )
                
                if self.db.create_container(container):
                    print(f"Created container mapping: {service_name}")
                    synced_count += 1
            
            print(f"Synced {synced_count} services to database")
            return True
            
        except Exception as e:
            print(f"Error syncing database with compose file: {e}")
            return False 