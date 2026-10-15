import tempfile
import unittest
from pathlib import Path

from host.missionlink_contacts import Contact, ContactBook, ContactBookError
from host.missionlink_contact_resolver import (
    ContactBookResolver,
    ResolvedContact,
    resolver_from_file,
)

NUMBER = "(777)-482-1937"
FINGERPRINT = "b" * 64


class ContactResolverTests(unittest.TestCase):
    def test_resolves_client_view_without_exposing_storage_field_names(self):
        book = ContactBook()
        book.upsert(Contact(
            NUMBER, "Vancouver relay", node_id="node_van",
            public_key_fingerprint=FINGERPRINT, last_seen_ms=1234,
        ))
        resolved = ContactBookResolver(book).resolve(NUMBER)
        self.assertEqual(resolved, ResolvedContact(
            mesh_number=NUMBER,
            display_name="Vancouver relay",
            routing_node_id="node_van",
            public_key_fingerprint=FINGERPRINT,
            last_seen_ms=1234,
        ))

    def test_unknown_valid_number_returns_none(self):
        self.assertIsNone(ContactBookResolver(ContactBook()).resolve(NUMBER))

    def test_invalid_number_is_distinct_from_unknown_number(self):
        resolver = ContactBookResolver(ContactBook())
        with self.assertRaisesRegex(ContactBookError, "invalid_mesh_number"):
            resolver.resolve("777-482-1937")

    def test_rejects_wrong_book_type(self):
        with self.assertRaisesRegex(TypeError, "book_must_be_contact_book"):
            ContactBookResolver(object())

    def test_file_helper_loads_once_and_resolves(self):
        book = ContactBook()
        book.upsert(Contact(NUMBER, "Mission gateway", node_id="node_mission"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.json"
            book.save(path)
            resolver = resolver_from_file(str(path))
            self.assertEqual(resolver.resolve(NUMBER).display_name, "Mission gateway")
            # Resolver is an explicit snapshot, not a live file watcher.
            book.rename(NUMBER, "Renamed")
            book.save(path)
            self.assertEqual(resolver.resolve(NUMBER).display_name, "Mission gateway")


if __name__ == "__main__":
    unittest.main()
