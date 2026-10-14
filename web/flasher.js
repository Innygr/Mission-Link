import { ESPLoader, Transport } from "https://unpkg.com/esptool-js@0.5.6/bundle.js";

(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const connectButton = $("connect"), disconnectButton = $("disconnect"), flashButton = $("flash");
  const logBox = $("flasher-log"), statusBox = $("device-status");
  const fileIds = ["bootloader", "partitions", "bootapp", "application"];
  let port = null, transport = null, loader = null, connected = false, busy = false, chipName = "";

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
    return ["bootloader", "partitions", "application"].every(id => $(id).files?.length === 1);
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
    if (!("serial" in navigator)) {
      log("Web Serial is not available. Use desktop Chrome or Edge over HTTPS, with a USB data cable.");
      setResult("This browser cannot flash USB serial devices.", "error");
      return;
    }
    try {
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
  async function readFile(id, address) {
    const file = $(id).files?.[0];
    if (!file) return null;
    if (!file.name.toLowerCase().endsWith(".bin")) throw new Error(file.name + " does not look like a .bin file.");
    const bytes = new Uint8Array(await file.arrayBuffer());
    if (!bytes.length) throw new Error(file.name + " is empty.");
    log("Loaded " + file.name + " (" + bytes.length.toLocaleString() + " bytes) → 0x" + address.toString(16).toUpperCase());
    return { data: toBinaryString(bytes), address };
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
      if (!confirm("Flash " + chipName + " with " + files.length + " binary files? This will overwrite firmware. Continue only if these files were built for your exact board.")) {
        log("Flash cancelled before writing.");
        setResult("Cancelled. No files were written.");
        return;
      }
      log("Starting flash operation. Keep USB connected.");
      $("progress-label").textContent = "Writing firmware…";
      await loader.writeFlash({
        fileArray: files,
        flashSize: "keep",
        eraseAll: $("erase-all").checked,
        compress: true,
        reportProgress(fileIndex, written, total) {
          const percent = total > 0 ? Math.min(100, Math.round((written / total) * 100)) : 0;
          $("progress").value = percent;
          $("progress-percent").textContent = percent + "%";
          $("progress-label").textContent = "Writing file " + (fileIndex + 1) + " of " + files.length;
        }
      });
      $("progress").value = 100; $("progress-percent").textContent = "100%";
      $("progress-label").textContent = "Flash write completed";
      log("Flash write completed. Reset the board and check its serial output.");
      setResult("Flash write completed. This confirms the write operation—not that the firmware has booted or radio hardware is working.", "success");
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
      $(id + "-name").textContent = file ? file.name + " · " + file.size.toLocaleString() + " bytes" : "No file selected";
      updateFlashButton();
    });
  }
  connectButton.addEventListener("click", connect);
  disconnectButton.addEventListener("click", disconnect);
  flashButton.addEventListener("click", flash);
  $("clear-log").addEventListener("click", () => { logBox.textContent = "Log cleared."; });
  if (!("serial" in navigator)) {
    statusBox.textContent = "Web Serial unavailable in this browser. Use desktop Chrome or Edge.";
    log("Web Serial is unavailable in this browser. iPhone/iPad Safari cannot run this USB flasher.");
  }
})();