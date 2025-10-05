# Load the json module for reading and writing JSON
import json
from datetime import datetime

# Open network_devices.json with UTF-8 encoding
data = json.load(open("network_devices.json", "r",encoding = "utf-8")) 

# Create a variable that holds our whole text report
report = ""

# Header and dates reads from JSON data

WIDTH = 66 # total line width for centrering; tweak to match your layout

def hr (ch="=", widht=WIDTH):
    # Return a horizontal rule line of given char and width
    return ch * widht

def iso_to_str(value):
    # Parses ISO8601 string safely and returns "YYYY-MM-DDTHH:MM:SS"
    if not value:
        return "-"
    try:
        #Handle trailing 'Z' (UTC) if present
        value = value.raplace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return str(value)
    
company = str(data.get("company", "-"))
title   = f"NÄTVERKSRAPPORT - {company}"

# Build header block
report += hr("=") + "\n"
report += title.center(WIDTH) + "\n"
report += hr("=") + "\n"

# Dates
report_date_str   = datetime.now().strftime("%Y-%m-%d %H:%M")
last_updated_str  = iso_to_str(data.get("last_updated"))

# Left-align labels to same width so colons line up
LABEL_W = 16
report += f"{'Rapportdatum:':<{LABEL_W}} {report_date_str}\n"
report += f"{'Datauppdatering:':<{LABEL_W}} {last_updated_str}\n"

# Executive summary header
report += "\nEXECUTIVE SUMMARY\n"
report += ".................\n"

# --- Counters for the summary ---
offline_count = 0
warning_count = 0
low_uptime_count = 0                # devices with uptime < 30 days
high_port_util_switches = 0         # switches with port utilization > 80%

for location in data.get("locations", []):
    for device in location.get("devices", []):
        status = str(device.get("status", "")).lower()
        if status == "offline":
            offline_count += 1
        elif status == "warning":
            warning_count += 1

        uptime = device.get("uptime_days")
        if isinstance(uptime, (int, float)) and uptime < 30:
            low_uptime_count += 1

        if device.get("type") == "switch":
            ports = device.get("ports", {})
            total = ports.get("total")
            used = ports.get("used")
            if isinstance  (total, int) and total and isinstance(used, int):
                if used / total >= 0.80:
                    high_port_util_switches +=1

# --- Write the summary lines ---
report += f"⚠ KRITISKT: {offline_count} enheter offline\n"
report += f"⚠ VARNING: {warning_count} enheter med varningsstatus\n"
report += f"⚠ {low_uptime_count} enheter med låg uptime (<30 dagar) – kan indikera instabilitet\n"
report += f"⚠ {high_port_util_switches} switchar har hög portanvändning (>80%)\n"

report += "\nENHETER MED PROBLEM\n"
report += "...................\n"

# --- Column widths for aligned output ---
COL_HOST = 16
COL_IP = 18
COL_TYPE = 15
COL_SITE = 15

def fmt_type(t: str) -> str:
    # Pretty print: "access_point" -> "Access Point"
    return str(t or "").replace("_", " ").title()

def fmt_line(host, ip, dtype, site):
    return (
         f"{host:<{COL_HOST}}"
        f"{ip:<{COL_IP}}"
        f"{dtype:<{COL_TYPE}}"
        f"{site:<{COL_SITE}}"
    )

report += "Status: OFFLINE\n"

for location in data["locations"]:
    for device in location["devices"]:
        if device["status"] == "offline":
            line = fmt_line(
                device["hostname"],
                device["ip_address"],
                fmt_type(device["type"]),
                location["site"],
            )
            report += line + "\n"

report += "\nStatus: Warning\n"

warning_devices = []

for location in data["locations"]:
    for device in location["devices"]:
        if device["status"] == "warning":
            warning_devices.append((location, device))

# --- Sort devices: router → switch → access_point ---
type_priority = {"router": 0, "switch": 1, "access point": 2, "access_point": 2}

def sort_key(item):
    loc, dev = item
    dtype = str(dev.get("type", "")).lower().replace("_", " ").strip()
    pri = type_priority.get(dtype, 99)
    return (pri, dev.get("hostname", ""))

warning_devices.sort(key=sort_key)

# Print in sorted order with aligned columns
for location, device in warning_devices:
    line = fmt_line(
        device["hostname"],
        device["ip_address"],
        fmt_type(device["type"]),
        location["site"],
    )

     # Fetch any client value form connected_clients or clients
    clients = device.get("connected_clients", device.get("clients"))
    dtype_norm = device.get("type", "").replace("_", " ").strip().lower()
    
    # If it's an Access Point - show clients instead of uptime
    if device.get("type", "").replace("_", " ").strip().lower() == "access point" and clients is not None:
        line += f" ({clients} anslutna klienter!)"
    # Otherwise, show uptime if available
    elif "uptime_days" in device and device["uptime_days"] is not None:
        line += f" (uptime: {device['uptime_days']} dagar)"
    # If it's not an AP but still have clients, show them
    elif clients is not None:
        line += f" ({clients} anslutna klienter!)"
            
    report += line + "\n"

