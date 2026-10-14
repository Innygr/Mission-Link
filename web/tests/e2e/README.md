# Flasher end-to-end test (QEMU)

Runs the real `flasher.html` in Chromium against an emulated chip. `navigator.serial` is replaced with a bridge to the emulator's UART0 on TCP port 5555, so esptool-js does the real sync, stub upload, compressed writes and MD5 read-back.

**Limitation:** Espressif's QEMU (fork at `febae18`) does not support UART download mode for the ESP32-S3: the ROM panics on the first sync packet, and Python esptool fails against it too. The test therefore uses the emulated **classic ESP32** (`-M esp32`). With `RELAX_CHIP=1`, it serves a copy of `flasher-validate.js` with only the ESP32-S3 chip checks disabled. Without `RELAX_CHIP`, the same run should end with the flasher refusing the chip and writing nothing. Neither run says anything about S3-specific behaviour or real USB hardware.

```sh
# Build Espressif QEMU from https://github.com/espressif/qemu (xtensa-softmmu), then:
python3 -c "open('flash4.bin','wb').write(b'\xff'*4*1024*1024)"
qemu-system-xtensa -M esp32 -display none -drive file=flash4.bin,if=mtd,format=raw \
  -global driver=esp32.gpio,property=strap_mode,value=0x0f -serial tcp:127.0.0.1:5555,server=on,wait=off &
pio run -e xiao_esp32s3   # then stage web/firmware/ as in .github/workflows/deploy-web.yml
python3 -m http.server 8123 --directory web &
npm install --no-save playwright  # or any install the ESM import "playwright" resolves to
npm pack esptool-js@0.5.6 && tar xzf esptool-js-0.5.6.tgz
RELAX_CHIP=1 node web/tests/e2e/flasher-qemu.mjs http://localhost:8123/flasher.html package/bundle.js default
```

Stop QEMU before comparing `flash4.bin` against the files in `web/firmware/` at 0x0, 0x8000, 0xE000 and 0x10000.
