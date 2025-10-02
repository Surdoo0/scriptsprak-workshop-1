# Load the json module for reading and writing JSON
import json
from datetime import datetime

# Open network_devices.json with UTF-8 encoding
data = json.load(open("network_devices.json", "r",encoding = "utf-8")) 

# Create a variable that holds our whole text report
report = ""
report += "\n.............................\n" 
report += "Nätverksrapport - TechCorp AB\n.............................\n"

# Dates & time
report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
try:
    last_updated_dt = datetime.fromisoformat(data.get("last_updated"))
    last_updated_str = last_updated_dt.strftime("%Y-%m-%dT%H:%M:%S")
except Exception:
    last_updated_str = str(data.get("last_updated") or "-")
report += f"Rapportdatum: {report_date}\n"
report += f"Datauppdatering: {last_updated_str}\n"

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
        
# write the report to text file
with open('report.txt', 'w', encoding='utf-8') as f:
    f.write(report)
