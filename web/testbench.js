(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const connectButton = $("connect"), disconnectButton = $("disconnect");
  const runButton = $("run-tests"), commandInput = $("command");
  const sendButton = $("send-command"), logBox = $("console-log");
  let port = null, reader = null, writer = null, readTask = null;
  let connected = false, running = false, lineBuffer = "", pending = [], lastStatus = null;
  let decoder = new TextDecoder();

  function log(message, kind = "") {
    const stamp = new Date().toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"});
    logBox.textContent += "\n[" + stamp + "] " + String(message);
    logBox.scrollTop = logBox.scrollHeight;
  }
  function setConnected(value) {
    connected = value;
    connectButton.disabled = value;
    disconnectButton.disabled = !value;
    runButton.disabled = !value || running;
    sendButton.disabled = !value || running;
    $("apply-preset").disabled = !value || running;
    $("read-status").disabled = !value || running;
    $("connection-label").textContent = value ? "USB connected" : "Not connected";
    document.querySelector(".header-status .status-dot")?.classList.toggle("active", value);
    $("serial-state").textContent = value ? "●" : "○";
    $("device-status").className = "testbench-status" + (value ? " connected" : "");
    $("device-status").innerHTML = value ? "<strong>USB serial connected</strong>Listening for firmware JSON events at 115200 baud." : "<strong>Not connected</strong>Choose the device in the browser permission dialog.";
  }
  function addResult(name, state, detail) {
    const row = document.createElement("div");
    row.className = "testbench-check " + state;
    const icon = document.createElement("span"); icon.className = "check-icon";
    icon.textContent = state === "pass" ? "✓" : state === "fail" ? "×" : "○";
    const body = document.createElement("div");
    const title = document.createElement("strong"); title.textContent = name;
    const sub = document.createElement("small"); sub.textContent = detail;
    body.append(title, sub); row.append(icon, body); $("test-results").append(row);
  }
  function handleLine(line) {
    if (!line.trim()) return;
    log("< " + line);
    let event;
    try { event = JSON.parse(line); } catch { return; }
    if (event.type === "status") {
      lastStatus = event;
      $("rf-state").textContent = event.rfEnabled === false ? "✓" : event.rfEnabled === true ? "!" : "?";
      if (event.rfEnabled !== false) log("SAFETY WARNING: status did not confirm rfEnabled:false.", "error");
    }
    const idx = pending.findIndex(p => p.match(event));
    if (idx >= 0) {
      const [waiter] = pending.splice(idx, 1);
      clearTimeout(waiter.timer);
      waiter.resolve(event);
    }
  }
  async function readLoop() {
    try {
      while (connected && port?.readable) {
        reader = port.readable.getReader();
        try {
          while (connected) {
            const {value, done} = await reader.read();
            if (done) break;
            if (!value) continue;
            lineBuffer += decoder.decode(value, {stream:true});
            if (lineBuffer.length > 8192) { lineBuffer = ""; log("Input buffer cleared after an oversized response."); }
            const lines = lineBuffer.split(/\r?\n/);
            lineBuffer = lines.pop() || "";
            lines.forEach(handleLine);
          }
        } finally { try { reader.releaseLock(); } catch {} reader = null; }
        break;
      }
    } catch (e) { if (connected) log("Serial reader stopped: " + (e?.message || String(e))); }
  }
  function waitFor(match, timeoutMs = 2500) {
    return new Promise(resolve => {
      const waiter = {match, resolve, timer:null};
      waiter.timer = setTimeout(() => {
        const i = pending.indexOf(waiter);
        if (i >= 0) pending.splice(i, 1);
        resolve(null);
      }, timeoutMs);
      pending.push(waiter);
    });
  }
  async function command(text, matcher, timeoutMs = 2500) {
    if (!writer || !connected) throw new Error("USB device is not connected.");
    const response = waitFor(matcher, timeoutMs);
    log("> " + text);
    await writer.write(new TextEncoder().encode(text + "\n"));
    return response;
  }
  async function connect() {
    if (!("serial" in navigator)) {
      log("Web Serial is unavailable. Open this page in desktop Chrome or Edge over HTTPS.");
      $("device-status").className = "testbench-status error";
      $("device-status").textContent = "This browser cannot connect to USB serial. iOS Safari is not supported for USB flashing/testing.";
      return;
    }
    try {
      port = await navigator.serial.requestPort();
      await port.open({baudRate:115200});
      decoder = new TextDecoder(); lineBuffer = "";
      writer = port.writable.getWriter();
      setConnected(true);
      log("USB serial opened at 115200 baud. Waiting for JSON Lines events.");
      readTask = readLoop();
    } catch (e) {
      log("Connection failed: " + (e?.message || String(e)));
      try { await port?.close(); } catch {}
      port = null; writer = null; setConnected(false);
    }
  }
  async function disconnect() {
    connected = false;
    pending.splice(0).forEach(p => { clearTimeout(p.timer); p.resolve(null); });
    try { await reader?.cancel(); } catch {}
    try { writer?.releaseLock(); } catch {}
    writer = null;
    try { await port?.close(); } catch (e) { log("Close note: " + (e?.message || String(e))); }
    port = null; setConnected(false); log("Disconnected.");
  }
  const isType = type => e => e?.type === type;
  async function runSuite() {
    if (!connected || running) return;
    running = true; runButton.textContent = "Tests running…"; setConnected(true);
    $("test-results").replaceChildren();
    const check = (name, ok, detail) => addResult(name, ok ? "pass" : "fail", detail);
    try {
      let e = await command("status", isType("status"));
      check("Status responds", !!e, e ? "Received a JSON status event." : "Timed out waiting for status.");
      check("RF is confirmed disabled", !!e && e.rfEnabled === false, e ? "rfEnabled=" + String(e.rfEnabled) + ", radioReady=" + String(e.radioReady) : "No status received; cannot confirm radio state.");
      check("Firmware reports radio not ready", !!e && e.radioReady === false, e ? "radioReady=" + String(e.radioReady) : "No status received.");
      e = await command("presets", isType("presets"));
      const ids = Array.isArray(e?.items) ? e.items.map(x => x.id) : [];
      check("Preset list", ["client","repeater","gateway"].every(x => ids.includes(x)), e ? "Received presets: " + (ids.join(", ") || "none") : "Timed out or malformed preset list.");
      e = await command("preset repeater", x => x?.type === "preset" && x.active === "repeater");
      check("Switch to Repeater", !!e, e ? "Firmware acknowledged Repeater." : "No matching preset response.");
      e = await command("status", x => x?.type === "status" && x.preset === "repeater");
      check("Status confirms Repeater", !!e, e ? "Active preset is Repeater." : "Preset did not appear in status.");
      e = await command("preset gateway", x => x?.type === "preset" && x.active === "gateway");
      check("Switch to Gateway", !!e, e ? "Firmware acknowledged Gateway." : "No matching preset response.");
      e = await command("preset client", x => x?.type === "preset" && x.active === "client");
      check("Restore Client preset", !!e, e ? "Firmware acknowledged Client." : "No matching preset response.");
      e = await command("nodes", x => x?.type === "nodes");
      check("Node discovery safely reports not ready", !!e && e.ready === false, e ? "ready=" + String(e.ready) + "; discovery is a placeholder." : "No nodes response.");
      e = await command("send demo bench-test", x => x?.type === "error" && x.code === "not_ready");
      check("Messaging command does not pretend to send", !!e, e ? "Firmware returned not_ready as expected." : "No not_ready response; inspect firmware behavior.");
      if (lastStatus?.rfEnabled !== false) log("WARNING: last status did not confirm RF disabled.");
    } catch (e) {
      addResult("Test suite interrupted", "fail", e?.message || String(e));
    } finally {
      running = false; runButton.textContent = "Run USB test suite"; setConnected(connected);
      const passed = $("test-results").querySelectorAll(".testbench-check.pass").length;
      const failed = $("test-results").querySelectorAll(".testbench-check.fail").length;
      log("Suite finished: " + passed + " passed, " + failed + " failed. This tests USB command behavior only, not RF mesh.");
    }
  }
  async function sendManual() {
    const text = commandInput.value.trim();
    if (!text || !connected || running) return;
    const event = await command(text, () => true, 2500);
    if (!event) log("No JSON event received within timeout.");
    commandInput.value = "";
  }
  $("connect").addEventListener("click", connect);
  $("disconnect").addEventListener("click", disconnect);
  runButton.addEventListener("click", runSuite);
  sendButton.addEventListener("click", sendManual);
  commandInput.addEventListener("keydown", e => { if (e.key === "Enter") sendManual(); });
  $("apply-preset").addEventListener("click", async () => {
    const preset = $("preset-select").value;
    const e = await command("preset " + preset, x => x?.type === "preset" && x.active === preset);
    log(e ? "Preset changed to " + preset + "." : "Preset change was not confirmed.");
  });
  $("read-status").addEventListener("click", async () => {
    const e = await command("status", isType("status"));
    if (!e) log("Status request timed out.");
  });
  document.querySelectorAll("[data-command]").forEach(b => b.addEventListener("click", () => {
    commandInput.value = b.dataset.command; commandInput.focus();
  }));
  $("clear-log").addEventListener("click", () => { logBox.textContent = "Log cleared."; });
  $("clear-results").addEventListener("click", () => {
    $("test-results").replaceChildren();
    addResult("Waiting to test", "pending", "Connect your board and run the test suite.");
  });
  if (!("serial" in navigator)) {
    $("device-status").className = "testbench-status error";
    $("device-status").textContent = "Web Serial unavailable in this browser. Use desktop Chrome or Edge over HTTPS.";
  }
})();