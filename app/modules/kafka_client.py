import json
from typing import Any, Dict, Optional

from confluent_kafka import Producer
from confluent_kafka.error import KafkaError

from app.modules.logger import bastion_logger
from settings import KafkaSettings, get_settings


class KafkaClient:
    """
    Client for working with Apache Kafka.

    Provides functionality for connecting to Kafka and sending messages
    to a topic defined in configuration. Supports automatic reconnection
    and error handling with detailed logging.

    Attributes:
        _producer (KafkaProducer): Kafka producer for sending messages
        _kafka_settings (KafkaSettings): Kafka connection settings
        topic (str): Topic name for sending messages
    """

    def __init__(self) -> None:
        """
        Initialize Kafka client with connection settings.

        Args:
            kafka_settings (KafkaSettings): Settings for connecting to Kafka
        """
        settings = get_settings()
        self._kafka_settings: KafkaSettings = settings.KAFKA
        if self._kafka_settings and hasattr(self._kafka_settings, "topic"):
            self.topic = self._kafka_settings.topic
            self._producer = None
            self.connect()

    @property
    def producer(self) -> Producer:
        """
        Returns current Kafka producer.

        Returns:
            Producer: Kafka producer for sending messages

        Raises:
            AttributeError: If producer is not initialized
        """
        if self._producer is None:
            self.connect()
        return self._producer

    def connect(self) -> None:
        """
        Establishes connection to Kafka.

        Creates a new Kafka producer with security and connection settings.
        Logs the result of the connection operation.
        """
        try:
            config = {
                "bootstrap.servers": self._kafka_settings.bootstrap_servers,
                "security.protocol": self._kafka_settings.security_protocol.lower(),
            }

            # Add SASL settings if provided
            if self._kafka_settings.sasl_mechanism:
                config["sasl.mechanism"] = self._kafka_settings.sasl_mechanism
                if self._kafka_settings.sasl_username:
                    config["sasl.username"] = self._kafka_settings.sasl_username
                if self._kafka_settings.sasl_password:
                    config["sasl.password"] = self._kafka_settings.sasl_password

            self._producer = Producer(config)
            bastion_logger.info(f"Successfully connected to Kafka at {self._kafka_settings.bootstrap_servers}")

        except Exception as e:
            bastion_logger.error(f"Failed to connect to Kafka: {e}")

    def disconnect(self) -> None:
        """
        Closes connection to Kafka.

        Closes producer and cleans up resources.
        """
        if self._producer:
            try:
                self._producer.close()
                bastion_logger.info("Kafka connection closed")
            except Exception as e:
                bastion_logger.error(f"Error closing Kafka connection: {e}")
            finally:
                self._producer = None

    def send_message(self, message: Dict[str, Any], key: Optional[str] = None) -> bool:
        """
        Sends message to the specified topic.

        Args:
            message (Dict[str, Any]): Message to send
            key (Optional[str]): Key for partitioning (optional)

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if not self.producer:
            bastion_logger.error("Kafka producer is not initialized")
            return False

        try:
            # Serialize message to JSON
            message_bytes = json.dumps(message).encode("utf-8")
            key_bytes = key.encode("utf-8") if key else None

            # Send message
            self._producer.produce(
                topic=self.topic, value=message_bytes, key=key_bytes, callback=self._delivery_callback
            )

            # Flush to ensure message is sent
            self._producer.flush(timeout=10)

            bastion_logger.info(f"Message sent to topic '{self.topic}'")
            return True

        except KafkaError as e:
            bastion_logger.error(f"Kafka error while sending message: {e}")
            return False
        except Exception as e:
            bastion_logger.error(f"Unexpected error while sending message: {e}")
            return False

    def _delivery_callback(self, err, msg):
        """
        Callback for message delivery confirmation.

        Args:
            err: Error if delivery failed, None if successful
            msg: Message metadata
        """
        if err is not None:
            bastion_logger.error(f"Message delivery failed: {err}")
        else:
            bastion_logger.info(
                f"Message delivered to topic '{msg.topic()}' " f"partition {msg.partition()} " f"offset {msg.offset()}"
            )


KAFKA_CLIENT = KafkaClient()
