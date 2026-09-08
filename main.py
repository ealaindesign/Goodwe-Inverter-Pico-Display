import time

# Cold boot stabilization
time.sleep(1.0)

import ntptime
import network
import socket
import struct
import math
import rp2
import machine
import gc

# Set region rules for Australia (channels 1-13)
rp2.country('AU')

from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY_2, PEN_RGB565

# --- HARDWARE INITIALIZATION ---
display = PicoGraphics(display=DISPLAY_PICO_DISPLAY_2, pen_type=PEN_RGB565)
display.set_backlight(0.85)  # 85% Brightness
rtc = machine.RTC()

# Color Palette Definitions
BLACK      = display.create_pen(15, 18, 24)
WHITE      = display.create_pen(245, 245, 250)
GREY       = display.create_pen(120, 130, 145)
DARK_GREY  = display.create_pen(30, 36, 48)
GREEN      = display.create_pen(40, 210, 100)
RED        = display.create_pen(235, 60, 60)
YELLOW     = display.create_pen(255, 210, 0)
CYAN       = display.create_pen(50, 200, 255)

# --- CONFIGURATION ---
WIFI_SSID = "Pi_2.4ghz"
WIFI_PASS = "jollypotato710"
INVERTER_IP = "192.168.1.35"
INVERTER_PORT = 502
UNIT_ID = 0xF7                # 247 in Hex
TARIFF_RATE = 0.17            # $0.17 / kWh Feed-In Tariff

# Location & Time Settings (Sydney / AEST = UTC+10)
FALLBACK_LAT = -34.03
FALLBACK_LON = 151.06
UTC_OFFSET_HOURS = 10.0

# Financial Tariff Lock Baseline
BASELINE_KWH = 0.0
BASELINE_VALUE_AUD = 0.0

current_lat = FALLBACK_LAT
current_lon = FALLBACK_LON

# --- TIME SYNC & LOCAL TIME ---
def sync_time():
    """Fetches atomic UTC time via NTP and sets Pico RTC shifted by GMT offset."""
    for attempt in range(3):
        try:
            ntptime.host = "pool.ntp.org"
            ntptime.timeout = 5
            ntptime.settime()  # Sets hardware RTC to UTC
            
            # Shift RTC by UTC_OFFSET_HOURS to obtain local time
            utc_epoch = time.time()
            local_epoch = utc_epoch + int(UTC_OFFSET_HOURS * 3600)
            lt = time.localtime(local_epoch)
            
            # RTC tuple: (year, month, day, weekday, hours, minutes, seconds, subseconds)
            rtc.datetime((lt[0], lt[1], lt[2], lt[6], lt[3], lt[4], lt[5], 0))
            print(f"[TIME SYNC] Success: {lt[3]:02d}:{lt[4]:02d}:{lt[5]:02d} (GMT {UTC_OFFSET_HOURS:+0.1f})")
            return True
        except Exception as e:
            print(f"[TIME SYNC] Attempt {attempt + 1} failed: {e}")
            time.sleep(1.0)
    return False

def get_local_time():
    """Returns local time tuple directly from Pico RTC."""
    return time.localtime()

def get_sunrise_sunset(local_time):
    year, month, day = local_time[0], local_time[1], local_time[2]
    
    days_in_months = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
        days_in_months[2] = 29
    N = sum(days_in_months[:month]) + day

    rad = math.pi / 180.0
    declination = -23.45 * math.cos(rad * (360 / 365.0) * (N + 10))
    lat_rad = current_lat * rad
    dec_rad = declination * rad
    
    cos_h = -math.tan(lat_rad) * math.tan(dec_rad)
    cos_h = max(-1.0, min(1.0, cos_h))
    h = math.acos(cos_h) / rad / 15.0

    solar_noon_utc = 12.0 - (current_lon / 15.0)
    sunrise_utc = solar_noon_utc - h
    sunset_utc = solar_noon_utc + h

    sunrise_local = (sunrise_utc + UTC_OFFSET_HOURS) % 24
    sunset_local = (sunset_utc + UTC_OFFSET_HOURS) % 24

    return sunrise_local, sunset_local

