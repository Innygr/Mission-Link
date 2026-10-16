import json
import tempfile
import unittest
from pathlib import Path

from host.missionlink_contacts import (
    MAX_CONTACTS,
    Contact,
    ContactBook,
    ContactBookError,
)

NUMBER = "(777)-482-1937"
FINGERPRINT = "a" * 64


class ContactBookTests(unittest.TestCase):
    def test_upsert_lookup_rename_and_remove(self):
        book = ContactBook()
        book.upsert(Contact(NUMBER, "Vancouver relay", node_id="node_123"))
        self.assertEqual(book.get(NUMBER).label, "Vancouver relay")
        renamed = book.rename(NUMBER, "Downtown relay")
        self.assertEqual(renamed.label, "Downtown relay")
        self.assertEqual(renamed.node_id, "node_123")
        self.assertTrue(book.remove(NUMBER))
        self.assertFalse(book.remove(NUMBER))
        self.assertIsNone(book.get(NUMBER))

    def test_number_format_and_metadata_are_validated(self):
        for number in ("777-482-1937", "(777)-48-1937", "(778)-482-1937", "(777)-482-193"):
            with self.subTest(number=number), self.assertRaises(ContactBookError):
                Contact(number, "Invalid").validate()
        with self.assertRaises(ContactBookError):
            Contact(NUMBER, "x" * 49).validate()
        with self.assertRaises(ContactBookError):
            Contact(NUMBER, "Relay", public_key_fingerprint="not-a-fingerprint").validate()
        with self.assertRaises(ContactBookError):
            Contact(NUMBER, "Relay", last_seen_ms=True).validate()

    def test_node_id_and_public_key_fingerprint_are_separate_fields(self):
        contact = Contact(
            NUMBER, "Mission base", node_id="routing-node-9",
            public_key_fingerprint=FINGERPRINT, last_seen_ms=123456,
        )
        book = ContactBook()
        book.upsert(contact)
        decoded = ContactBook.from_bytes(book.to_bytes()).get(NUMBER)
        self.assertEqual(decoded.mesh_number, NUMBER)
        self.assertEqual(decoded.node_id, "routing-node-9")
        self.assertEqual(decoded.public_key_fingerprint, FINGERPRINT)
        self.assertEqual(decoded.last_seen_ms, 123456)

    def test_duplicate_mesh_numbers_are_rejected(self):
        with self.assertRaises(ContactBookError):
            ContactBook((Contact(NUMBER, "First"), Contact(NUMBER, "Second")))

    def test_serialization_is_stable_and_round_trips(self):
        book = ContactBook()
        book.upsert(Contact("(777)-482-1937", "Vancouver", node_id="node_van"))
        book.upsert(Contact("(777)-123-4567", "Mission", node_id="node_msn"))
        raw = book.to_bytes()
        self.assertEqual(raw, ContactBook.from_bytes(raw).to_bytes())
        self.assertEqual(
            [contact.mesh_number for contact in ContactBook.from_bytes(raw).list_contacts()],
            ["(777)-123-4567", "(777)-482-1937"],
        )

    def test_unknown_fields_bad_versions_and_malformed_json_are_rejected(self):
        valid = {"schemaVersion": 1, "contacts": []}
        with self.assertRaises(ContactBookError):
            ContactBook.from_bytes(json.dumps({**valid, "secret": "unexpected"}).encode())
        with self.assertRaises(ContactBookError):
            ContactBook.from_bytes(json.dumps({"schemaVersion": 2, "contacts": []}).encode())
        with self.assertRaises(ContactBookError):
            ContactBook.from_bytes(b"{broken")
        with self.assertRaises(ContactBookError):
            ContactBook.from_bytes(json.dumps({
                "schemaVersion": 1,
                "contacts": [{"mesh_number": NUMBER, "label": "Relay"}],
            }).encode())

    def test_contact_count_is_bounded(self):
        contacts = tuple(
            Contact(f"(777)-{i // 10000:03d}-{i % 10000:04d}", f"Node {i}")
            for i in range(MAX_CONTACTS + 1)
        )
        with self.assertRaises(ContactBookError):
            ContactBook(contacts)

    def test_atomic_save_and_load(self):
        book = ContactBook()
        book.upsert(Contact(NUMBER, "Vancouver relay", node_id="node_van"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.json"
            book.save(path)
            self.assertEqual(ContactBook.load(path).get(NUMBER).label, "Vancouver relay")
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ["contacts.json"])

    def test_oversized_files_are_rejected(self):
        with self.assertRaises(ContactBookError):
            ContactBook.from_bytes(b"x" * (128 * 1024 + 1))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "too-large.json"
            path.write_bytes(b"x" * (128 * 1024 + 1))
            with self.assertRaises(ContactBookError):
                ContactBook.load(path)


if __name__ == "__main__":
    unittest.main()
