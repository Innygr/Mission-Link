"""Fail-closed service dispatch policy for a future MissionLink gateway.

This module does not authenticate transports or open network/radio interfaces.
The adapter must authenticate a peer first and pass its verified principal ID.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
import json
import threading
from typing import Any

from host.missionlink_envelopes import (
    EnvelopeError,
    MAX_LIFETIME_MS,
    ServiceEnvelope,
    is_expired,
)
from host.missionlink_services import (
    RegistryError,
    ServiceRecord,
    ServiceRegistry,
)

MAX_REPLAY_ENTRIES = 1024
MAX_CLOCK_SKEW_MS = 30_000
RESPONSE_LIFETIME_MS = 30_000


class DispatchError(ValueError):
    """Stable, non-sensitive dispatch rejection code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


Handler = Callable[[str, Mapping[str, Any]], dict[str, Any]]


class ServiceDispatcher:
    """Bounded request dispatcher with explicit ACLs and replay suppression.

    `acl` maps an already-authenticated principal ID to allowed service IDs.
    It is policy data, not an authentication mechanism. Handlers are registered
    explicitly by service ID and operation; there is no dynamic import or
    arbitrary endpoint execution.
    """

    def __init__(
        self,
        registry: ServiceRegistry,
        acl: Mapping[str, frozenset[str]],
        max_replay_entries: int = MAX_REPLAY_ENTRIES,
    ) -> None:
        if not isinstance(registry, ServiceRegistry):
            raise TypeError("registry_required")
        if isinstance(max_replay_entries, bool) or not isinstance(max_replay_entries, int):
            raise ValueError("invalid_replay_limit")
        if not 1 <= max_replay_entries <= MAX_REPLAY_ENTRIES:
            raise ValueError("replay_limit_out_of_range")
        clean_acl: dict[str, frozenset[str]] = {}
        for principal, services in acl.items():
            if not isinstance(principal, str) or not principal or len(principal) > 64:
                raise ValueError("invalid_principal")
            if not isinstance(services, frozenset) or any(
                not isinstance(service_id, str) or not service_id for service_id in services
            ):
                raise ValueError("invalid_acl")
            clean_acl[principal] = services
        self._registry = registry
        self._acl = clean_acl
        self._max_replay_entries = max_replay_entries
        self._handlers: dict[tuple[str, str], Handler] = {}
        self._seen: dict[tuple[str, str], int] = {}
        self._lock = threading.Lock()

    def register_handler(self, service_id: str, operation: str, handler: Handler) -> None:
        if not isinstance(service_id, str) or not service_id:
            raise ValueError("invalid_service_id")
        if not isinstance(operation, str) or not operation:
            raise ValueError("invalid_operation")
        if not callable(handler):
            raise TypeError("handler_must_be_callable")
        self._handlers[(service_id, operation)] = handler

    def _reserve_request_id(self, principal: str, request_id: str, now_ms: int) -> None:
        key = (principal, request_id)
        with self._lock:
            # Prune expired entries before applying the hard memory bound.
            self._seen = {item: expiry for item, expiry in self._seen.items() if expiry > now_ms}
            if key in self._seen:
                raise DispatchError("replay")
            if len(self._seen) >= self._max_replay_entries:
                raise DispatchError("replay_cache_full")
            self._seen[key] = now_ms + MAX_LIFETIME_MS

    def dispatch(self, raw: bytes, *, principal_id: str, now_ms: int) -> ServiceEnvelope:
        """Validate, authorize, deduplicate, then invoke one registered handler.

        `principal_id` must come from a trusted/authenticated adapter. This
        function deliberately does not infer identity from packet fields.
        """
        if not isinstance(principal_id, str) or not principal_id or len(principal_id) > 64:
            raise DispatchError("unauthenticated")
        if isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms < 0:
            raise DispatchError("invalid_clock")
        try:
            request = ServiceEnvelope.from_bytes(raw)
        except EnvelopeError as exc:
            raise DispatchError("bad_request") from exc
        if request.kind != "request":
            raise DispatchError("request_required")
        if is_expired(request, now_ms):
            raise DispatchError("expired")
        if request.created_at_ms > now_ms + MAX_CLOCK_SKEW_MS:
            raise DispatchError("future_timestamp")
        if request.service_id not in self._acl.get(principal_id, frozenset()):
            raise DispatchError("forbidden")
        service = self._registry.get(request.service_id)
        if service is None:
            raise DispatchError("not_found")
        if not service.healthy:
            raise DispatchError("unavailable")
        if not _payload_fits(request.payload, service):
            raise DispatchError("too_large")
        handler = self._handlers.get((request.service_id, request.operation))
        if handler is None:
            raise DispatchError("operation_not_found")

        # Reserve before executing so a repeated request cannot invoke a
        # side-effecting handler twice. If a handler fails, clients must use a
        # new request ID; the same ID remains reserved until its TTL expires.
        self._reserve_request_id(principal_id, request.request_id, now_ms)
        try:
            response_payload = handler(principal_id, request.payload)
        except Exception as exc:
            raise DispatchError("handler_failed") from exc
        if not isinstance(response_payload, dict):
            raise DispatchError("invalid_handler_response")

        response_expiry = min(request.expires_at_ms, now_ms + RESPONSE_LIFETIME_MS)
        response = ServiceEnvelope(
            kind="response",
            request_id=request.request_id,
            service_id=request.service_id,
            operation=request.operation,
            created_at_ms=now_ms,
            expires_at_ms=response_expiry,
            payload=response_payload,
        )
        try:
            response.to_bytes()
        except EnvelopeError as exc:
            raise DispatchError("response_too_large") from exc
        return response


def _payload_fits(payload: dict[str, Any], service: ServiceRecord) -> bool:
    try:
        size = len(json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError, UnicodeError):
        return False
    return size <= service.max_inline_request_bytes