# --- WI-FI CONNECTION ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active():
        wlan.active(True)
        time.sleep(0.5)

    display.set_pen(BLACK)
    display.clear()
    display.set_pen(WHITE)
    display.text("SOLAR MONITOR", 20, 40, 320, 3)
    display.set_pen(CYAN)
    display.text("Connecting WiFi...", 20, 100, 300, 2)
    display.update()

    if wlan.isconnected():
        return wlan.ifconfig()[0]

    wlan.connect(WIFI_SSID, WIFI_PASS)
    timeout = 10
    while not wlan.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1

    if wlan.isconnected():
        return wlan.ifconfig()[0]
    return None

# --- FINANCIAL CALCULATION ---
def get_lifetime_value(e_total_kwh):
    if e_total_kwh is None:
        return 0.0
    if BASELINE_KWH == 0.0 or e_total_kwh <= BASELINE_KWH:
        return e_total_kwh * TARIFF_RATE
    else:
        new_kwh = e_total_kwh - BASELINE_KWH
        return BASELINE_VALUE_AUD + (new_kwh * TARIFF_RATE)

# --- GLOBAL STATE ---
peak_daily_kwh = 0.0
last_raw_kwh = 0.0
accumulated_kwh = 0.0
last_e_total_kwh = 0.0
is_generating = False
last_reset_day = -1
has_synced_time = False

GRAPH_WIDTH = 280
power_graph = [0.0] * GRAPH_WIDTH

# --- MODBUS QUERY ---
def fetch_goodwe_data():
    global peak_daily_kwh, last_raw_kwh, accumulated_kwh, is_generating, last_e_total_kwh
    
    gc.collect()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    
    try:
        sock.connect((INVERTER_IP, INVERTER_PORT))
        
        # Request 1: Read PV Voltages (Register 0x0200 to 0x0205)
        req_pv = struct.pack(">HHHBBHH", 0x0001, 0x0000, 0x0006, UNIT_ID, 0x03, 0x0200, 0x0006)
        sock.send(req_pv)
        res_pv = sock.recv(1024)
        
        bank_a, bank_b = 0.0, 0.0
        if res_pv and len(res_pv) >= 9 and res_pv[7] == 0x03:
            payload_pv = res_pv[9:]
            bank_a = struct.unpack(">H", payload_pv[4:6])[0] / 10.0
            bank_b = struct.unpack(">H", payload_pv[8:10])[0] / 10.0

        # Request 2: Read Running/System Data (Register 0x0220 to 0x0239)
        req_sys = struct.pack(">HHHBBHH", 0x0002, 0x0000, 0x0006, UNIT_ID, 0x03, 0x0220, 0x001A)
        sock.send(req_sys)
        res_sys = sock.recv(1024)
        
        if res_sys and len(res_sys) >= 9 and res_sys[7] == 0x03:
            payload = res_sys[9:]
            
            raw_e_total = struct.unpack(">I", payload[4:8])[0]
            e_total_kwh = raw_e_total / 10.0
            last_e_total_kwh = e_total_kwh
            
            raw_power_w = struct.unpack(">H", payload[38:40])[0]
            if raw_power_w > 20000:
                raw_power_w = 0
            kw = raw_power_w / 1000.0
            
            current_raw_kwh = struct.unpack(">H", payload[44:46])[0] / 10.0
            
            if last_raw_kwh > 2.0 and current_raw_kwh < (last_raw_kwh - 5.0):
                accumulated_kwh += last_raw_kwh
                peak_daily_kwh = 0.0

            last_raw_kwh = current_raw_kwh
            true_daily_kwh = accumulated_kwh + current_raw_kwh

            if kw > 0.005:
                is_generating = True
                if true_daily_kwh > peak_daily_kwh:
                    peak_daily_kwh = true_daily_kwh
            else:
                is_generating = False
                bank_a = 0.0
                bank_b = 0.0
                if peak_daily_kwh == 0.0 and true_daily_kwh > 0:
                    peak_daily_kwh = true_daily_kwh

            display_kwh = peak_daily_kwh if peak_daily_kwh > 0 else true_daily_kwh
            return kw, display_kwh, bank_a, bank_b, e_total_kwh

    except Exception:
        pass
    finally:
        try:
            sock.close()
        except:
            pass
        gc.collect()
            
    is_generating = False
    return 0.0, peak_daily_kwh, 0.0, 0.0, last_e_total_kwh

# --- ICON DRAWING HELPERS ---
def draw_sun_icon(cx, cy):
    display.set_pen(YELLOW)
    display.circle(cx, cy, 6)
    display.line(cx - 9, cy, cx + 9, cy)
    display.line(cx, cy - 9, cx, cy + 9)
    display.line(cx - 6, cy - 6, cx + 6, cy + 6)
    display.line(cx - 6, cy + 6, cx + 6, cy - 6)

