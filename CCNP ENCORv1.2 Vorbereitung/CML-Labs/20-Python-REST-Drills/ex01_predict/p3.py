# Was gibt das aus? (f-Strings, Formatierung)
host, port, up = "R1", 830, True
print(f"{host}:{port}")
print(f"{host:>6}|{port:<6}|{port:06d}")
print(f"Status: {'UP' if up else 'DOWN'}")
print("-".join(["10", "0", "0", "1"]))
