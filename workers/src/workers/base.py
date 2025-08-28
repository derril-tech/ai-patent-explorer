"""Base worker class for all patent processing workers."""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional
from abc import ABC, abstractmethod

import nats
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class BaseWorker(ABC):
    """Base class for all workers in the patent processing pipeline."""

    def __init__(self):
        self.nats_client: Optional[nats.NATS] = None
        self.running = False
        self.subscriptions = []

    async def connect(self):
        """Connect to NATS and other services."""
        try:
            # Connect to NATS
            self.nats_client = await nats.connect(
                servers=["nats://localhost:4222"],
                reconnect_time_wait=3,
                max_reconnect_attempts=5
            )
            logger.info("Connected to NATS")

        except Exception as e:
            logger.error("Failed to connect to NATS", error=str(e))
            raise

    async def disconnect(self):
        """Disconnect from NATS and other services."""
        try:
            if self.nats_client:
                await self.nats_client.close()
                logger.info("Disconnected from NATS")
        except Exception as e:
            logger.error("Error disconnecting from NATS", error=str(e))

    async def subscribe(self, subject: str, handler: Callable):
        """Subscribe to a NATS subject."""
        try:
            subscription = await self.nats_client.subscribe(subject, cb=handler)
            self.subscriptions.append(subscription)
            logger.info("Subscribed to subject", subject=subject)
        except Exception as e:
            logger.error("Failed to subscribe", subject=subject, error=str(e))
            raise

    async def publish(self, subject: str, data: Dict[str, Any]):
        """Publish a message to a NATS subject."""
        try:
            await self.nats_client.publish(subject, data)
            logger.debug("Published message", subject=subject)
        except Exception as e:
            logger.error("Failed to publish message", subject=subject, error=str(e))
            raise

    async def start(self):
        """Start the worker."""
        try:
            await self.connect()
            self.running = True
            logger.info("Worker started")
        except Exception as e:
            logger.error("Failed to start worker", error=str(e))
            raise

    async def stop(self):
        """Stop the worker."""
        try:
            self.running = False
            
            # Unsubscribe from all subjects
            for subscription in self.subscriptions:
                await subscription.unsubscribe()
            
            await self.disconnect()
            logger.info("Worker stopped")
        except Exception as e:
            logger.error("Error stopping worker", error=str(e))

    @abstractmethod
    async def process_message(self, message: BaseModel) -> BaseModel:
        """Process a message. Must be implemented by subclasses."""
        pass

    async def run(self):
        """Run the worker indefinitely."""
        try:
            await self.start()
            
            # Keep the worker running
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error("Worker error", error=str(e))
        finally:
            await self.stop()
