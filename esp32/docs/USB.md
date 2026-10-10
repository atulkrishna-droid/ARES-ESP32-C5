# ARES ESP32-C5 USB Architecture

## 1. Hardware Architecture
The ESP32-C5 includes a built-in **USB Serial/JTAG Controller** (Full-Speed 12 Mbps, USB 2.0 compatible):
- **Vendor ID (VID)**: `0x303A` (Espressif Systems)
- **Product ID (PID)**: `0x1001` (ESP32-C5 USB Serial/JTAG)
- **Endpoint Types**: CDC-ACM communications & JTAG debugging.
- **Port Capabilities**: Full-Speed USB (12 Mbps). It is **not** high-speed (480 Mbps) or USB 3.x.

## 2. Host Communication
- Default baudrate: `115200` (virtual CDC baud rate transparent over USB).
- Line Delimiter: `\n` (LF) or `\r\n` (CRLF).
- Buffer Size: 4096-byte ring buffers on RX and TX.
- Dedicated FreeRTOS background task `ares_usb_rx` ensures zero dropped frames without blocking execution tasks.
