import tkinter as tk
from tkinter import ttk, messagebox
import re

# Comprehensive list of GMT offsets
TIMEZONE_OFFSETS = [
    ("GMT -12:00 (Eniwetok, Kwajalein)", -12.0),
    ("GMT -11:00 (Midway Island, Samoa)", -11.0),
    ("GMT -10:00 (Hawaii, Honolulu)", -10.0),
    ("GMT -09:00 (Alaska)", -9.0),
    ("GMT -08:00 (Pacific Time - US & Canada)", -8.0),
    ("GMT -07:00 (Mountain Time - US & Canada)", -7.0),
    ("GMT -06:00 (Central Time - US & Canada, Mexico)", -6.0),
    ("GMT -05:00 (Eastern Time - US & Canada)", -5.0),
    ("GMT -04:00 (Atlantic Time - Canada, Caracas)", -4.0),
    ("GMT -03:30 (Newfoundland)", -3.5),
    ("GMT -03:00 (Brazil, Buenos Aires)", -3.0),
    ("GMT -02:00 (Mid-Atlantic)", -2.0),
    ("GMT -01:00 (Azores, Cape Verde)", -1.0),
    ("GMT +00:00 (Western European Time, London, Lisbon)", 0.0),
    ("GMT +01:00 (Central European Time, Berlin, Paris, Rome)", 1.0),
    ("GMT +02:00 (Eastern European Time, Athens, Cairo)", 2.0),
    ("GMT +03:00 (Baghdad, Riyadh, Moscow)", 3.0),
    ("GMT +03:30 (Tehran)", 3.5),
    ("GMT +04:00 (Abu Dhabi, Muscat, Baku)", 4.0),
    ("GMT +04:30 (Kabul)", 4.5),
    ("GMT +05:00 (Islamabad, Karachi, Tashkent)", 5.0),
    ("GMT +05:30 (India Standard Time - Mumbai, New Delhi)", 5.5),
    ("GMT +05:45 (Kathmandu)", 5.75),
    ("GMT +06:00 (Almaty, Dhaka)", 6.0),
    ("GMT +06:30 (Yangon / Cocos Islands)", 6.5),
    ("GMT +07:00 (Bangkok, Hanoi, Jakarta)", 7.0),
    ("GMT +08:00 (Perth, Beijing, Singapore, Hong Kong)", 8.0),
    ("GMT +08:45 (Eucla)", 8.75),
    ("GMT +09:00 (Tokyo, Seoul)", 9.0),
    ("GMT +09:30 (Adelaide, Darwin)", 9.5),
    ("GMT +10:00 (Sydney, Melbourne, Brisbane, Guam)", 10.0),
    ("GMT +10:30 (Lord Howe Island)", 10.5),
    ("GMT +11:00 (Solomon Islands, Vladivostok)", 11.0),
    ("GMT +12:00 (Auckland, Wellington, Fiji)", 12.0),
    ("GMT +12:45 (Chatham Islands)", 12.75),
    ("GMT +13:00 (Nuku'alofa, Samoa)", 13.0),
    ("GMT +14:00 (Kiritimati)", 14.0),
]

COUNTRY_CODES = [
    ("AU - Australia", "AU", "$"),
    ("US - United States", "US", "$"),
    ("GB - United Kingdom", "GB", "£"),
    ("NZ - New Zealand", "NZ", "$"),
    ("DE - Germany", "DE", "€"),
    ("NL - Netherlands", "NL", "€"),
    ("ES - Spain", "ES", "€"),
    ("IT - Italy", "IT", "€"),
    ("ZA - South Africa", "ZA", "R"),
    ("Custom / Other", "XX", "$")
]

def on_country_change(event=None):
    sel = cb_country.current()
    if sel >= 0:
        _, code, curr = COUNTRY_CODES[sel]
        entry_rp2.delete(0, tk.END)
        entry_rp2.insert(0, code)
        entry_curr.delete(0, tk.END)
        entry_curr.insert(0, curr)

