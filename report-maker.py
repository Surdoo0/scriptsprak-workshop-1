# Load the json module for reading and writing JSON
import json

# Open network_devices.json with UTF-8 encoding
data = json.load(open("network_devices.json", "r",encoding = "utf-8")) 

# Create a variable that holds our whole text report
report = ""
report += "\n.............................\n" "Nätverksrapport - TechCorp AB" + "\n.............................\n"

# For each element in the location list
for location in data["locations"]:
    # Print the name of the location

    report += "\n" + location["site"] + "\n...............\n"
    # print a list of the host names of the devices on the location
    for device in location["devices"]:
        report += " " + device["hostname"] + "\n"

# write the report to text file
with open('report.txt', 'w', encoding='utf-8') as f:
    f.write(report)
