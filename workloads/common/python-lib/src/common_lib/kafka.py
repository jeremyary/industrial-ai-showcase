# This project was developed with assistance from AI tools.
"""Thin wrappers around confluent-kafka with pydantic serialization."""

import json
from collections.abc import Iterator
from typing import TypeVar

from confluent_kafka import Consumer, KafkaError, KafkaException, Producer, TopicPartition
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class JsonProducer:
    """Wraps confluent_kafka.Producer with pydantic JSON serialization."""

    def __init__(
        self,
        bootstrap_servers: str,
        client_id: str,
        extra_config: dict[str, str | int | bool] | None = None,
    ) -> None:
        config: dict[str, str | int | bool] = {
            "bootstrap.servers": bootstrap_servers,
            "client.id": client_id,
            "enable.idempotence": True,
            "acks": "all",
            # Phase 1: gzip (natively decoded by kafkajs in the Console backend).
            # Phase 2 may revisit zstd once the Console migrates to a Node client
            # bundle that ships a working WASM zstd codec.
            "compression.type": "gzip",
        }
        if extra_config:
            config.update(extra_config)
        self._producer = Producer(config)

    def send(self, topic: str, key: str, value: BaseModel) -> None:
        self._producer.produce(
            topic=topic,
            key=key.encode("utf-8"),
            value=value.model_dump_json().encode("utf-8"),
        )
        self._producer.poll(0)

    def flush(self, timeout: float = 5.0) -> None:
        self._producer.flush(timeout)


class JsonConsumer[T: BaseModel]:
    """Wraps confluent_kafka.Consumer with pydantic JSON deserialization."""

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topic: str,
        model: type[T],
        auto_offset_reset: str = "earliest",
        extra_config: dict[str, str | int | bool] | None = None,
    ) -> None:
        config: dict[str, str | int | bool] = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": auto_offset_reset,
            "enable.auto.commit": False,
        }
        if extra_config:
            config.update(extra_config)
        self._consumer = Consumer(config)
        self._consumer.subscribe([topic])
        self._model = model

    def poll(self, timeout: float = 1.0) -> T | None:
        msg = self._consumer.poll(timeout)
        if msg is None:
            return None
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                return None
            raise KafkaException(msg.error())
        value = msg.value()
        if value is None:
            return None
        payload = json.loads(value.decode("utf-8"))
        return self._model.model_validate(payload)

    def commit(self) -> None:
        self._consumer.commit(asynchronous=False)

    def iter(self, timeout: float = 1.0) -> Iterator[T]:
        while True:
            event = self.poll(timeout)
            if event is not None:
                yield event

    def seek_to_end(self, timeout: float = 10.0) -> None:
        """Skip to the end of all assigned partitions, discarding any backlog."""
        self._consumer.poll(timeout)
        for tp in self._consumer.assignment():
            _, high = self._consumer.get_watermark_offsets(tp)
            self._consumer.seek(TopicPartition(tp.topic, tp.partition, high))

    def close(self) -> None:
        self._consumer.close()
