"""Command-line interface for the experimental local MissionLink contact book.

This is a local file utility only; it does not discover nodes or send messages.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from host.missionlink_contacts import Contact, ContactBook, ContactBookError

DEFAULT_PATH = Path.home() / ".local" / "share" / "missionlink" / "contacts.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage local MissionLink Mesh Number contacts.")
    parser.add_argument("--file", type=Path, default=DEFAULT_PATH, help=f"contact file (default: {DEFAULT_PATH})")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="list saved contacts")
    add = commands.add_parser("add", help="add or replace a contact")
    add.add_argument("mesh_number")
    add.add_argument("label")
    add.add_argument("--node-id")
    add.add_argument("--fingerprint")
    add.add_argument("--last-seen-ms", type=int)

    rename = commands.add_parser("rename", help="change a contact's local label")
    rename.add_argument("mesh_number")
    rename.add_argument("label")

    remove = commands.add_parser("remove", help="remove a contact")
    remove.add_argument("mesh_number")

    export = commands.add_parser("export", help="export validated contact JSON")
    export.add_argument("destination", type=Path)

    import_cmd = commands.add_parser("import", help="validate and replace contacts from a JSON file")
    import_cmd.add_argument("source", type=Path)
    import_cmd.add_argument("--replace", action="store_true", help="required confirmation to replace the current book")
    return parser


def _load(path: Path) -> ContactBook:
    if not path.exists():
        return ContactBook()
    return ContactBook.load(path)


def _save(book: ContactBook, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    book.save(path)
    # Contacts can contain personally meaningful labels; limit access to this user's file.
    try:
        os.chmod(path, 0o600)
    except OSError:
        # Windows and some filesystems may not support POSIX permission semantics.
        pass


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "export":
            book = _load(args.file)
            _save(book, args.destination)
            print(f"Exported {len(book)} contact(s) to {args.destination}")
            return 0

        if args.command == "import":
            if not args.replace:
                print("Refusing to replace contacts without --replace.", file=sys.stderr)
                return 2
            book = ContactBook.load(args.source)
            _save(book, args.file)
            print(f"Imported {len(book)} contact(s) into {args.file}")
            return 0

        book = _load(args.file)
        if args.command == "list":
            if not len(book):
                print("No contacts.")
            else:
                for contact in book.list_contacts():
                    suffix = f" [node: {contact.node_id}]" if contact.node_id else ""
                    print(f"{contact.mesh_number}\t{contact.label}{suffix}")
            return 0

        if args.command == "add":
            book.upsert(Contact(
                mesh_number=args.mesh_number,
                label=args.label,
                node_id=args.node_id,
                public_key_fingerprint=args.fingerprint,
                last_seen_ms=args.last_seen_ms,
            ))
            _save(book, args.file)
            print(f"Saved {args.mesh_number}")
            return 0

        if args.command == "rename":
            book.rename(args.mesh_number, args.label)
            _save(book, args.file)
            print(f"Renamed {args.mesh_number}")
            return 0

        if args.command == "remove":
            if not book.remove(args.mesh_number):
                print("Contact not found.", file=sys.stderr)
                return 1
            _save(book, args.file)
            print(f"Removed {args.mesh_number}")
            return 0

        raise AssertionError("unhandled_command")
    except ContactBookError as exc:
        print(f"Contact book error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"File operation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
