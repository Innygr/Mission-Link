"""Local Mesh Number contact book.

Contacts are labels for local convenience, not proof of identity. Mesh Numbers,
routing node IDs, and public-key fingerprints remain distinct fields.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

SCHEMA_VERSION = 1
MAX_CONTACTS = 512
MAX_FILE_BYTES = 128 * 1024
MAX_LABEL_LENGTH = 48
MESH_NUMBER_RE = re.compile(r"^\(777\)-[0-9]{3}-[0-9]{4}$")
NODE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")


class ContactBookError(ValueError):
    """Raised when a contact or contact-book file violates the bounded schema."""


@dataclass(frozen=True)
class Contact:
    mesh_number: str
    label: str
    node_id: str | None = None
    public_key_fingerprint: str | None = None
    last_seen_ms: int | None = None

    def validate(self) -> None:
        if not isinstance(self.mesh_number, str) or not MESH_NUMBER_RE.fullmatch(self.mesh_number):
            raise ContactBookError("invalid_mesh_number")
        if not isinstance(self.label, str) or not self.label.strip() or len(self.label) > MAX_LABEL_LENGTH:
            raise ContactBookError("invalid_label")
        if any(ord(ch) < 32 for ch in self.label):
            raise ContactBookError("invalid_label")
        if self.node_id is not None and (
            not isinstance(self.node_id, str) or not NODE_ID_RE.fullmatch(self.node_id)
        ):
            raise ContactBookError("invalid_node_id")
        if self.public_key_fingerprint is not None and (
            not isinstance(self.public_key_fingerprint, str)
            or not FINGERPRINT_RE.fullmatch(self.public_key_fingerprint)
        ):
            raise ContactBookError("invalid_public_key_fingerprint")
        if self.last_seen_ms is not None and (
            isinstance(self.last_seen_ms, bool)
            or not isinstance(self.last_seen_ms, int)
            or self.last_seen_ms < 0
        ):
            raise ContactBookError("invalid_last_seen")


class ContactBook:
    """Bounded local address book; persistence is opt-in via save/load."""

    def __init__(self, contacts: tuple[Contact, ...] = ()) -> None:
        if not isinstance(contacts, tuple) or len(contacts) > MAX_CONTACTS:
            raise ContactBookError("invalid_contact_list")
        self._contacts: dict[str, Contact] = {}
        for contact in contacts:
            self._validate_contact(contact)
            if contact.mesh_number in self._contacts:
                raise ContactBookError("duplicate_mesh_number")
            self._contacts[contact.mesh_number] = contact

    @staticmethod
    def _validate_contact(contact: Contact) -> None:
        if not isinstance(contact, Contact):
            raise ContactBookError("invalid_contact")
        contact.validate()

    def __len__(self) -> int:
        return len(self._contacts)

    def list_contacts(self) -> tuple[Contact, ...]:
        return tuple(self._contacts[key] for key in sorted(self._contacts))

    def get(self, mesh_number: str) -> Contact | None:
        return self._contacts.get(mesh_number)

    def upsert(self, contact: Contact) -> None:
        self._validate_contact(contact)
        if contact.mesh_number not in self._contacts and len(self._contacts) >= MAX_CONTACTS:
            raise ContactBookError("contact_book_full")
        self._contacts[contact.mesh_number] = contact

    def rename(self, mesh_number: str, label: str) -> Contact:
        current = self._contacts.get(mesh_number)
        if current is None:
            raise ContactBookError("contact_not_found")
        updated = Contact(
            mesh_number=current.mesh_number,
            label=label,
            node_id=current.node_id,
            public_key_fingerprint=current.public_key_fingerprint,
            last_seen_ms=current.last_seen_ms,
        )
        updated.validate()
        self._contacts[mesh_number] = updated
        return updated

    def remove(self, mesh_number: str) -> bool:
        return self._contacts.pop(mesh_number, None) is not None

    def to_bytes(self) -> bytes:
        payload = {
            "schemaVersion": SCHEMA_VERSION,
            "contacts": [asdict(contact) for contact in self.list_contacts()],
        }
        raw = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        if len(raw) > MAX_FILE_BYTES:
            raise ContactBookError("contact_book_too_large")
        return raw

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ContactBook":
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_FILE_BYTES:
            raise ContactBookError("invalid_file_size")
        try:
            payload = json.loads(
                raw.decode("utf-8", errors="strict"),
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError("invalid_constant")),
            )
        except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
            raise ContactBookError("invalid_json") from exc
        if not isinstance(payload, dict) or set(payload) != {"schemaVersion", "contacts"}:
            raise ContactBookError("invalid_file_fields")
        if type(payload["schemaVersion"]) is not int or payload["schemaVersion"] != SCHEMA_VERSION:
            raise ContactBookError("unsupported_schema_version")
        entries = payload["contacts"]
        if not isinstance(entries, list) or len(entries) > MAX_CONTACTS:
            raise ContactBookError("invalid_contact_list")
        contacts: list[Contact] = []
        allowed = {"mesh_number", "label", "node_id", "public_key_fingerprint", "last_seen_ms"}
        for item in entries:
            if not isinstance(item, dict) or set(item) != allowed:
                raise ContactBookError("invalid_contact_fields")
            contacts.append(Contact(**item))
        return cls(tuple(contacts))

    def save(self, path: str | os.PathLike[str]) -> None:
        """Atomically replace a local contact-book file; parent must already exist."""
        destination = Path(path)
        raw = self.to_bytes()
        if not destination.parent.is_dir():
            raise ContactBookError("parent_directory_missing")
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".missionlink-contacts-", suffix=".tmp",
                dir=destination.parent, delete=False,
            ) as stream:
                temporary_name = stream.name
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, destination)
            temporary_name = None
        except OSError as exc:
            raise ContactBookError("contact_book_write_failed") from exc
        finally:
            if temporary_name is not None:
                try:
                    os.unlink(temporary_name)
                except OSError:
                    pass

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> "ContactBook":
        source = Path(path)
        try:
            if source.stat().st_size > MAX_FILE_BYTES:
                raise ContactBookError("invalid_file_size")
            with source.open("rb") as stream:
                raw = stream.read(MAX_FILE_BYTES + 1)
        except ContactBookError:
            raise
        except OSError as exc:
            raise ContactBookError("contact_book_read_failed") from exc
        if len(raw) > MAX_FILE_BYTES:
            raise ContactBookError("invalid_file_size")
        return cls.from_bytes(raw)