def draw_moon_icon(cx, cy):
    display.set_pen(CYAN)
    display.circle(cx, cy, 7)
    display.set_pen(BLACK)
    display.circle(cx + 3, cy - 2, 6)

# --- UI DRAWING FUNCTIONS ---
def draw_page_dashboard(kw, display_kwh, bank_a, bank_b, e_total_kwh, local_time):
    display.set_pen(BLACK)
    display.clear()

    # --- Header Bar ---
    display.set_pen(DARK_GREY)
    display.rectangle(0, 0, 320, 35)
    display.set_pen(WHITE)
    display.text("SOLAR MONITOR", 10, 9, 150, 2)
    
    # 24h Time
    time_str = f"{local_time[3]:02d}:{local_time[4]:02d}"
    display.set_pen(GREY)
    display.text(time_str, 165, 9, 80, 2)

    # ON / OFF Status Badge
    if is_generating and kw > 0.005:
        display.set_pen(GREEN)
        display.rectangle(245, 4, 70, 27)
        display.set_pen(WHITE)
        display.text("ON", 265, 9, 60, 2)
    else:
        display.set_pen(RED)
        display.rectangle(245, 4, 70, 27)
        display.set_pen(WHITE)
        display.text("OFF", 258, 9, 60, 2)

    # --- Box 1: Current Output (kW) ---
    display.set_pen(DARK_GREY)
    display.rectangle(10, 42, 145, 92)
    display.set_pen(WHITE)
    display.text("CURRENT", 15, 46, 135, 2)
    display.text("OUTPUT (kW)", 15, 60, 135, 2)
    display.set_pen(GREEN if is_generating and kw > 0.005 else RED)
    display.text(f"{kw:.2f}", 18, 82, 130, 4)

    # --- Box 2: Today's Output (kWh) ---
    today_aud = display_kwh * TARIFF_RATE
    display.set_pen(DARK_GREY)
    display.rectangle(165, 42, 145, 92)
    display.set_pen(WHITE)
    display.text("TODAY'S", 168, 46, 140, 2)
    display.text("OUTPUT (kWh)", 168, 60, 200, 2)
    display.set_pen(GREEN)
    display.text(f"{display_kwh:.1f}", 170, 80, 130, 3)
    display.set_pen(WHITE)
    display.text(f"(${today_aud:.2f})", 170, 106, 130, 3)

    # --- Box 3: Lifetime Total (MWh) ---
    mwh = e_total_kwh / 1000.0 if e_total_kwh else 0.0
    lifetime_aud = get_lifetime_value(e_total_kwh)
    display.set_pen(DARK_GREY)
    display.rectangle(10, 140, 145, 92)
    display.set_pen(WHITE)
    display.text("LIFETIME", 15, 144, 135, 2)
    display.text("TOTAL (MWh)", 15, 158, 135, 2)
    display.set_pen(CYAN)
    display.text(f"{mwh:.3f}", 18, 178, 130, 3)
    display.set_pen(WHITE)
    display.text(f"(${lifetime_aud:,.0f})", 18, 204, 130, 3)

    # --- Box 4: System Info (Bank A, Bank B, FIT) ---
    display.set_pen(DARK_GREY)
    display.rectangle(165, 140, 145, 92)
    display.set_pen(WHITE)
    display.text("SYSTEM INFO", 168, 146, 140, 2)

    display.set_pen(GREEN if bank_a > 5.0 else RED)
    display.text(f"Bank A: {bank_a:.0f}V", 170, 168, 130, 2)

    display.set_pen(GREEN if bank_b > 5.0 else RED)
    display.text(f"Bank B: {bank_b:.0f}V", 170, 188, 130, 2)

    display.set_pen(WHITE)
    display.text(f"FIT: ${TARIFF_RATE:.2f}", 170, 210, 130, 1)

    display.update()