report += "\nENHETER MED LÅG UPTIME (<30 dagar)\n"
report += "..................................\n"

# Column widths for aligned output
LU_COL_HOST     = 16
LU_COL_UPTIME   = 10
LU_COL_SITE     = 20
LU_COL_FLAG     = 12

#Device with uptime les than this are marked as critical
CRIT_THRESHOLD = 3

def fmt_low_uptime_line(host, days, site, is_critical):
    # Correct pluralization: 1 dag vs. 2 dagar
    unit = "dag" if int(days) == 1 else "dagar"
    flag = "⚠ KRITISKT" if is_critical else ""
    return (
        f"{host:<{LU_COL_HOST}}"
        f"{(str(int(days)) + ' ' + unit):<{LU_COL_UPTIME}}"
        f"{site:<{LU_COL_SITE}}"
        f"{flag:<{LU_COL_FLAG}}"    
    )

# Collect all devices with uptime < 30 days
low_uptime_list = []
for location in data.get("locations", []):
    for device in location.get("devices", []):
        d = device.get("uptime_days") # <-- d is defined here
        if isinstance(d, (int, float)) and d < 30:
            low_uptime_list.append((device, location))

# Sort by uptime (ascending), the by hostname
low_uptime_list.sort(key=lambda x: (x[0].get("uptime_days", 999999), x[0].get("hostname", "")))

# Render lines
for device, location in low_uptime_list:
    days = device.get("uptime_days", 0)
    critical = days < CRIT_THRESHOLD
    line = fmt_low_uptime_line(device.get("hostname", "-"), days, location.get("site", "-"), critical)
    report += line + "\n"

report += "\nSTATISTIK PER ENHETSTYP\n"
report += ".......................\n"

device_stats = {} # dict to hold counts

total_devices = 0
total_offline = 0

for location in data.get("locations", []):
    for device in location.get("devices", []):
        dtype = str(device.get("type", "")).replace("_", " ").title()

        # Initialize dict entre if not exists
        if dtype not in device_stats:
            device_stats[dtype] = {"total": 0, "offline": 0}

        # Update counters
        device_stats[dtype]["total"] += 1
        total_devices += 1

        if str(device.get("status", "")).lower() == "offline":
            device_stats[dtype]["offline"] += 1
            total_offline += 1

# Print statistics with aligned columns
for dtype, stats in device_stats.items():
    report += (
        f"{dtype:<15}"            # device type, left aligned
        f"{stats['total']:>3} st   "  # total, right aligned in 3 spaces
        f"({stats['offline']} offline)\n"
    )

# Summary line
offline_percent = (total_offline / total_devices * 100) if total_devices else 0
report += "--------------------------------------\n"
report += f"TOTALT: {total_devices} enheter ({total_offline} offline = {offline_percent:.1f}% offline)\n"
report += ""

report += "\nPORTANDVÄNDNING SWITCHAR\n"
report += "........................\n"

# Column widths
PU_COL_SITE     = 22    # site name
PU_COL_COUNT    = 12    # switch count
PU_COL_USED     = 15    # used/total 
PU_COL_PCT      = 12    # utilization %
PU_COL_FLAG     = 12    # warning/critical flag

# Thresholds
WARN_THRESHOLD = 0.80 # 80% => warning
CRIT_THRESHOLD = 0.95 # 95% => critical

# Collector per site
site_stats = {} # { site: {"switches": n, "used": x, "total": y} }
total_used = 0
total_total = 0

for location in data.get("locations", []):
    site = location.get("site", "-")
    for dev in location.get("devices", []):
        dtype = str(dev.get("type", "")).lower()
        if dtype == "switch":
            ports = dev.get("ports") or {}
            used = ports.get("used", 0) or 0
            total = ports.get("total", 0) or 0

            if site not in site_stats:
                site_stats[site] = {"switches": 0, "used": 0, "total": 0}
            
            site_stats[site]["switches"] += 1
            site_stats[site]["used"] += used
            site_stats[site]["total"] += total

            total_used += used
            total_total += total

# Sort sites by name (change key to sort by utilization instead if you want)
sorted_sites = sorted(
    site_stats.items(),
    key=lambda kv: (kv[1]['used'] / kv[1]['total']) if kv[1]['total'] else 0.0,
    reverse=True
)

