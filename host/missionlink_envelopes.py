"""Bounded, versioned service request/response envelopes for MissionLink.

This is a host-side protocol codec only. It does not authenticate peers, open
sockets, route packets, or enable radio transmission.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from host.missionlink_services import SERVICE_ID_RE

SCHEMA_VERSION = 1
MAX_ENVELOPE_BYTES = 180
MAX_LIFETIME_MS = 300_000
MAX_JSON_DEPTH = 8
REQUEST_KINDS = frozenset({"request", "response", "error"})
ERROR_CODES = frozenset({"bad_request", "forbidden", "not_found", "unavailable", "too_large", "expired", "internal"})
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,48}$")


class EnvelopeError(ValueError):
    """Raised when an envelope is malformed or exceeds protocol bounds."""


def _json_depth(value: Any, depth: int = 0) -> int:
    if depth > MAX_JSON_DEPTH:
        return depth
    if isinstance(value, dict):
        return max([depth, *(_json_depth(k, depth + 1) for k in value),
                    *(_json_depth(v, depth + 1) for v in value.values())])
    if isinstance(value, list):
        return max([depth, *(_json_depth(item, depth + 1) for item in value)])
    return depth


def _validate_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise EnvelopeError("payload_must_be_object")
    try:
        json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        if _json_depth(payload) > MAX_JSON_DEPTH:
            raise EnvelopeError("payload_too_deep")
    except (TypeError, ValueError, UnicodeError) as exc:
        if isinstance(exc, EnvelopeError):
            raise
        raise EnvelopeError("payload_not_json_safe") from exc


@dataclass(frozen=True)
class ServiceEnvelope:
    kind: str
    request_id: str
    service_id: str
    operation: str
    created_at_ms: int
    expires_at_ms: int
    payload: dict[str, Any]
    error_code: str | None = None

    def validate(self) -> None:
        if not isinstance(self.kind, str) or self.kind not in REQUEST_KINDS:
            raise EnvelopeError("invalid_kind")
        if not isinstance(self.request_id, str) or not REQUEST_ID_RE.fullmatch(self.request_id):
            raise EnvelopeError("invalid_request_id")
        if not isinstance(self.service_id, str) or not SERVICE_ID_RE.fullmatch(self.service_id):
            raise EnvelopeError("invalid_service_id")
        if not isinstance(self.operation, str) or not SERVICE_ID_RE.fullmatch(self.operation):
            raise EnvelopeError("invalid_operation")
        for field_name, value in (("created_at_ms", self.created_at_ms), ("expires_at_ms", self.expires_at_ms)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise EnvelopeError(f"invalid_{field_name}")
        lifetime = self.expires_at_ms - self.created_at_ms
        if lifetime <= 0 or lifetime > MAX_LIFETIME_MS:
            raise EnvelopeError("lifetime_out_of_range")
        _validate_payload(self.payload)
        if self.kind == "error":
            if not isinstance(self.error_code, str) or self.error_code not in ERROR_CODES:
                raise EnvelopeError("invalid_error_code")
        elif self.error_code is not None:
            raise EnvelopeError("unexpected_error_code")

    def to_bytes(self) -> bytes:
        self.validate()
        obj: dict[str, Any] = {
            "v": SCHEMA_VERSION, "k": self.kind, "rid": self.request_id,
            "sid": self.service_id, "op": self.operation,
            "t": self.created_at_ms, "x": self.expires_at_ms,
            "p": self.payload,
        }
        if self.error_code is not None:
            obj["e"] = self.error_code
        try:
            raw = json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError, UnicodeError) as exc:
            raise EnvelopeError("envelope_not_json_safe") from exc
        if len(raw) > MAX_ENVELOPE_BYTES:
            raise EnvelopeError("envelope_too_large")
        return raw

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ServiceEnvelope":
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_ENVELOPE_BYTES:
            raise EnvelopeError("invalid_wire_size")
        try:
            obj = json.loads(raw.decode("utf-8", errors="strict"),
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non_json_constant")))
        except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise EnvelopeError("invalid_json") from exc
        if not isinstance(obj, dict):
            raise EnvelopeError("envelope_must_be_object")
        allowed = {"v", "k", "rid", "sid", "op", "t", "x", "p", "e"}
        required = allowed - {"e"}
        if set(obj) - allowed or not required.issubset(obj):
            raise EnvelopeError("invalid_fields")
        if type(obj["v"]) is not int or obj["v"] != SCHEMA_VERSION:
            raise EnvelopeError("unsupported_version")
        envelope = cls(
            kind=obj["k"], request_id=obj["rid"], service_id=obj["sid"],
            operation=obj["op"], created_at_ms=obj["t"],
            expires_at_ms=obj["x"], payload=obj["p"], error_code=obj.get("e"),
        )
        envelope.validate()
        return envelope


def is_expired(envelope: ServiceEnvelope, now_ms: int) -> bool:
    """Return whether an otherwise-valid envelope has reached its expiry time."""
    envelope.validate()
    if isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms < 0:
        raise EnvelopeError("invalid_now_ms")
    return now_ms >= envelope.expires_at_ms
