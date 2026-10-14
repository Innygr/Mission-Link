(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const connectButton = $("connect-button"), disconnectButton = $("disconnect-button");
  const sendButton = $("send-button"), commandInput = $("command");
  const logBox = $("console-log"), connectionLabel = $("connection-label");
  let port = null, reader = null, writer = null, keepReading = false, decoder = new TextDecoder(), serialTextBuffer = "";
  function log(message, kind = "") {
    const row = document.createElement("p");
    const time = document.createElement("span");
    time.className = "log-time";
    time.textContent = new Date().toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"});
    row.append(time, document.createTextNode(message));
    if (kind) row.classList.add(kind);
    logBox.append(row);
    logBox.scrollTop = logBox.scrollHeight;
  }
  function setConnected(connected) {
    connectionLabel.textContent = connected ? "USB connected" : "Not connected";
    document.querySelector(".header-status .status-dot").classList.toggle("active", connected);
    connectButton.disabled = connected;
    disconnectButton.disabled = !connected;
    sendButton.disabled = !connected;
    $("transport-detail").textContent = connected ? "Connected through Web Serial. RF remains disabled in this firmware." : "Waiting for a local connection";
  }
  function handleFirmwareLine(line) {
    try {
      const event = JSON.parse(line);
      if (event.type === "status") {
        const rf = event.rfEnabled ? "enabled" : "disabled";
        $("firmware-status").textContent = "Firmware " + event.firmware + " · RF " + rf;
        $("node-count").textContent = event.knownNodeCount ?? "—";
        log("Status received: firmware " + event.firmware + ", RF " + rf + ".");
        return;
      }
      if (event.type === "nodes") {
        $("node-count").textContent = Array.isArray(event.items) ? event.items.length : "—";
        log("Node discovery is not ready yet.");
        return;
      }
      if (event.type === "error") {
        log("Error [" + event.code + "]: " + event.message);
        return;
      }
      if (event.type === "boot" || event.type === "ready") {
        $("firmware-status").textContent = "Firmware " + event.firmware + " · RF disabled";
      }
      log(line);
    } catch {
      log(line);
    }
  }
  async function connect() {
    if (!("serial" in navigator)) {
      log("Web Serial is unavailable in this browser. Try a supported desktop Chromium browser, or use the native iOS app for Bluetooth.", "log-muted");
      $("transport-detail").textContent = "This browser cannot access USB serial.";
      return;
    }
    try {
      port = await navigator.serial.requestPort();
      await port.open({baudRate:115200});
      writer = port.writable.getWriter();
      serialTextBuffer = "";
      decoder = new TextDecoder();
      setConnected(true);
      log("USB serial opened at 115200 baud.");
      keepReading = true;
      readLoop();
    } catch (error) {
      log("Connection failed: " + (error?.message || String(error)));
      if (port) { try { await port.close(); } catch {} }
      port = null; writer = null; setConnected(false);
    }
  }
  async function readLoop() {
    while (port?.readable && keepReading) {
      try {
        reader = port.readable.getReader();
        while (keepReading) {
          const {value, done} = await reader.read();
          if (done) break;
          if (value) {
            serialTextBuffer += decoder.decode(value, {stream:true});
            const completeLines = serialTextBuffer.split(/\r?\n/);
            serialTextBuffer = completeLines.pop() ?? "";
            completeLines.filter(Boolean).forEach(line => handleFirmwareLine(line));
          }
        }
      } catch (error) {
        if (keepReading) log("Serial read error: " + (error?.message || String(error)));
      } finally {
        reader?.releaseLock(); reader = null;
      }
      break;
    }
  }
  async function disconnect() {
    keepReading = false;
    try { if (reader) await reader.cancel(); } catch {}
    try { if (writer) { writer.releaseLock(); writer = null; } } catch {}
    try { if (port) await port.close(); } catch (error) { log("Close warning: " + error.message); }
    if (serialTextBuffer.trim()) handleFirmwareLine(serialTextBuffer.trim());
    serialTextBuffer = "";
    port = null; setConnected(false); log("USB serial disconnected.");
  }
  async function sendCommand() {
    const command = commandInput.value.trim();
    if (!command || !writer) return;
    try {
      await writer.write(new TextEncoder().encode(command + "\n"));
      log("> " + command);
      commandInput.value = "";
    } catch (error) { log("Write failed: " + (error?.message || String(error))); }
  }
  connectButton.addEventListener("click", connect);
  disconnectButton.addEventListener("click", disconnect);
  sendButton.addEventListener("click", sendCommand);
  commandInput.addEventListener("keydown", (event) => { if (event.key === "Enter") sendCommand(); });
  document.querySelectorAll("[data-command]").forEach(button => button.addEventListener("click", () => {
    commandInput.value = button.dataset.command;
    commandInput.focus();
  }));
  $("clear-log").addEventListener("click", () => { logBox.replaceChildren(); log("Console cleared."); });
  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch(() => {}));
  }
  if (!("serial" in navigator)) {
    $("transport-detail").textContent = "USB serial is unavailable in this browser. iOS users need the native app for BLE.";
  }
})();