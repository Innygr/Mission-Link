# Local Mesh Number Contact Book (experimental)

The contact book stores local friendly names for Mission-Link addresses such as `(777)-482-1937`. A Mesh Number is an address, **not** a real telephone number, a routing node ID, or proof of cryptographic identity.

## Data model

Each contact contains:
- `mesh_number`: reserved Mission-Link address in the exact `(777)-XXX-XXXX` format.
- `label`: local display name, up to 48 characters.
- `node_id`: optional stable routing identifier, kept separate from the address.
- `public_key_fingerprint`: optional 64-character lowercase hexadecimal fingerprint. Storing a fingerprint does not verify it or establish trust.
- `last_seen_ms`: optional timestamp supplied by the caller.

The module does not assign Mesh Numbers, discover nodes, verify keys, or send messages. A future enrollment/registry process must prevent address collisions across regions. Contacts are sorted by Mesh Number when serialized.

## Command-line tool

Run commands from the repository root. The default file is `~/.local/share/missionlink/contacts.json`; pass `--file PATH` before the command to use another file.

```sh
python -m host.missionlink_contacts_cli list
python -m host.missionlink_contacts_cli add '(777)-482-1937' 'Vancouver relay' --node-id node_van
python -m host.missionlink_contacts_cli rename '(777)-482-1937' 'Downtown relay'
python -m host.missionlink_contacts_cli remove '(777)-482-1937'
python -m host.missionlink_contacts_cli export ./contacts-backup.json
python -m host.missionlink_contacts_cli --file ./contacts.json import ./contacts-backup.json --replace
```

Import replaces the target contact book and therefore requires the explicit `--replace` flag. Imported JSON is validated against the strict schema before it is saved. The CLI creates parent directories as needed and attempts to set the contact file to owner-only permissions on platforms that support POSIX permissions. Keep backups secure; labels and Mesh Numbers may reveal information about your network.

## Python use

```python
from host.missionlink_contacts import Contact, ContactBook

contacts = ContactBook.load("contacts.json")
contacts.upsert(Contact("(777)-482-1937", "Vancouver relay", node_id="node_van"))
contacts.save("contacts.json")
```

The library's destination directory must already exist. Writes use a temporary file in the same directory followed by an atomic replacement. The library does not encrypt the contact file.

## Safety and limits

- At most 512 contacts and 128 KiB per file.
- Unknown fields and unsupported schema versions are rejected rather than silently discarded.
- Duplicate Mesh Numbers are rejected on import.
- The file contains no bearer tokens, private keys, or secret credentials.
- No GUI, contact synchronization, network discovery, key verification, or radio transport is included.

Run tests with:

```sh
python -m unittest discover -s host/tests -v
```
