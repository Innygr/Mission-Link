import { validateFirmwareSet, md5BinaryString } from "./flasher-validate.js";

const ESPTOOL_URL = "https://unpkg.com/esptool-js@0.5.6/bundle.js";

(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const connectButton = $("connect"), disconnectButton = $("disconnect"), flashButton = $("flash");
  const logBox = $("flasher-log"), statusBox = $("device-status");
  const fileIds = ["bootloader", "partitions", "bootapp", "application"];
  let ESPLoader = null, Transport = null, port = null, transport = null, loader = null, connected = false, busy = false, chipName = "";
  const defaultFiles = Object.create(null);
  const defaultPaths = {
    bootloader: "./firmware/bootloader.bin",
    partitions: "./firmware/partitions.bin",
    bootapp: "./firmware/boot_app0.bin",
    application: "./firmware/firmware.bin"
  };

  function log(message) {
    const time = new Date().toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"});
    logBox.textContent += "\n[" + time + "] " + String(message);
    logBox.scrollTop = logBox.scrollHeight;
  }
  function setResult(message, kind = "") {
    const el = $("flash-result");
    el.textContent = message;
    el.className = "flash-result" + (kind ? " " + kind : "");
  }
  function selectedFilesReady() {
    return ["bootloader", "partitions", "application"].every(id =>
      $(id).files?.length === 1 || Boolean(defaultFiles[id])
    );
  }
  function activeFileName(id) {
    return $(id).files?.[0]?.name || defaultFiles[id]?.name || "";
  }
  function refreshFileLabels() {
    for (const id of fileIds) {
      const file = $(id).files?.[0];
      const fallback = defaultFiles[id];
      $(id + "-name").textContent = file
        ? file.name + " · " + file.size.toLocaleString() + " bytes (custom)"
        : fallback
          ? fallback.name + " · " + fallback.bytes.length.toLocaleString() + " bytes (official build)"
          : "No file selected";
    }
    updateFlashButton();
  }
  async function loadDefaultFirmware() {
    const status = $("default-build-status");
    const button = $("load-defaults");
    button.disabled = true;
    status.textContent = "Loading official MissionLink build…";
    try {
      const entries = await Promise.all(Object.entries(defaultPaths).map(async ([id, url]) => {
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) throw new Error(url + " returned HTTP " + response.status);
        const bytes = new Uint8Array(await response.arrayBuffer());
        if (!bytes.length) throw new Error(url + " is empty");
        return [id, { name: url.split("/").pop(), bytes }];
      }));
      for (const [id, file] of entries) defaultFiles[id] = file;
      refreshFileLabels();
      status.textContent = "Official build loaded. Files are from this repository's CI build.";
      log("Loaded the default MissionLink firmware set from this site's same-origin firmware directory.");
      log("Default files: bootloader.bin, partitions.bin, boot_app0.bin, firmware.bin.");
      setResult("Official MissionLink build loaded. The flasher will validate it before writing.", "success");
    } catch (error) {
      status.textContent = "Could not load the official build; choose files manually.";
      log("Default firmware load failed: " + (error?.message || String(error)));
      refreshFileLabels();
    } finally {
      button.disabled = false;
    }
  }
  function updateFlashButton() {
    flashButton.disabled = !connected || busy || !selectedFilesReady();
  }
  function setConnected(value) {
    connected = value;
    connectButton.disabled = value || busy;
    disconnectButton.disabled = !value || busy;
    statusBox.textContent = value ? "Connected to " + (chipName || "ESP32-S3") + " bootloader" : "No device connected";
    statusBox.classList.toggle("connected", value);
    updateFlashButton();
  }
  function terminal() {
    return {
      clean() {},
      writeLine(data) { log(data); },
      write(data) { if (data) logBox.textContent += String(data); logBox.scrollTop = logBox.scrollHeight; }
    };
  }
  async function connect() {
    refreshFileLabels();
    if (!("serial" in navigator)) {
      log("Web Serial is not available. Use desktop Chrome or Edge over HTTPS, with a USB data cable.");
      setResult("This browser cannot flash USB serial devices.", "error");
      return;
    }
    try {
      if (!ESPLoader) {
        // Loaded on demand so a blocked CDN shows an error instead of leaving the page inert.
        ({ ESPLoader, Transport } = await import(ESPTOOL_URL));
      }
      port = await navigator.serial.requestPort();
      transport = new Transport(port);
      loader = new ESPLoader({ transport, baudrate: 460800, terminal: terminal() });
      setResult("Connecting to bootloader…");
      chipName = await loader.main();
      log("Connected chip: " + chipName);
      setConnected(true);
      setResult("Connected to " + chipName + ". Select build files to continue.");
    } catch (error) {
      log("Connection failed: " + (error?.message || String(error)));
      setResult("Could not connect. Try holding BOOT while connecting the board, then retry.", "error");
      try { await transport?.disconnect(); } catch {}
      transport = null; loader = null; port = null; setConnected(false);
    }
  }
  async function disconnect() {
    if (busy) return;
    try { if (transport) await transport.disconnect(); }
    catch (error) { log("Disconnect note: " + (error?.message || String(error))); }
    transport = null; loader = null; port = null; chipName = "";
    setConnected(false);
    log("Device disconnected.");
    setResult("Disconnected.");
  }
  function toBinaryString(bytes) {
    let result = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      result += String.fromCharCode(...bytes.subarray(i, Math.min(i + chunk, bytes.length)));
    }
    return result;
  }
  async function sha256(bytes) {
    if (!globalThis.crypto?.subtle) return "unavailable";
    const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
    return Array.from(digest, b => b.toString(16).padStart(2, "0")).join("");
  }
  async function readFile(id, address) {
    const selected = $(id).files?.[0];
    const source = selected
      ? { name: selected.name, bytes: new Uint8Array(await selected.arrayBuffer()) }
      : defaultFiles[id];
    if (!source) return null;
    if (!source.name.toLowerCase().endsWith(".bin")) throw new Error(source.name + " does not look like a .bin file.");
    const bytes = source.bytes;
    if (!bytes.length) throw new Error(source.name + " is empty.");
    log("Loaded " + source.name + " (" + bytes.length.toLocaleString() + " bytes) → 0x" + address.toString(16).toUpperCase() + (selected ? " (custom)" : " (official default)"));
    return { data: toBinaryString(bytes), address, bytes, name: source.name };
  }
  async function flash() {
    if (!connected || busy) return;
    if (!selectedFilesReady()) {
      setResult("Choose bootloader, partition table, and application binaries first.", "error");
      return;
    }
    busy = true; updateFlashButton(); connectButton.disabled = true; disconnectButton.disabled = true;
    $("progress").value = 0; $("progress-percent").textContent = "0%";
    $("progress-label").textContent = "Preparing files…"; setResult("");
    try {
      const files = [];
      const bootloader = await readFile("bootloader", 0x0000);
      const partitions = await readFile("partitions", 0x8000);
      const bootapp = await readFile("bootapp", 0xE000);
      const application = await readFile("application", 0x10000);
      if (bootloader) files.push(bootloader);
      if (partitions) files.push(partitions);
      if (bootapp) files.push(bootapp);
      if (application) files.push(application);
      if (files.length < 3) throw new Error("Required firmware files are missing.");
      const check = validateFirmwareSet({
        bootloader: bootloader?.bytes, partitions: partitions?.bytes, bootapp: bootapp?.bytes, application: application?.bytes
      }, chipName);
      for (const w of check.warnings) log("Note: " + w);
      if (check.errors.length) {
        check.errors.forEach(e => log("Pre-flash check failed: " + e));
        throw new Error("Pre-flash checks failed; nothing was written. " + check.errors[0]);
      }
      log("Pre-flash header checks passed (image magic, ESP32-S3 chip ID, slot sizes, app partition). These do not prove the build is correct for your board.");
      const summary = [];
      for (const f of files) {
        const hash = await sha256(f.bytes);
        log("SHA-256 " + f.name + ": " + hash);
        summary.push("0x" + f.address.toString(16).toUpperCase() + "  " + f.name + "  (" + f.bytes.length.toLocaleString() + " bytes)");
      }
      const eraseAll = $("erase-all").checked;
      if (!confirm("Flash " + chipName + " with " + files.length + " binary files?\n\n" + summary.join("\n") + "\n\nThis will overwrite firmware. Continue only if these files were built for your exact board.")) {
        log("Flash cancelled before writing.");
        setResult("Cancelled. No files were written.");
        return;
      }
      if (eraseAll && !confirm("ERASE ALL FLASH first? This permanently removes existing settings and stored data on the board.")) {
        log("Flash cancelled at erase confirmation.");
        setResult("Cancelled. No files were written.");
        return;
      }
      log("Starting flash operation. Keep USB connected.");
      $("progress-label").textContent = "Writing firmware…";
      await loader.writeFlash({
        fileArray: files,
        // FlashOptions requires all three. Passing "keep" explicitly leaves the bootloader header untouched by contract,
        // instead of relying on esptool-js 0.5.6's header check happening to bail out on undefined mode/freq.
        flashSize: "keep",
        flashMode: "keep",
        flashFreq: "keep",
        eraseAll,
        compress: true,
        // Enables esptool-js's read-back MD5 comparison after each file is written.
        calculateMD5Hash: md5BinaryString,
        reportProgress(fileIndex, written, total) {
          const percent = total > 0 ? Math.min(100, Math.round((written / total) * 100)) : 0;
          $("progress").value = percent;
          $("progress-percent").textContent = percent + "%";
          $("progress-label").textContent = "Writing file " + (fileIndex + 1) + " of " + files.length;
        }
      });
      $("progress").value = 100; $("progress-percent").textContent = "100%";
      $("progress-label").textContent = "Flash write completed";
      log("Flash write completed and each file's MD5 matched the flash contents. Press RESET on the board (or replug USB) and check its serial output.");
      setResult("Flash write completed and verified by MD5 read-back. This confirms the write operation—not that the firmware has booted or radio hardware is working.", "success");
    } catch (error) {
      log("Flash failed: " + (error?.message || String(error)));
      setResult("Flash failed: " + (error?.message || String(error)), "error");
      $("progress-label").textContent = "Flash failed";
    } finally {
      busy = false;
      connectButton.disabled = connected;
      disconnectButton.disabled = !connected;
      updateFlashButton();
    }
  }

  for (const id of fileIds) {
    $(id).addEventListener("change", () => {
      const file = $(id).files?.[0];
      refreshFileLabels();
    });
  }
  navigator.serial?.addEventListener("disconnect", () => {
    if (!connected) return;
    log(busy ? "USB device disappeared during flashing. The board may be left with incomplete firmware; reconnect, hold BOOT, and flash again." : "USB device was unplugged.");
    if (!busy) { transport = null; loader = null; port = null; chipName = ""; setConnected(false); setResult("Device unplugged."); }
  });
  $("load-defaults").addEventListener("click", loadDefaultFirmware);
  connectButton.addEventListener("click", connect);
  disconnectButton.addEventListener("click", disconnect);
  flashButton.addEventListener("click", flash);
  $("clear-log").addEventListener("click", () => { logBox.textContent = "Log cleared."; });
  if (!("serial" in navigator)) {
    statusBox.textContent = "Web Serial unavailable in this browser. Use desktop Chrome or Edge.";
    log("Web Serial is unavailable in this browser. iPhone/iPad Safari cannot run this USB flasher.");
  }
  // Load the official firmware immediately; connecting the board is a separate step.
  refreshFileLabels();
  void loadDefaultFirmware();
})();