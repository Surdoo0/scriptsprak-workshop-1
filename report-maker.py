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

report += "Status: OFFLINE\n"

for location in data["locations"]:
    for device in location["devices"]:
        if device["status"] == "offline":
            line = (
                device["hostname"] + "  "
                + device["ip_address"] + "  "
                + device["type"] + "  "
                + location["site"]
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

# --- Print in sorted order ---
for location, device in warning_devices:
    line = (
        device["hostname"] + "  "
        + device["ip_address"] + "  "
        + device["type"] + "  "
        + location["site"] 
    )

     # Fetch any client value form connected_clients or clients
    clients = device.get("connected_clients", device.get("clients"))

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
        
# write the report to text file
with open('report.txt', 'w', encoding='utf-8') as f:
    f.write(report)
