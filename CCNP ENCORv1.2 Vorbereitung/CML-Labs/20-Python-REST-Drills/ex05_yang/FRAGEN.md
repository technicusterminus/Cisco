# Aufgabe 5 – YANG lesen und Instanzdaten bauen (Ziel 6.3)

Datei: [`lab-interfaces.yang`](lab-interfaces.yang). Zum Anzeigen des Baums: `pip install pyang`, dann `pyang -f tree lab-interfaces.yang`.

1. Benenne alle Knotentypen (`container`, `list`, `leaf`, `leaf-list`) und gib den Schlüssel der Liste an. Was bedeutet `config false`?
2. Welche Knoten sind Pflicht (`mandatory`), welche haben einen Default? Was passiert, wenn du `mode` weglässt (Fehlertyp bei NETCONF/RESTCONF)?
3. Schreibe eine **gültige** JSON-Instanz (RESTCONF-Stil, Modulpräfix) für `GigabitEthernet0/1` als Access-Port in VLAN 10 mit Description `H1`.
4. Schreibe eine gültige Instanz für einen Trunk mit den VLANs 10, 20 und 30.
5. Welche dieser Instanzen sind **ungültig** und warum?
   - (a) Access-Port mit `allowed-vlans: [10]`
   - (b) Access-Port mit `access-vlan: 5000`
   - (c) Interface ohne `name`
   - (d) Änderung von `statistics/in-octets` per `edit-config`
6. Welche RESTCONF-URL liest genau das Interface `GigabitEthernet0/1` (Vorsicht: Schrägstrich im Schlüssel)?
7. Unterschied zwischen einem Datenknoten und einem `rpc` (hier `clear-counters`). Wie rufst du den RPC per RESTCONF auf (Methode, Pfad, Body)?
8. Warum ist YANG ein *Datenmodell* und kein Transportprotokoll? Nenne je ein Beispiel für Standard-, Hersteller- und OpenConfig-Modelle.
