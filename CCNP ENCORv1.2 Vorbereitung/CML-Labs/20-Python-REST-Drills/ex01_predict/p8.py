# Was gibt das aus? (Mini-Parser einer CLI-Ausgabe)
output = """Interface              IP-Address      Status
GigabitEthernet0/0     10.0.0.1        up
GigabitEthernet0/1     unassigned      down
Loopback0              1.1.1.1         up"""
rows = []
for line in output.splitlines()[1:]:
    name, ip, status = line.split()
    rows.append({"name": name, "ip": ip, "up": status == "up"})
print(len(rows))
print([r["name"] for r in rows if r["up"]])
print(rows[1])
