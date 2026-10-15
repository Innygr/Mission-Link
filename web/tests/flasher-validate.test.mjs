// Run: node --test web/tests/
import test from "node:test";
import assert from "node:assert/strict";
import { validateFirmwareSet, parsePartitionTable, checkImageHeader } from "../flasher-validate.js";

const image = (chip = 9, size = 64) => { const b = new Uint8Array(size); b[0] = 0xE9; b[1] = 3; b[12] = chip & 255; b[13] = chip >> 8; return b; };
const entry = (type, offset, size) => { const b = new Uint8Array(32); b[0] = 0xAA; b[1] = 0x50; b[2] = type; const dv = new DataView(b.buffer); dv.setUint32(4, offset, true); dv.setUint32(8, size, true); return b; };
const table = (...es) => { const b = new Uint8Array(es.length * 32); es.forEach((e, i) => b.set(e, i * 32)); return b; };
const good = () => ({ bootloader: image(), partitions: table(entry(1, 0x9000, 0x5000), entry(0, 0x10000, 0x100000)), application: image(9, 4096) });

test("accepts a consistent ESP32-S3 set", () => {
  const r = validateFirmwareSet(good(), "ESP32-S3 (QFN56) (revision v0.2)");
  assert.deepEqual(r.errors, []);
  assert.equal(r.warnings.length, 1);
});
test("rejects non-S3 connected chip", () => assert.ok(validateFirmwareSet(good(), "ESP32").errors.length));
test("rejects wrong chip id in image", () => {
  const f = good(); f.application = image(0);
  assert.ok(validateFirmwareSet(f, "ESP32-S3").errors.some(e => /chip ID/.test(e)));
});
test("rejects bad magic", () => assert.ok(checkImageHeader(new Uint8Array(64), "X").length));
test("rejects merged-size bootloader", () => {
  const f = good(); f.bootloader = image(9, 0x20000);
  assert.ok(validateFirmwareSet(f, "ESP32-S3").errors.some(e => /merged/.test(e)));
});
test("rejects app larger than partition", () => {
  const f = good(); f.partitions = table(entry(0, 0x10000, 1024));
  assert.ok(validateFirmwareSet(f, "ESP32-S3").errors.some(e => /larger than its partition/.test(e)));
});
test("rejects table without app slot at 0x10000", () => {
  const f = good(); f.partitions = table(entry(0, 0x20000, 0x100000));
  assert.ok(validateFirmwareSet(f, "ESP32-S3").errors.some(e => /no app partition/.test(e)));
});
test("rejects garbage partition table", () => assert.ok(parsePartitionTable(new Uint8Array(64)).errors.length));
test("rejects malformed data after a valid partition entry", () => {
  const malformed = table(entry(1, 0x9000, 0x5000), new Uint8Array(32));
  const parsed = parsePartitionTable(malformed);
  assert.equal(parsed.entries.length, 1);
  assert.ok(parsed.errors.some(e => /malformed data at offset 0x20/.test(e)));
});
test("accepts erased 0xFF padding after valid partition entries", () => {
  const padded = new Uint8Array(96).fill(0xFF);
  padded.set(entry(0, 0x10000, 0x100000), 0);
  const parsed = parsePartitionTable(padded);
  assert.deepEqual(parsed.errors, []);
  assert.equal(parsed.entries.length, 1);
});

import { createHash } from "node:crypto";
import { md5BinaryString } from "../flasher-validate.js";
test("md5BinaryString matches node:crypto across block boundaries", () => {
  for (const n of [0, 1, 55, 56, 63, 64, 65, 1000, 70001]) {
    const bytes = new Uint8Array(n).map((_, i) => (i * 131 + 7) & 0xFF);
    const str = String.fromCharCode(...bytes);
    assert.equal(md5BinaryString(str), createHash("md5").update(bytes).digest("hex"), "length " + n);
  }
});
