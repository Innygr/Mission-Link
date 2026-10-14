import { readFile } from "node:fs/promises";
import path from "node:path";
import { validateFirmwareSet } from "../flasher-validate.js";

const directory = path.resolve(process.argv[2] ?? "web/firmware");
const names = {
  bootloader: "bootloader.bin",
  partitions: "partitions.bin",
  bootapp: "boot_app0.bin",
  application: "firmware.bin"
};

try {
  const entries = await Promise.all(
    Object.entries(names).map(async ([key, name]) => [key, new Uint8Array(await readFile(path.join(directory, name)))])
  );
  const files = Object.fromEntries(entries);
  const result = validateFirmwareSet(files, "ESP32-S3");

  for (const warning of result.warnings) console.warn("WARN: " + warning);
  if (result.errors.length) {
    for (const error of result.errors) console.error("ERROR: " + error);
    process.exitCode = 1;
  } else {
    console.log("Built firmware set passes flasher preflight checks:");
    for (const [key, name] of Object.entries(names)) {
      console.log("  " + name + ": " + files[key].byteLength.toLocaleString() + " bytes");
    }
  }
} catch (error) {
  console.error("Could not validate built firmware set: " + (error?.message ?? String(error)));
  process.exitCode = 1;
}
