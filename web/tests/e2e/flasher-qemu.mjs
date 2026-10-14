// End-to-end flasher test: the real flasher page in Chromium, with navigator.serial replaced by a bridge to a
// QEMU-emulated chip's UART0 on TCP 5555. Not run in CI; see web/tests/e2e/README.md.
// usage: node flasher-qemu.mjs <flasher URL> <esptool-js 0.5.6 bundle.js> <default|custom>
import { chromium } from "playwright";
import net from "node:net";
import { readFileSync } from "node:fs";
const [,, pageUrl, bundlePath, mode] = process.argv;
const sock = net.connect(5555, "127.0.0.1");
await new Promise((ok, bad) => { sock.once("connect", ok); sock.once("error", bad); });
const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
const page = await browser.newPage();
const errors = [];
page.on("pageerror", e => errors.push(e.message));
page.on("dialog", d => { console.log("[dialog] " + d.message().replace(/\n+/g, " | ")); d.accept(); });
await page.route("https://unpkg.com/esptool-js@0.5.6/bundle.js", r => r.fulfill({ body: readFileSync(bundlePath), contentType: "text/javascript" }));
let tx = 0, rx = 0;
if (process.env.RELAX_CHIP) {
  // Emulator-only: QEMU's ESP32-S3 ROM can't do UART download, so tests run against the emulated classic ESP32.
  const src = readFileSync(new URL("../../flasher-validate.js", import.meta.url), "utf8")
    .replace('return /ESP32-S3/i.test(String(name || ""));', "return true;")
    .replace("if (chipId !== ESP32_S3_CHIP_ID)", "if (false)");
  if (!src.includes("return true;") || !src.includes("if (false)")) throw new Error("relax patch did not apply");
  await page.route("**/flasher-validate.js", r => r.fulfill({ body: src, contentType: "text/javascript" }));
}
await page.exposeFunction("__serialWrite", arr => { tx += arr.length; return new Promise(ok => sock.write(Buffer.from(arr), ok)); });
sock.on("data", d => { rx += d.length; if (process.env.DBG) console.log("rx", d.toString("hex").slice(0, 80)); page.evaluate(a => window.__serialPush(a), Array.from(d)).catch(() => {}); });
await page.addInitScript(() => {
  const port = {
    readable: null, writable: null, _ctrl: null,
    async open() {
      this.readable = new ReadableStream({ start: c => { port._ctrl = c; }, cancel: () => { port._ctrl = null; port.readable = null; } }); // per Web Serial spec, cancel clears port.readable
      this.writable = new WritableStream({ write: chunk => window.__serialWrite(Array.from(chunk)), close: () => { port.writable = null; } });
    },
    async close() { try { this._ctrl?.close(); } catch {} this._ctrl = null; this.readable = null; this.writable = null; },
    async setSignals() {}, getInfo() { return { usbVendorId: 0x303a, usbProductId: 0x1001 }; }, async forget() {}
  };
  window.__serialPush = a => { try { port._ctrl?.enqueue(new Uint8Array(a)); } catch {} };
  Object.defineProperty(navigator, "serial", { value: { requestPort: async () => port, getPorts: async () => [port], addEventListener() {} } });
});
await page.goto(pageUrl);
await page.waitForFunction(() => !/Loading/.test(document.getElementById("default-build-status").textContent));
console.log("default build:", await page.textContent("#default-build-status"));
if (mode === "custom") {
  const B = new URL("../../../.pio/build/xiao_esp32s3/", import.meta.url).pathname;
  await page.setInputFiles("#bootloader", B + "bootloader.bin");
  await page.setInputFiles("#partitions", B + "partitions.bin");
  await page.setInputFiles("#bootapp", (process.env.PLATFORMIO_CORE_DIR || process.env.HOME + "/.platformio") + "/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin");
  await page.setInputFiles("#application", B + "firmware.bin");
}
await page.click("#connect");
try {
  await page.waitForFunction(() => /Connected|Could not/.test(document.getElementById("flash-result").textContent), null, { timeout: Number(process.env.CONNECT_MS || 120000) });
} catch (e) { console.log("CONNECT TIMEOUT tx", tx, "rx", rx, "\n" + await page.textContent("#flasher-log")); process.exit(1); }
console.log("status:", await page.textContent("#device-status"));
console.log(await page.textContent("#flasher-log"));
if (await page.isDisabled("#flash")) throw new Error("Flash button still disabled: " + await page.textContent("#flash-result"));
const t0 = Date.now();
await page.click("#flash");
await page.waitForFunction(() => /completed|failed|Cancelled/i.test(document.getElementById("flash-result").textContent), null, { timeout: 600000 });
console.log("result:", await page.textContent("#flash-result"), `(${((Date.now() - t0) / 1000).toFixed(1)}s)`);
console.log("---- page log ----\n" + await page.textContent("#flasher-log"));
console.log("page errors:", errors);
await browser.close(); sock.destroy();
