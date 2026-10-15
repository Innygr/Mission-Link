import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from host.missionlink_contacts import Contact, ContactBook
from host.missionlink_contacts_cli import main

NUMBER = "(777)-482-1937"


class ContactBookCliTests(unittest.TestCase):
    def test_add_list_rename_and_remove(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "contacts.json"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--file", str(path), "add", NUMBER, "Vancouver", "--node-id", "node_van"]), 0)
                self.assertEqual(main(["--file", str(path), "list"]), 0)
                self.assertEqual(main(["--file", str(path), "rename", NUMBER, "Vancouver relay"]), 0)
                self.assertEqual(main(["--file", str(path), "remove", NUMBER]), 0)
                self.assertEqual(main(["--file", str(path), "list"]), 0)
            text = output.getvalue()
            self.assertIn("Vancouver", text)
            self.assertIn("Vancouver relay", text)
            self.assertIn("No contacts.", text)
            self.assertEqual(ContactBook.load(path).list_contacts(), ())

    def test_show_outputs_machine_readable_contact_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.json"
            book = ContactBook()
            book.upsert(Contact(NUMBER, "Vancouver relay", node_id="node_van", last_seen_ms=1234))
            book.save(path)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["--file", str(path), "show", NUMBER])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(output.getvalue()), {
                "mesh_number": NUMBER,
                "label": "Vancouver relay",
                "node_id": "node_van",
                "public_key_fingerprint": None,
                "last_seen_ms": 1234,
            })

    def test_show_missing_contact_returns_nonzero_without_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.json"
            output = io.StringIO()
            errors = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                result = main(["--file", str(path), "show", NUMBER])
            self.assertEqual(result, 1)
            self.assertEqual(output.getvalue(), "")
            self.assertIn("Contact not found.", errors.getvalue())

    def test_find_matches_label_case_insensitively_and_mesh_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.json"
            book = ContactBook()
            book.upsert(Contact(NUMBER, "Vancouver relay", node_id="node_van"))
            book.upsert(Contact("(777)-111-2222", "Mission gateway"))
            book.save(path)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--file", str(path), "find", "VANCOUVER"]), 0)
            self.assertIn(NUMBER, output.getvalue())
            self.assertIn("Vancouver relay", output.getvalue())
            self.assertNotIn("Mission gateway", output.getvalue())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--file", str(path), "find", "111-2222"]), 0)
            self.assertIn("Mission gateway", output.getvalue())

    def test_find_rejects_empty_query(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.json"
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                result = main(["--file", str(path), "find", "   "])
            self.assertEqual(result, 2)
            self.assertIn("Search query must not be empty.", errors.getvalue())

    def test_find_without_matches_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.json"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["--file", str(path), "find", "missing"])
            self.assertEqual(result, 1)
            self.assertIn("No matching contacts.", output.getvalue())

    def test_invalid_contact_is_reported_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.json"
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                result = main(["--file", str(path), "add", "not-a-number", "bad"])
            self.assertEqual(result, 1)
            self.assertIn("invalid_mesh_number", errors.getvalue())
            self.assertFalse(path.exists())

    def test_remove_missing_contact_returns_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.json"
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                result = main(["--file", str(path), "remove", NUMBER])
            self.assertEqual(result, 1)
            self.assertIn("Contact not found", errors.getvalue())

    def test_import_requires_explicit_replace_and_validates_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            destination = root / "contacts.json"
            book = ContactBook()
            book.upsert(Contact(NUMBER, "Vancouver relay"))
            book.save(source)

            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                result = main(["--file", str(destination), "import", str(source)])
            self.assertEqual(result, 2)
            self.assertFalse(destination.exists())

            self.assertEqual(main(["--file", str(destination), "import", str(source), "--replace"]), 0)
            self.assertEqual(ContactBook.load(destination).get(NUMBER).label, "Vancouver relay")

    def test_export_writes_validated_book(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "contacts.json"
            exported = root / "backup" / "contacts.json"
            book = ContactBook()
            book.upsert(Contact(NUMBER, "Vancouver relay"))
            book.save(source)
            self.assertEqual(main(["--file", str(source), "export", str(exported)]), 0)
            self.assertEqual(ContactBook.load(exported).get(NUMBER).label, "Vancouver relay")


if __name__ == "__main__":
    unittest.main()
