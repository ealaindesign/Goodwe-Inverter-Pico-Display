# Goodwe-Inverter-Pico-Display
A Raspberry Pi driven data analytics hardware project, which takes data out of most Goodwe solar inverters, and presents it on a range of display options. It reads data packages from the inverter via LAN (Wifi Pico 2 and either LAN or Wifi inverter), decodes them and presents them with numerous data ranges:

1. Daily Page: Presents current output power (kW), output for the day (kWh), and with some user inputs, tells you exact dollar value generation.
2. Lifetime Page: Presents the total lifetime generation, and attributes a dollar value to it based on your feed-in tariff
3. Graph: a daily power generation graph showing kW power generation throughout the day.

There are a couple versions - one runs on an SH1106 OLED screen, scaled for 128x64 pixels, the second runs on a Pimoroni 2" Pico Display Pack (320x240 IPS LCD) running on ST7789 drivers. Both run on a Pico 2W or 2WH (must have wireless connectivity) in a 3D-printed case.
