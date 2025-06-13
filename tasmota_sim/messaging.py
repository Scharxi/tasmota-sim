"""
Asynchronous RabbitMQ messaging module using aio-pika for better concurrency handling.
"""

import asyncio
import json
import logging
from typing import Callable, Optional, Any
from datetime import datetime

import aio_pika
from aio_pika import Message, ExchangeType, DeliveryMode
from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractExchange, AbstractQueue

from .models import StatusResponse, TelemetryData, CommandMessage

logger = logging.getLogger(__name__)

class AsyncTasmotaMessaging:
    """Asynchronous RabbitMQ messaging for Tasmota devices."""

    def __init__(self, host: str = "localhost", user: str = "guest", password: str = "guest"):
        self.host = host
        self.user = user
        self.password = password
        
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        
        # Exchanges
        self.command_exchange: Optional[AbstractExchange] = None
        self.status_exchange: Optional[AbstractExchange] = None
        self.telemetry_exchange: Optional[AbstractExchange] = None
        
        # Device queue
        self.device_queue: Optional[AbstractQueue] = None
        self._is_consuming = False

    async def connect(self) -> bool:
        """Establish connection to RabbitMQ with retry logic."""
        max_retries = 10
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                # Build connection URL
                url = f"amqp://{self.user}:{self.password}@{self.host}/"
                
                # Create connection with robust parameters
                self.connection = await aio_pika.connect_robust(
                    url,
                    client_properties={"connection_name": f"tasmota-device-{datetime.now().isoformat()}"},
                    heartbeat=300,
                    blocked_connection_timeout=60,
                )
                
                # Create channel
                self.channel = await self.connection.channel()
                await self.channel.set_qos(prefetch_count=10)
                
                # Setup exchanges and queues
                await self._setup_exchanges_and_queues()
                
                logger.info(f"Connected to RabbitMQ at {self.host} (attempt {attempt + 1})")
                return True
                
            except Exception as e:
                logger.warning(f"Failed to connect to RabbitMQ (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, 10)  # Exponential backoff
                else:
                    logger.error(f"Failed to connect to RabbitMQ after {max_retries} attempts")
                    return False

    async def _setup_exchanges_and_queues(self):
        """Setup RabbitMQ exchanges and queues."""
        if not self.channel:
            raise RuntimeError("No channel available")

        # Declare exchanges
        self.command_exchange = await self.channel.declare_exchange(
            "tasmota.commands", 
            ExchangeType.TOPIC,
            durable=True
        )
        
        self.status_exchange = await self.channel.declare_exchange(
            "tasmota.status", 
            ExchangeType.TOPIC,
            durable=True
        )
        
        self.telemetry_exchange = await self.channel.declare_exchange(
            "tasmota.telemetry", 
            ExchangeType.TOPIC,
            durable=True
        )

        logger.debug("RabbitMQ exchanges and queues setup completed")

    async def setup_device_queue(self, device_id: str, callback):
        """Setup device-specific command queue."""
        if not self.channel:
            logger.error("Not connected to RabbitMQ")
            return False

        try:
            # Declare device queue
            queue_name = f"device.{device_id}.commands"
            self.device_queue = await self.channel.declare_queue(
                queue_name,
                durable=True,
                auto_delete=False
            )

            # Bind queue to command exchange
            routing_key = f"device.command.{device_id}"
            await self.device_queue.bind(self.command_exchange, routing_key)

            logger.info(f"Setup command queue for device {device_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to setup device queue for {device_id}: {e}")
            return False

    async def start_consuming(self, callback):
        """Start consuming messages from the device queue."""
        if not self.device_queue:
            logger.error("Device queue not setup")
            return

        async def message_handler(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    # Parse command message
                    data = json.loads(message.body.decode())
                    command = CommandMessage(**data)
                    
                    # Check if callback is async or sync
                    if asyncio.iscoroutinefunction(callback):
                        await callback(command)
                    else:
                        # Execute sync callback in thread pool to avoid blocking
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(None, callback, command)
                    
                    logger.debug(f"Processed command: {command.command}")
                    
                except Exception as e:
                    logger.error(f"Error processing command message: {e}")

        try:
            # Start consuming
            await self.device_queue.consume(message_handler)
            self._is_consuming = True
            logger.info("Started consuming messages")
            
        except Exception as e:
            logger.error(f"Failed to start consuming: {e}")

    async def publish_status(self, device_id: str, status: StatusResponse) -> bool:
        """Publish device status update."""
        if not self.status_exchange:
            logger.error("Not connected to RabbitMQ")
            return False

        routing_key = f"device.status.{device_id}"
        
        try:
            message = Message(
                status.model_dump_json().encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                content_encoding="utf-8",
                timestamp=datetime.now()
            )
            
            await self.status_exchange.publish(message, routing_key)
            logger.debug(f"Published status for device {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish status: {e}")
            return False

    async def publish_telemetry(self, device_id: str, telemetry: TelemetryData) -> bool:
        """Publish device telemetry data."""
        if not self.telemetry_exchange:
            logger.error("Not connected to RabbitMQ")
            return False

        routing_key = f"device.telemetry.{device_id}"
        
        try:
            message = Message(
                telemetry.model_dump_json().encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                content_encoding="utf-8",
                timestamp=datetime.now()
            )
            
            await self.telemetry_exchange.publish(message, routing_key)
            logger.debug(f"Published telemetry for device {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish telemetry: {e}")
            return False

    async def send_command(self, device_id: str, command: str, payload: Optional[dict] = None) -> bool:
        """Send command to a specific device."""
        if not self.command_exchange:
            logger.error("Not connected to RabbitMQ")
            return False

        routing_key = f"device.command.{device_id}"
        
        try:
            command_msg = CommandMessage(
                device_id=device_id,
                command=command,
                payload=payload or {},
                timestamp=datetime.now().isoformat()
            )
            
            message = Message(
                command_msg.model_dump_json().encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                content_type="application/json",
                content_encoding="utf-8",
                timestamp=datetime.now()
            )
            
            await self.command_exchange.publish(message, routing_key)
            logger.info(f"Sent command '{command}' to device {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            return False

    async def query_status(self, device_id: str) -> bool:
        """Query device status."""
        return await self.send_command(device_id, "status")

    async def query_energy(self, device_id: str) -> bool:
        """Query device energy data."""
        return await self.send_command(device_id, "energy")

    async def set_power(self, device_id: str, state: bool) -> bool:
        """Set device power state."""
        command = "power_on" if state else "power_off"
        return await self.send_command(device_id, command, {"state": state})

    async def setup_response_listener(self, callback: Callable[[str, str, dict], None]):
        """Setup listener for status and telemetry responses."""
        if not self.channel:
            logger.error("Not connected to RabbitMQ")
            return False

        try:
            # Create temporary queue for responses
            response_queue = await self.channel.declare_queue("", exclusive=True, auto_delete=True)
            
            # Bind to status and telemetry exchanges  
            await response_queue.bind(self.status_exchange, "#")
            await response_queue.bind(self.telemetry_exchange, "#")
            
            async def response_handler(message: aio_pika.IncomingMessage):
                try:
                    async with message.process():
                        data = json.loads(message.body.decode())
                        exchange_name = message.exchange if hasattr(message, 'exchange') and message.exchange else ""
                        if hasattr(exchange_name, 'name'):
                            exchange_name = exchange_name.name
                        routing_key = message.routing_key or ""
                        callback(routing_key, exchange_name, data)
                except Exception as e:
                    logger.error(f"Error processing response message: {e}")
            
            # Start consuming responses
            await response_queue.consume(response_handler)
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup response listener: {e}")
            return False

    async def close(self):
        """Close the RabbitMQ connection safely."""
        try:
            if self._is_consuming and self.device_queue:
                await self.device_queue.cancel()
                self._is_consuming = False
                
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("Closed RabbitMQ connection")
                
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")
        finally:
            self.connection = None
            self.channel = None
            self.command_exchange = None
            self.status_exchange = None
            self.telemetry_exchange = None
            self.device_queue = None

# Legacy compatibility wrapper for synchronous usage
class TasmotaMessaging:
    """Synchronous wrapper for backward compatibility."""
    
    def __init__(self, host: str = "localhost", user: str = "guest", password: str = "guest"):
        self.async_messaging = AsyncTasmotaMessaging(host, user, password)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
    def _ensure_loop(self):
        """Ensure we have an event loop."""
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
    
    def connect(self) -> bool:
        """Synchronous connect wrapper."""
        self._ensure_loop()
        return self._loop.run_until_complete(self.async_messaging.connect())
    
    def setup_device_queue(self, device_id: str, callback: Callable[[CommandMessage], None]) -> bool:
        """Synchronous setup device queue wrapper."""
        self._ensure_loop()
        return self._loop.run_until_complete(
            self.async_messaging.setup_device_queue(device_id, callback)
        )
    
    def start_consuming(self, callback: Callable[[CommandMessage], None]):
        """Synchronous start consuming wrapper."""
        self._ensure_loop()
        return self._loop.run_until_complete(
            self.async_messaging.start_consuming(callback)
        )
    
    def publish_status(self, device_id: str, status: StatusResponse) -> bool:
        """Synchronous publish status wrapper."""
        self._ensure_loop()
        return self._loop.run_until_complete(
            self.async_messaging.publish_status(device_id, status)
        )
    
    def publish_telemetry(self, device_id: str, telemetry: TelemetryData) -> bool:
        """Synchronous publish telemetry wrapper."""
        self._ensure_loop()
        return self._loop.run_until_complete(
            self.async_messaging.publish_telemetry(device_id, telemetry)
        )
    
    def send_command(self, device_id: str, command: str, payload: Optional[dict] = None) -> bool:
        """Synchronous send command wrapper."""
        self._ensure_loop()
        return self._loop.run_until_complete(
            self.async_messaging.send_command(device_id, command, payload)
        )
    
    def query_status(self, device_id: str) -> bool:
        """Synchronous query status wrapper."""
        self._ensure_loop()
        return self._loop.run_until_complete(self.async_messaging.query_status(device_id))
    
    def query_energy(self, device_id: str) -> bool:
        """Synchronous query energy wrapper."""
        self._ensure_loop()
        return self._loop.run_until_complete(self.async_messaging.query_energy(device_id))
    
    def set_power(self, device_id: str, state: bool) -> bool:
        """Synchronous set power wrapper."""
        self._ensure_loop()
        return self._loop.run_until_complete(self.async_messaging.set_power(device_id, state))
    
    def close(self):
        """Synchronous close wrapper."""
        self._ensure_loop()
        return self._loop.run_until_complete(self.async_messaging.close())

    @property
    def connection(self):
        """Backward compatibility property."""
        return self.async_messaging.connection
    
    @property
    def channel(self):
        """Backward compatibility property."""
        return self.async_messaging.channel 