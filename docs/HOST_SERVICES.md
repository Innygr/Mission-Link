# Cross-platform host services and mesh gateways

MissionLink's radio firmware is not the same thing as a service host. A machine does **not** need to be an ESP32-S3, run Arduino firmware, or have its own LoRa radio to offer storage or AI services.

## Architecture

```text
Windows / Linux / macOS / NAS / local-AI workstation
         |  authenticated LAN API (bulk data stays here)
         v
Cross-platform MissionLink host service
         |  local gateway API / USB serial (future adapter)
         v
MissionLink gateway node (e.g. XIAO ESP32-S3 + Wio-SX1262)
         |  short control messages, discovery, job IDs
         v
          LoRa mesh
```

A host joins by connecting to a MissionLink gateway that it can reach over a supported local transport. The gateway bridges service discovery and small control messages between the host API and mesh. The host and the gateway have separate identities: a mesh node ID identifies a radio endpoint; a host ID identifies a computer; a service ID identifies one capability on that computer.

This first implementation adds a platform-independent, transport-agnostic in-memory registry in `host/missionlink_services.py`. It does not yet implement a network listener, radio bridge, automatic discovery, or a production service. Those are follow-on milestones; don't describe a registered test record as an available network service.

## Service model

Each service record includes:

- stable service ID and host ID;
- display name and bounded capability list (examples: `file.index`, `file.read`, `ai.inference`);
- available transports;
- optional direct endpoint, health flag, and maximum inline request size.

The registry bounds service count, ID lengths, capability count, endpoint length, and mesh-inline request size. Endpoint metadata is local registry data; do not broadcast LAN addresses, access tokens, or credentials in public mesh announcements.

## What belongs on LoRa vs. LAN

**LoRa mesh:** discovery summaries, service IDs, short prompts/commands, status, job IDs, progress summaries, and small responses.

**Authenticated direct connection:** files, model weights, large prompts/outputs, embeddings, and other bulk payloads. The current protocol v1 payload ceiling is 180 bytes before future encryption overhead, and the conservative service-registry default is only 96 bytes for inline requests. Neither value is a promise that every real radio configuration supports the full amount.

Do not automatically chunk and send large files through LoRa. If a future use case absolutely requires store-and-forward transfer over radio, it needs a separately designed protocol with strict quotas, resumability, hashes, timeouts, expiry, congestion controls, and explicit user approval.

## Security requirements before production

- Authenticate host-to-gateway and client-to-service connections.
- Authorize every service operation; a mesh node being reachable does not grant file or AI access.
- Use TLS or another reviewed authenticated channel for remote service endpoints. Do not expose plain HTTP endpoints beyond loopback.
- Restrict file operations to explicitly configured roots; reject traversal, symlink escapes, and untrusted path input.
- Give AI services request/token/time limits and explicit opt-in before allowing tools or filesystem access.
- Do not put secrets, private file contents, raw prompts, or model data in mesh discovery packets.
- Add end-to-end authenticated encryption and replay protection to MissionLink before sending sensitive data over RF.
- Keep `ML_RF_ENABLED=0` until board configuration and Canadian compliance gates are complete.

## Current Python component and tests

From the repository root, with Python 3.10+:

```sh
python -m unittest discover -s host/tests -v
```

The service registry is only a data/validation layer. It is not a daemon and opens no sockets. A subsequent milestone should define the versioned gateway API and implement a loopback-first adapter, then add an authenticated LAN transport and service plugins for file storage and local AI.