def draw_page_graph(current_kw, local_time):
    display.set_pen(BLACK)
    display.clear()

    sunrise_h, sunset_h = get_sunrise_sunset(local_time)
    
    display.set_pen(WHITE)
    display.text("TODAY'S TREND", 10, 8, 160, 2)
    display.set_pen(GREEN if is_generating and current_kw > 0.005 else RED)
    display.text(f"Now: {current_kw:.2f}kW", 175, 8, 135, 2)
    display.set_pen(GREY)
    display.line(10, 28, 310, 28)

    # Graph Dimensions
    gx, gy, gw, gh = 30, 38, GRAPH_WIDTH, 160
    
    peak_p = max(power_graph)
    if peak_p < 0.5:
        max_p = 1.0
    elif peak_p < 2.0:
        max_p = 2.0
    else:
        max_p = math.ceil(peak_p * 1.1)

    display.set_pen(DARK_GREY)
    display.line(gx, gy, gx + gw, gy)
    display.line(gx, gy + int(gh * 0.5), gx + gw, gy + int(gh * 0.5))

    display.set_pen(YELLOW)
    for x in range(gw - 1):
        p1 = power_graph[x]
        p2 = power_graph[x + 1]
        
        y1 = max(gy, min(gy + gh, gy + gh - int((p1 / max_p) * gh)))
        y2 = max(gy, min(gy + gh, gy + gh - int((p2 / max_p) * gh)))
        
        if p1 > 0 or p2 > 0:
            display.line(gx + x, y1, gx + x + 1, y2)

    display.set_pen(WHITE)
    display.line(gx, gy + gh, gx + gw, gy + gh)

    sr_m = int((sunrise_h % 1) * 60)
    ss_m = int((sunset_h % 1) * 60)
    sunrise_str = f"{int(sunrise_h):02d}:{sr_m:02d}"
    sunset_str = f"{int(sunset_h):02d}:{ss_m:02d}"

    draw_sun_icon(15, gy + gh + 18)
    display.set_pen(WHITE)
    display.text(sunrise_str, 32, gy + gh + 14, 60, 1)

    draw_moon_icon(305, gy + gh + 18)
    display.set_pen(WHITE)
    display.text(sunset_str, 260, gy + gh + 14, 60, 1)

    display.set_pen(GREY)
    display.text(f"{max_p:.0f}k" if max_p >= 2 else f"{max_p:.1f}k", 2, gy, 25, 1)
    display.text("0k", 5, gy + gh - 8, 25, 1)

    display.update()

# --- INITIALIZATION ---
connect_wifi()

current_page = 0
PAGE_INTERVAL_MS = 10000
page_swap_timer = time.ticks_ms()

# Render initial frame immediately
draw_page_dashboard(0.0, 0.0, 0.0, 0.0, 0.0, get_local_time())

# --- MAIN LOOP ---
while True:
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        connect_wifi()
    elif not has_synced_time:
        has_synced_time = sync_time()

    local_time = get_local_time()
    c_day, c_hour, c_min = local_time[2], local_time[3], local_time[4]
    
    # 4:00 AM Daily Reset & Re-sync Time
    if c_hour == 4 and c_min == 0 and c_day != last_reset_day:
        peak_daily_kwh = 0.0
        accumulated_kwh = 0.0
        last_raw_kwh = 0.0
        power_graph = [0.0] * GRAPH_WIDTH
        last_reset_day = c_day
        has_synced_time = False

    kw, display_kwh, bank_a, bank_b, e_total_kwh = fetch_goodwe_data()

    if kw is not None:
        sunrise_h, sunset_h = get_sunrise_sunset(local_time)
        current_dec_hour = c_hour + (c_min / 60.0)

        if sunrise_h <= current_dec_hour <= sunset_h:
            day_progress = (current_dec_hour - sunrise_h) / (sunset_h - sunrise_h)
            graph_idx = int(day_progress * (GRAPH_WIDTH - 1))
            graph_idx = max(0, min(GRAPH_WIDTH - 1, graph_idx))
            power_graph[graph_idx] = kw

    live_kw_display = kw if kw is not None else 0.0

    if time.ticks_diff(time.ticks_ms(), page_swap_timer) > PAGE_INTERVAL_MS:
        current_page = (current_page + 1) % 2
        page_swap_timer = time.ticks_ms()

    if current_page == 0:
        draw_page_dashboard(
            live_kw_display,
            display_kwh,
            bank_a,
            bank_b,
            e_total_kwh,
            local_time,
        )
    else:
        draw_page_graph(live_kw_display, local_time)

    print(f"[{c_hour:02d}:{c_min:02d}] Live: {kw:.2f}kW | Day: {display_kwh:.1f}kWh | Bank A: {bank_a:.0f}V Bank B: {bank_b:.0f}V")
        
    time.sleep(2.5)
