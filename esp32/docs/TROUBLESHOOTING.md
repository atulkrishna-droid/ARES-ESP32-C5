# ARES ESP32-C5 Troubleshooting Guide

## Common Issues & Resolutions

### 1. Device Not Detected Over USB
- **Symptom**: `UsbSerialTransport.discover_ports()` returns no Espressif devices.
- **Cause**: Inadequate USB cable (charge-only) or missing USB drivers.
- **Fix**: Use a high-quality data cable connected to the USB Serial/JTAG port. On Windows, verify Device Manager shows "USB JTAG/serial debug unit (COMx)".

### 2. Hardware Profile Mismatch Error
- **Symptom**: Backend rejects device with `HardwareIncompatibleException`.
- **Cause**: Target profile in database does not match connected hardware revision or flash size.
- **Fix**: Verify `board_target` equals `"ESP32-C5-DevKitC-1"` and `bluetooth_classic` is `false`.

### 3. Replay Defense Sequence Error
- **Symptom**: ESP32 returns `INVALID_SEQUENCE`.
- **Cause**: Host sent a message with sequence $\le$ last received sequence.
- **Fix**: Ensure the host transport monotonically increments outbound sequence numbers.
