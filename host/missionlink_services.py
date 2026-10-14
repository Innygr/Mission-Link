"""Platform-independent MissionLink host service registry.

This module is transport-agnostic: a non-ESP32-S3 computer can advertise local
services to a MissionLink gateway without pretending that the host itself is a
LoRa radio node. It deliberately does not open sockets or enable RF.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

SERVICE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
CAPABILITY_RE = SERVICE_ID_RE
# MissionLink protocol v1 currently allows at most 180 payload bytes before
# any future encryption overhead. This is a policy ceiling, not a guarantee
# that every radio configuration can carry that many bytes.
CURRENT_MESH_PAYLOAD_MAX = 180
DEFAULT_MESH_INLINE_MAX = 96
MAX_SERVICE_COUNT = 128
MAX_CAPABILITIES = 16


class RegistryError(ValueError):
    """Raised when a service registration violates the bounded schema."""


@dataclass(frozen=True)
class ServiceRecord:
    service_id: str
    host_id: str
    display_name: str
    capabilities: tuple[str, ...]
    transports: tuple[str, ...] = ("lan",)
    endpoint: str | None = None
    healthy: bool = True
    max_inline_request_bytes: int = DEFAULT_MESH_INLINE_MAX

    def validate(self) -> None:
        if not SERVICE_ID_RE.fullmatch(self.service_id):
            raise RegistryError("invalid_service_id")
        if not SERVICE_ID_RE.fullmatch(self.host_id):
            raise RegistryError("invalid_host_id")
        if not self.display_name or len(self.display_name) > 80:
            raise RegistryError("invalid_display_name")
        if not self.capabilities or len(self.capabilities) > MAX_CAPABILITIES:
            raise RegistryError("invalid_capabilities")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise RegistryError("duplicate_capability")
        if any(not CAPABILITY_RE.fullmatch(cap) for cap in self.capabilities):
            raise RegistryError("invalid_capability")
        allowed_transports = {"lan", "usb-serial", "bluetooth"}
        if not self.transports or any(t not in allowed_transports for t in self.transports):
            raise RegistryError("invalid_transport")
        if self.max_inline_request_bytes < 1 or self.max_inline_request_bytes > DEFAULT_MESH_INLINE_MAX:
            raise RegistryError("inline_limit_out_of_range")
        if self.endpoint is not None and len(self.endpoint) > 512:
            raise RegistryError("endpoint_too_long")
        # Mesh announcements must not include arbitrary endpoint URLs. They
        # may contain only service metadata; direct endpoints are local-only.
        if self.endpoint is not None and not self.endpoint.startswith(("http://127.0.0.1:", "http://localhost:", "https://")):
            raise RegistryError("endpoint_must_be_local_or_https")


class ServiceRegistry:
    """Bounded in-memory registry for services reachable through a host bridge."""

    def __init__(self, max_services: int = MAX_SERVICE_COUNT) -> None:
        if not 1 <= max_services <= MAX_SERVICE_COUNT:
            raise ValueError("max_services_out_of_range")
        self._max_services = max_services
        self._records: dict[str, ServiceRecord] = {}

    def register(self, record: ServiceRecord) -> None:
        record.validate()
        if record.service_id not in self._records and len(self._records) >= self._max_services:
            raise RegistryError("registry_full")
        self._records[record.service_id] = record

    def unregister(self, service_id: str) -> bool:
        return self._records.pop(service_id, None) is not None

    def get(self, service_id: str) -> ServiceRecord | None:
        return self._records.get(service_id)

    def list(self, capability: str | None = None, healthy_only: bool = True) -> tuple[ServiceRecord, ...]:
        records: Iterable[ServiceRecord] = self._records.values()
        if healthy_only:
            records = (record for record in records if record.healthy)
        if capability is not None:
            if not CAPABILITY_RE.fullmatch(capability):
                raise RegistryError("invalid_capability_filter")
            records = (record for record in records if capability in record.capabilities)
        return tuple(sorted(records, key=lambda item: item.service_id))


def mesh_inline_allowed(payload_bytes: int, service: ServiceRecord) -> bool:
    """Whether a small request fits the conservative mesh-inline policy.

    Bulk file data, model weights, and large AI inputs/results should use a
    separately authenticated direct transport, not be tunneled through LoRa.
    """
    return (
        isinstance(payload_bytes, int)
        and not isinstance(payload_bytes, bool)
        and 0 <= payload_bytes <= service.max_inline_request_bytes
        and payload_bytes <= CURRENT_MESH_PAYLOAD_MAX
    )
