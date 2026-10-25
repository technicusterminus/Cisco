# Was gibt das aus? (Comprehensions, Filter)
devices = [
    {"name": "sw1", "status": "up", "ports": 24},
    {"name": "sw2", "status": "down", "ports": 48},
    {"name": "sw3", "status": "up", "ports": 48},
]
print([d["name"] for d in devices if d["status"] == "up"])
print({d["name"]: d["ports"] for d in devices})
print(sum(d["ports"] for d in devices if d["ports"] > 24))
