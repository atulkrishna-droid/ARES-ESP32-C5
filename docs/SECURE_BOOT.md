# ARES ESP32-C5 Secure Boot & Flash Encryption Specification

## 1. Development Mode vs Production Hardening
During Phase 2 firmware development, **irreversible eFuse burning must NOT be executed**. Development boards must remain recoverable and re-flashable via USB Serial/JTAG.

- **Development Mode (Current)**:
  - Secure storage partitioned via NVS (`ares_sec`).
  - HMAC secret loaded dynamically or provisioned via authorized pairing.
  - Flash and eFuses remain unlocked to allow rapid debugging and iteration.

- **Production Mode (Future Hardware Provisioning)**:
  - **Secure Boot V2**: RSA-3072 or ECDSA-P256 signature verification enforced by hardware boot ROM.
  - **Flash Encryption**: XTS-AES-256 hardware encryption of SPI flash contents.
  - **NVS Encryption**: Encrypted NVS partition with key stored in protected eFuse block.
  - **JTAG / Serial Download Mode Disabling**: Permanently disables physical bus readout.

## 2. Recovery Implications
Burning production eFuses permanently disables plaintext firmware flashing. Once locked:
- Only binaries signed with the designated private key can boot.
- If the private signing key is lost, the hardware is permanently bricked.
- Production locking will occur only in Phase 4/5 after firmware stabilization.
