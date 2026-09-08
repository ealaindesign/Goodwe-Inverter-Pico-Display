# GoodWe Desktop Solar Monitor

A live, low-power desktop solar monitor for GoodWe inverters built using the **Raspberry Pi Pico 2 W / 2 WH** and the **Pimoroni Pico Display Pack 2.0"**.

Features a 320x240 color IPS dashboard that cycles between:
1. **Real-time Telemetry Dashboard**: Instantaneous solar output (kW), today's total production (kWh) and accrued feed-in earnings, lifetime generation (MWh) and valuation, live DC string voltages (Bank A & Bank B), and generation state (ON/OFF).
2. **Solar Trend Graph**: A daily production curve mapped dynamically between calculated local sunrise and sunset times.

---

## Hardware Requirements

| Component | Description |
| :--- | :--- |
| **Microcontroller** | **Raspberry Pi Pico 2 W** or **Pico 2 WH** (also backwards compatible with Pico W) |
| **Display** | [Pimoroni Pico Display Pack 2.0" (320x240 IPS ST7789)](https://shop.pimoroni.com/products/pico-display-pack-2-0) |
| **Enclosure** | 3D-printed desktop enclosure/stand designed for the Pico + Display Pack 2.0 |
| **Power** | 5V USB power adapter and cable |

---

## Supported Inverters

This project communicates directly with GoodWe residential inverters over **Modbus TCP** on port `502` (Unit ID `247` / `0xF7`). It reads registers `0x0200` (DC string voltages) and `0x0220` (System & running data).

Compatible with GoodWe string and hybrid inverters equipped with a Wi-Fi or LAN communication dongle:
* **GoodWe DNS Series** (e.g., GW3000D-NS, GW5000D-NS)
* **GoodWe MS Series**
* **GoodWe XS Series**
* **GoodWe SDT G2 / SMT Series**
* **GoodWe EH / ET Hybrid Series** *(Note: Battery storage registers are not polled in this release)*

---

## Network Prerequisites

1. **2.4 GHz Wi-Fi Subnet**:
   * Both the Raspberry Pi Pico and the GoodWe Wi-Fi dongle operate exclusively on **2.4 GHz (802.11 b/g/n)** networks. Ensure both devices are connected to the same local network subnet.
2. **Static / Reserved IP for the Inverter**:
   * Assign a fixed/reserved IP address to your GoodWe inverter in your home router settings (e.g., `192.168.1.35`) so the Pico does not lose connection when DHCP leases renew.

---

Getting Started

1. Flash MicroPython Firmware
You must use Pimoroni's MicroPython firmware build, which includes the `picographics` drivers:
1. Pull the attached firmware build from the zip (filename rpi_pico2_w-v1.26.1-micropython.uf2)
2. Hold down the **BOOTSEL** button on your Pico while plugging it into your computer via USB.
3. Drag and drop the downloaded `.uf2` file onto the mounted `RPI-RP2` drive. The Pico will reboot automatically.

# 2. Generate Configuration (`config.py`)

We provide a graphical setup wizard to configure your network, location, and tariffs without editing code manually.

#### Launching the Wizard:
* **Windows**: Double-click `run_setup.bat` (or double-click `setup_wizard.pyw`).
* **macOS / Linux**: Double-click `run_setup.command` (or run `python3 setup_wizard.pyw`).

#### Configuration Fields:
* **Country / Wi-Fi Region**: Select your country from the list (~240 regions). This automatically sets the radio channel regulatory domain (`rp2.country`) and default currency symbol.
* **Time Zone (GMT Offset)**: Choose your local GMT offset from the dropdown (e.g., `GMT +10:00 (Sydney, Melbourne, Brisbane)`). The Pico will fetch atomic time via NTP and shift it accordingly.
* **Google Maps Coordinates**: Open Google Maps, right-click your roof/location, and click the coordinates to copy them (e.g., `-33.8688, 151.2093`). Paste this string into the **Google Maps Right-Click** box and click **Paste/Apply**.
* **Wi-Fi & Inverter Settings**: Enter your 2.4 GHz Wi-Fi SSID, password, and the static IP of your GoodWe inverter.
* **Feed-In Tariff**: Enter your feed-in rate per kWh (e.g., `0.17` for 17¢/kWh).
* **Baseline Tariff Lock (Optional)**: If you were on an introductory feed-in promotional tariff that expired or changed after a certain production threshold, check this box and enter your baseline kWh and accumulated value. Otherwise, leave it unchecked.

Click **Generate config.py**. The file will be created in your folder.

---

3. Deploy to the Pico

Using an IDE like [Thonny](https://thonny.org/) or [mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html):
1. Connect your Pico to your computer.
2. Transfer both **`config.py`** and **`main.py`** to the root directory (`/`) of your Pico.
3. Reset or power cycle the device.

---

## Enclosure & 3D Printing

You can 3D print any standard enclosure designed for the Raspberry Pi Pico + Pimoroni Pico Display Pack 2.0". A desktop stand tilted at 30° to 45° provides optimal visibility for daytime monitoring.

---

## Troubleshooting

* **Screen shows `CONFIG MISSING!`**:
  Make sure you ran `setup_wizard.pyw` and copied both `config.py` and `main.py` to the Pico.
* **Stuck on `Connecting WiFi...`**:
  Verify that your Wi-Fi SSID is broadcasting on 2.4 GHz (the Pico does not support 5 GHz networks) and that your password is correct.
* **Readings show 0 kW or OFF during the day**:
  Ensure the inverter IP address set in `config.py` matches your inverter's current local IP and that port `502` is accessible on your local network.