def parse_google_maps_coords(event=None):
    """Parses 'lat, lon' pasted directly from Google Maps right-click."""
    raw = entry_gmaps.get().strip()
    if not raw:
        return
    # Match patterns like "-33.8688, 151.2093" or "-33.8688,151.2093"
    match = re.match(r"^([-+]?\d*\.?\d+)[,\s]+([-+]?\d*\.?\d+)$", raw)
    if match:
        lat, lon = match.group(1), match.group(2)
        entry_lat.delete(0, tk.END)
        entry_lat.insert(0, lat)
        entry_lon.delete(0, tk.END)
        entry_lon.insert(0, lon)
        entry_gmaps.delete(0, tk.END)
        lbl_gmaps_status.config(text="✓ Applied!", foreground="green")
    else:
        lbl_gmaps_status.config(text="Invalid format", foreground="red")

def toggle_baseline():
    if baseline_active.get():
        entry_base_kwh.config(state="normal")
        entry_base_val.config(state="normal")
    else:
        entry_base_kwh.config(state="disabled")
        entry_base_val.config(state="disabled")

def generate_config():
    try:
        tz_idx = cb_timezone.current()
        utc_offset = TIMEZONE_OFFSETS[tz_idx][1] if tz_idx >= 0 else 0.0

        cfg = f'''# Auto-generated configuration by setup_wizard.pyw

# Wi-Fi Regulatory & Credentials
RP2_COUNTRY = "{entry_rp2.get().strip().upper()}"
WIFI_SSID = "{entry_ssid.get().strip()}"
WIFI_PASS = "{entry_pass.get().strip()}"

# Inverter Connection (Modbus TCP)
INVERTER_IP = "{entry_ip.get().strip()}"
INVERTER_PORT = {int(entry_port.get().strip())}
UNIT_ID = {int(entry_unit.get().strip(), 0)}

# Feed-In Tariffs
CURRENCY_SYMBOL = "{entry_curr.get().strip()}"
TARIFF_RATE = {float(entry_tariff.get().strip())}

# Promotional / Locked Baseline Tariffs
BASELINE_KWH = {float(entry_base_kwh.get().strip()) if baseline_active.get() else 0.0}
BASELINE_VALUE = {float(entry_base_val.get().strip()) if baseline_active.get() else 0.0}

# Location & UTC Offset (for Sunrise/Sunset & Time Sync)
UTC_OFFSET_HOURS = {float(utc_offset)}
FALLBACK_LAT = {float(entry_lat.get().strip())}
FALLBACK_LON = {float(entry_lon.get().strip())}
'''
        with open("config.py", "w", encoding="utf-8") as f:
            f.write(cfg)
        messagebox.showinfo("Success", "config.py was generated successfully!\n\nUpload config.py and main.py to your Pico.")
    except Exception as err:
        messagebox.showerror("Validation Error", f"Please check your input:\n{err}")

# --- UI WINDOW SETUP ---
root = tk.Tk()
root.title("GoodWe Pico Monitor — Setup")
root.geometry("560x700")
root.resizable(False, False)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

frame = ttk.Frame(notebook, padding=12)
notebook.add(frame, text="Device Settings")

row = 0