# Header row (optional)
report += (
    f"{'Site':<{PU_COL_SITE}}"
    f"{'Switchar':<{PU_COL_COUNT}}"
    f"{'Använt/Totalt':<{PU_COL_USED}}"
    f"{'Användning':<{PU_COL_PCT}}"
    f"{'':<{PU_COL_FLAG}}\n"
)


# Render per-site rows
for site, stats in sorted_sites:
    used = stats["used"]
    total = stats["total"]
    pct = (used / total) if total else 0.0

    # Flag selection
    flag = ""
    if pct >= CRIT_THRESHOLD:
        flag = "⚠ KRITISKT!"
    elif pct >= WARN_THRESHOLD:
        flag = "⚠ KRITISKT!"

    report += (
        f"{site:<{PU_COL_SITE}}"
        f"{(str(stats['switches']) + ' st'):<{PU_COL_COUNT}}"
        f"{(str(used) + '/' + str(total)):<{PU_COL_USED}}"
        f"{(f'{pct*100:.1f}%'):<{PU_COL_PCT}}"
        f"{flag:<{PU_COL_FLAG}}\n"
    )

# Totals row aligned under "Använt/Totalt"
tot_pct = (total_used / total_total) if total_total else 0.0
report += "\n"
report += (
    f"{'Totalt:':<{PU_COL_SITE + PU_COL_COUNT}}"
    f"{(str(total_used) + '/' + str(total_total) + ' portar används'):<{PU_COL_USED}}"
    f"{(f'({tot_pct*100:.1f}%).'):<{PU_COL_PCT}}\n"
)

report += "\nSWITCHAR MED HÖG PORTANVÄNDNING (>80%)\n"
report += "......................................\n"

# Column widths (adjuts if you want tigher/wider columns)
HU_COL_HOST = 18    # hostname
HU_COL_USED = 10    # "used/total"
HU_COL_PCT  = 8     # "95.8%"
HU_COL_FLAG = 10    # "⚠", "⚠ FULLT!"

# Thresholds
HIGH_THRESHOLD = 0.80   # 80%
# (100% handled separately as "FULLT!")

high_list = []  # will store tuples: (hotname, used, total, pct_float)

# Collect switches and compute utiliation
for location in data.get("locations", []):
    for dev in location.get("devices", []):
        dtype = str(dev.get("type", "")).lower().replace("_", " ").strip()
        if dtype == "switch":
            ports = dev.get("ports") or {}
            used = int(ports.get("used") or 0)
            total = int(ports.get("total") or 0)
            if total <= 0:
                continue # skip invalid totals

            pct = used/total
            if pct >= HIGH_THRESHOLD:
                    high_list.append((dev.get("hostname", "-"), used, total, pct))

# Sort by utilization desc, then hostname asc
high_list.sort(key=lambda x: (-x[3], x[0]))

# Render rows
for host, used, total, pct in high_list:
    # Pick flag: FULLT! if 100%, otherwise generic warning
    if used == total and total > 0:
        flag = "⚠ FULLT!"
    else:
        flag = "⚠"
    
    report += (
        f"{host:<{HU_COL_HOST}}"
        f"{(str(used) + '/' + str(total)):<{HU_COL_USED}}"
        f"{(f'{pct*100:.1f}%'):<{HU_COL_PCT}}"
        f"{flag:<{HU_COL_FLAG}}\n"
    )

# If none matched, show a friendly line
if not high_list:
    report += "Inga switchar över 80% portanvändning. \n"

report += "\nVLAN-ÖVERSIKT\n"
report += ".............\n"

# Collect all VLAN IDs into a set
all_vlans = set()
devices_with_vlans = 0 # debug counter

for location in data.get("locations", []):
    for device in location.get("devices", []):
        vlist = device.get("vlans")  # may be None or a list
        if isinstance(vlist, list) and vlist:
            devices_with_vlans += 1
            for v in vlist:
                try:
                    all_vlans.add(int(v))  # accept ints or strings
                except Exception:
                    # ignore values that cannot be parsed as int
                    pass

sorted_vlans = sorted(all_vlans)

report += f"Totalt antal unika VLANs i nätverket: {len(sorted_vlans)} st\n"

# Pretty-print with wrapping (10 per line)
prefix = "VLANs: "
indent = " " * len(prefix)
per_line = 10
if sorted_vlans:
    for i in range(0, len(sorted_vlans), per_line):
        chunk = sorted_vlans[i:i+per_line]
        report += (prefix if i == 0 else indent) + ", ".join(map(str, chunk)) + "\n"
else:
    report += "VLANs: (inga funna)\n"

# Optional debug line if you still see 0:
# report += f"(DEBUG) devices_with_vlans={d



# write the report to text file
with open('report.txt', 'w', encoding='utf-8') as f:
    f.write(report)
