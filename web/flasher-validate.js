// Pure helpers for pre-flash checks. No DOM or Web Serial access, so they can run under Node.
export const ESP32_S3_CHIP_ID = 0x0009;
export const LAYOUT = {
  bootloader: { address: 0x0000, maxSize: 0x8000, label: "Bootloader" },
  partitions: { address: 0x8000, maxSize: 0x1000, label: "Partition table" },
  bootapp: { address: 0xE000, maxSize: 0x2000, label: "Boot app" },
  application: { address: 0x10000, maxSize: 0x3F0000, label: "Application" }
};

function hex(n) { return "0x" + n.toString(16).toUpperCase(); }

export function isS3ChipName(name) { return /ESP32-S3/i.test(String(name || "")); }

// Checks an ESP image header (bootloader or application). Returns an array of error strings.
export function checkImageHeader(bytes, label) {
  const errors = [];
  if (bytes.length < 24) return [label + " is too small to be an ESP image."];
  if (bytes[0] !== 0xE9) errors.push(label + " does not start with the ESP image magic byte 0xE9.");
  else {
    const chipId = bytes[12] | (bytes[13] << 8);
    if (chipId !== ESP32_S3_CHIP_ID) errors.push(label + " targets chip ID " + hex(chipId) + ", not ESP32-S3 (0x9).");
    if (bytes[1] === 0 || bytes[1] > 16) errors.push(label + " has an implausible segment count (" + bytes[1] + ").");
  }
  return errors;
}

// Parses 32-byte partition entries. Returns { errors, entries }.
export function parsePartitionTable(bytes) {
  const errors = [], entries = [];
  if (bytes.length < 32) return { errors: ["Partition table is too small."], entries };
  for (let off = 0; off + 32 <= bytes.length; off += 32) {
    if (bytes[off] === 0xEB && bytes[off + 1] === 0xEB) continue; // MD5 checksum entry
    if (bytes[off] !== 0xAA || bytes[off + 1] !== 0x50) {
      if (off === 0) errors.push("Partition table does not start with the 0xAA50 entry magic.");
      break;
    }
    const dv = new DataView(bytes.buffer, bytes.byteOffset + off, 32);
    entries.push({ type: bytes[off + 2], subtype: bytes[off + 3], offset: dv.getUint32(4, true), size: dv.getUint32(8, true) });
  }
  if (!errors.length && !entries.length) errors.push("Partition table contains no entries.");
  return { errors, entries };
}

// files: { bootloader, partitions, bootapp?, application } as Uint8Array. Returns { errors, warnings }.
export function validateFirmwareSet(files, chipName) {
  const errors = [], warnings = [];
  if (!isS3ChipName(chipName)) errors.push("Connected chip is \"" + (chipName || "unknown") + "\", not an ESP32-S3. Refusing to flash.");
  for (const key of Object.keys(LAYOUT)) {
    const bytes = files[key];
    if (!bytes) continue;
    const spec = LAYOUT[key];
    if (bytes.length > spec.maxSize) {
      errors.push(spec.label + " is " + bytes.length.toLocaleString() + " bytes; the slot at " + hex(spec.address) + " holds at most " + spec.maxSize.toLocaleString() + "." +
        (key === "bootloader" ? " This may be a merged image, which this flasher does not accept." : ""));
    }
  }
  if (files.bootloader) errors.push(...checkImageHeader(files.bootloader, "Bootloader"));
  if (files.application) errors.push(...checkImageHeader(files.application, "Application"));
  if (files.partitions) {
    const { errors: pe, entries } = parsePartitionTable(files.partitions);
    errors.push(...pe);
    if (files.application && !pe.length) {
      const apps = entries.filter(e => e.type === 0x00);
      const slot = apps.find(e => e.offset === LAYOUT.application.address);
      if (!slot) errors.push("Partition table has no app partition at " + hex(LAYOUT.application.address) + ", where the application would be written.");
      else if (files.application.length > slot.size) errors.push("Application (" + files.application.length.toLocaleString() + " bytes) is larger than its partition (" + slot.size.toLocaleString() + " bytes).");
    }
  }
  if (!files.bootapp) warnings.push("Boot app (boot_app0) not selected; OTA data selection will keep whatever is already on the board.");
  return { errors, warnings };
}

// MD5 of a binary string (one byte per char), hex-encoded. esptool-js uses this to verify flash contents after writing.
export function md5BinaryString(str) {
  const K = new Uint32Array(64), S = [7, 12, 17, 22, 5, 9, 14, 20, 4, 11, 16, 23, 6, 10, 15, 21];
  for (let i = 0; i < 64; i++) K[i] = Math.floor(Math.abs(Math.sin(i + 1)) * 2 ** 32) >>> 0;
  const len = str.length, padded = ((len + 8) >>> 6) + 1 << 6, buf = new Uint8Array(padded);
  for (let i = 0; i < len; i++) buf[i] = str.charCodeAt(i) & 0xFF;
  buf[len] = 0x80;
  const dv = new DataView(buf.buffer);
  dv.setUint32(padded - 8, (len * 8) >>> 0, true);
  dv.setUint32(padded - 4, Math.floor(len / 0x20000000), true);
  let a0 = 0x67452301, b0 = 0xEFCDAB89, c0 = 0x98BADCFE, d0 = 0x10325476;
  for (let off = 0; off < padded; off += 64) {
    let a = a0, b = b0, c = c0, d = d0;
    for (let i = 0; i < 64; i++) {
      let f, g;
      if (i < 16) { f = (b & c) | (~b & d); g = i; }
      else if (i < 32) { f = (d & b) | (~d & c); g = (5 * i + 1) % 16; }
      else if (i < 48) { f = b ^ c ^ d; g = (3 * i + 5) % 16; }
      else { f = c ^ (b | ~d); g = (7 * i) % 16; }
      const s = S[(i >> 4) * 4 + (i & 3)];
      const x = (a + f + K[i] + dv.getUint32(off + g * 4, true)) >>> 0;
      a = d; d = c; c = b; b = (b + ((x << s) | (x >>> (32 - s)))) >>> 0;
    }
    a0 = (a0 + a) >>> 0; b0 = (b0 + b) >>> 0; c0 = (c0 + c) >>> 0; d0 = (d0 + d) >>> 0;
  }
  const out = new Uint8Array(16), ov = new DataView(out.buffer);
  [a0, b0, c0, d0].forEach((v, i) => ov.setUint32(i * 4, v, true));
  return Array.from(out, b => b.toString(16).padStart(2, "0")).join("");
}
