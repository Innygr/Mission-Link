# Mesh routing simulation tests

These tests define the minimum behavior for the future mesh router. They are simulator-level and do not transmit RF. They must pass before connecting routing logic to the radio driver.

## Required cases

1. **Three-node path:** A originates a packet for C; B forwards once; C accepts it.
2. **Duplicate suppression:** B receives the same message ID twice and forwards it at most once within the cache lifetime.
3. **Hop limit:** a packet at its hop limit is dropped and not forwarded.
4. **Loop resistance:** A ↔ B loops cannot cause unlimited forwarding.
5. **Unknown destination:** bounded flood is rate-limited and expires.
6. **Queue bound:** a full store-and-forward queue drops according to documented policy without heap growth.
7. **Replay:** authenticated old packets are rejected once the security layer is present.
8. **Tamper:** invalid authentication is rejected before a packet can be forwarded.

## Status

Not implemented yet. Existing native tests validate the packet codec only; they do not test an actual mesh router.