# 1. Country & Wi-Fi Regulatory
ttk.Label(frame, text="Country & Wi-Fi Region:", font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", pady=3)
cb_country = ttk.Combobox(frame, values=[c[0] for c in COUNTRY_CODES], state="readonly", width=34)
cb_country.grid(row=row, column=1, sticky="w", pady=3)
cb_country.current(0)
cb_country.bind("<<ComboboxSelected>>", on_country_change)

row += 1
ttk.Label(frame, text="Wi-Fi Code (rp2.country):").grid(row=row, column=0, sticky="w", pady=2)
entry_rp2 = ttk.Entry(frame, width=12)
entry_rp2.insert(0, "AU")
entry_rp2.grid(row=row, column=1, sticky="w")

# 2. Timezone
row += 1
ttk.Label(frame, text="Time Zone (GMT Offset):", font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", pady=4)
cb_timezone = ttk.Combobox(frame, values=[tz[0] for tz in TIMEZONE_OFFSETS], state="readonly", width=34)
cb_timezone.grid(row=row, column=1, sticky="w", pady=4)
cb_timezone.current(30)  # Default: GMT +10:00

# 3. Google Maps Coordinates
row += 1
ttk.Separator(frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

row += 1
ttk.Label(frame, text="Google Maps Right-Click:", font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", pady=2)
gmaps_f = ttk.Frame(frame)
gmaps_f.grid(row=row, column=1, sticky="w")
entry_gmaps = ttk.Entry(gmaps_f, width=24)
entry_gmaps.pack(side="left", padx=(0, 5))
btn_apply_gmaps = ttk.Button(gmaps_f, text="Paste/Apply", command=parse_google_maps_coords)
btn_apply_gmaps.pack(side="left")
lbl_gmaps_status = ttk.Label(gmaps_f, text="")
lbl_gmaps_status.pack(side="left", padx=5)

row += 1
ttk.Label(frame, text="Latitude / Longitude:").grid(row=row, column=0, sticky="w", pady=2)
coords_f = ttk.Frame(frame)
coords_f.grid(row=row, column=1, sticky="w")
entry_lat = ttk.Entry(coords_f, width=16)
entry_lat.insert(0, "-33.8688")
entry_lat.pack(side="left", padx=(0, 4))
entry_lon = ttk.Entry(coords_f, width=16)
entry_lon.insert(0, "151.2093")
entry_lon.pack(side="left")

# 4. Wi-Fi
row += 1
ttk.Separator(frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

row += 1
ttk.Label(frame, text="2.4GHz Wi-Fi SSID:", font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", pady=2)
entry_ssid = ttk.Entry(frame, width=34)
entry_ssid.grid(row=row, column=1, sticky="w")

row += 1
ttk.Label(frame, text="Wi-Fi Password:").grid(row=row, column=0, sticky="w", pady=2)
entry_pass = ttk.Entry(frame, show="*", width=34)
entry_pass.grid(row=row, column=1, sticky="w")

# 5. Inverter
row += 1
ttk.Separator(frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

row += 1
ttk.Label(frame, text="Inverter Static IP:", font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky="w", pady=2)
entry_ip = ttk.Entry(frame, width=34)
entry_ip.insert(0, "192.168.1.35")
entry_ip.grid(row=row, column=1, sticky="w")

row += 1
ttk.Label(frame, text="Modbus Port / Unit ID:").grid(row=row, column=0, sticky="w", pady=2)
sub_f2 = ttk.Frame(frame)
sub_f2.grid(row=row, column=1, sticky="w")
entry_port = ttk.Entry(sub_f2, width=15)
entry_port.insert(0, "502")
entry_port.pack(side="left", padx=(0, 4))
entry_unit = ttk.Entry(sub_f2, width=15)
entry_unit.insert(0, "0xF7")
entry_unit.pack(side="left")

# 6. Tariffs & Baseline
row += 1
ttk.Separator(frame, orient="horizontal").grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)

row += 1
ttk.Label(frame, text="Currency Symbol:").grid(row=row, column=0, sticky="w", pady=2)
entry_curr = ttk.Entry(frame, width=10)
entry_curr.insert(0, "$")
entry_curr.grid(row=row, column=1, sticky="w")

row += 1
ttk.Label(frame, text="Feed-In Tariff (per kWh):").grid(row=row, column=0, sticky="w", pady=2)
entry_tariff = ttk.Entry(frame, width=34)
entry_tariff.insert(0, "0.17")
entry_tariff.grid(row=row, column=1, sticky="w")

row += 1
baseline_active = tk.BooleanVar(value=False)
chk_baseline = ttk.Checkbutton(frame, text="Enable Baseline FIT Offset (Promotional Tariff Lock)", variable=baseline_active, command=toggle_baseline)
chk_baseline.grid(row=row, column=0, columnspan=2, sticky="w", pady=5)

row += 1
ttk.Label(frame, text="Baseline Cutoff (kWh):").grid(row=row, column=0, sticky="w", pady=2)
entry_base_kwh = ttk.Entry(frame, width=34)
entry_base_kwh.insert(0, "0.0")
entry_base_kwh.grid(row=row, column=1, sticky="w")

row += 1
ttk.Label(frame, text="Baseline Accrued Total:").grid(row=row, column=0, sticky="w", pady=2)
entry_base_val = ttk.Entry(frame, width=34)
entry_base_val.insert(0, "0.0")
entry_base_val.grid(row=row, column=1, sticky="w")

toggle_baseline()

row += 1
btn_save = ttk.Button(frame, text="Generate config.py", command=generate_config)
btn_save.grid(row=row, column=0, columnspan=2, pady=16, sticky="ew")

root.mainloop()