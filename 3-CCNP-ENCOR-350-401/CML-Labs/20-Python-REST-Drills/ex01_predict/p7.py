# Was gibt das aus? (Funktionen, Standardargumente)
def add_vlan(vlan, liste=[]):
    liste.append(vlan)
    return liste
print(add_vlan(10))
print(add_vlan(20))
print(add_vlan(30, []))
