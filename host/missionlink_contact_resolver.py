"""Reusable in-process contact resolution for MissionLink clients.

The resolver exposes a small view model and does not spawn the contact CLI or
require callers to know the JSON persistence schema. It performs local lookup
only; it does not discover nodes, verify keys, or send messages.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from host.missionlink_contacts import Contact, ContactBook, ContactBookError


@dataclass(frozen=True)
class ResolvedContact:
    """Client-facing contact view, independent of the on-disk representation."""

    mesh_number: str
    display_name: str
    routing_node_id: str | None
    public_key_fingerprint: str | None
    last_seen_ms: int | None


class ContactResolver(Protocol):
    """Minimal interface for a client that needs to resolve a Mesh Number."""

    def resolve(self, mesh_number: str) -> ResolvedContact | None:
        """Return the local contact view, or None when the number is unknown."""
        ...


class ContactBookResolver:
    """Adapt an in-memory ContactBook to the client-facing resolver interface."""

    def __init__(self, book: ContactBook) -> None:
        if not isinstance(book, ContactBook):
            raise TypeError("book_must_be_contact_book")
        self._book = book

    def resolve(self, mesh_number: str) -> ResolvedContact | None:
        # Validate at the API boundary so malformed addresses are not confused
        # with a valid address that simply has no local contact entry.
        Contact(mesh_number=mesh_number, label="lookup").validate()
        contact = self._book.get(mesh_number)
        if contact is None:
            return None
        return ResolvedContact(
            mesh_number=contact.mesh_number,
            display_name=contact.label,
            routing_node_id=contact.node_id,
            public_key_fingerprint=contact.public_key_fingerprint,
            last_seen_ms=contact.last_seen_ms,
        )


def resolver_from_file(path: str) -> ContactBookResolver:
    """Load a contact book once and return a resolver over that snapshot.

    Callers that need to observe later edits should reload the book and replace
    the resolver explicitly; this helper does not watch the file.
    """
    return ContactBookResolver(ContactBook.load(path))
