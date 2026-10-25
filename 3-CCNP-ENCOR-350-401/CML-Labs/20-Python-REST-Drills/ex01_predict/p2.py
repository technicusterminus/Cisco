# Was gibt das aus? (Dictionaries und Schleifen)
sw = {"name": "SW1", "vlans": [10, 20], "mgmt": "10.0.0.1"}
sw["vlans"].append(30)
for k, v in sw.items():
    print(k, "->", v)
print(sw.get("model", "unbekannt"))
print("mgmt" in sw, "SW1" in sw)
