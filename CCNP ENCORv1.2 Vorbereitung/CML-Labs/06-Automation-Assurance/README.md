# Lab 06 – Automation und Assurance

**Blueprint:** 4.x/Assurance (SNMP, Syslog, SPAN, IP SLA, NetFlow), 6.x/Automation (NETCONF, RESTCONF, YANG, EEM, Python) · **Deck-Tags:** `Ziel::4.*`, `Ziel::6.*` (Domäne Assurance/Automation)
**Dauer:** ca. 90 min · **Nodes:** 1× CSR1000v, 1× IOSv Router, 1× IOSvL2, 2× IOSv Hosts, 1× External Connector (Default NAT)

## Topologie

```
 CML-Host (NAT) ─ EXT ─ CSR1 ─ R2 ─ SW1 ─ H1 (Quelle)   [10.0.23.0/29: R2 .1, H1 .2, COL .3]
        Gi1 (DHCP)  Gi2  10.0.12.0/30   └─ COL (SPAN-Ziel)
```

CSR1 bekommt über den External Connector (`virbr0`, Default NAT) per DHCP eine Adresse aus dem CML-Management-Netz und ist von deinem Rechner/der CML-VM aus erreichbar. Ohne CML-Netzwerkzugriff funktionieren die Python-Aufgaben nicht, die CLI-Aufgaben aber schon.

## Aufgaben

### Teil A – Zugang und Programmierbarkeit (CSR1)

1. **Grundzugang.** Lege einen lokalen Benutzer mit privilege 15 an, aktiviere SSH 2 und lies die DHCP-Adresse von Gi1 (`show ip interface brief`).
2. **RESTCONF.** Aktiviere `restconf`, `ip http secure-server` und `ip http authentication local`. Frage `https://<CSR1>/restconf/data/ietf-interfaces:interfaces` mit `curl -k -u user:pw -H "Accept: application/yang-data+json"` ab und vergleiche mit `show running-config`. Was bedeutet der Header `application/yang-data+json` und welche HTTP-Methoden (GET, PUT, POST, PATCH, DELETE) entsprechen welcher Operation?
3. **NETCONF.** Aktiviere `netconf-yang` (Port 830), baue per `ssh -p 830 user@<CSR1> -s netconf` eine Sitzung auf und tausche `<hello>` mit den Capabilities aus. Führe ein `<get-config>` auf `running` mit einem Subtree-Filter für `ietf-interfaces` aus (Beispiel: [`python/netconf_get.py`](python/netconf_get.py)). Welche Rolle spielen `<edit-config>`, `<commit>` und das `candidate`-Datastore?
4. **Python / REST.** Nutze [`python/restconf_get.py`](python/restconf_get.py), um die Interface-Liste zu holen. Ändere das Script so, dass es per PATCH die Description von Gi2 setzt. Prüfe auf der CLI.
5. **YANG verstehen.** Suche im JSON-Ergebnis Container, List und Leaf. Warum ist `ietf-interfaces` ein Standard-Modell und `Cisco-IOS-XE-native` ein herstellerspezifisches (native) Modell?

### Teil B – Assurance (CSR1/R2)

6. **Syslog.** Sende Syslog von R2 an COL (10.0.23.3, im Lab nur als Ziel; Quell-Interface Lo0, Severity `informational`). Wie ist ein Syslog-Eintrag aufgebaut (`%FACILITY-SEVERITY-MNEMONIC`) und was bedeutet Level 3 gegenüber 6?
7. **SNMPv3.** Lege auf R2 eine SNMPv3-Gruppe `authPriv` mit SHA und AES-128 an, ein Benutzer `monitor`, Trap-Ziel COL. Warum ist v3 mit `authPriv` den Versionen 1/2c überlegen (Authentifizierung + Verschlüsselung, USM, VACM)?
8. **IP SLA + Track.** Konfiguriere auf CSR1 eine `ip sla 1` mit `icmp-echo 2.2.2.2 source-interface Loopback0`, Frequenz 10 s, Schedule `life forever start-time now`. Binde `track 1 ip sla 1 reachability` an eine statische Default-Route (`ip route 0.0.0.0 0.0.0.0 10.0.12.2 track 1`) und teste, was passiert, wenn du R2 Gi0/0 abschaltest. Wozu dient `ip sla schedule` und warum fehlt eine Messung ohne?
9. **SPAN.** Spiegele auf SW1 den Port Gi0/1 (H1) auf Gi0/2 (COL): `monitor session 1 source interface Gi0/1 both`, `destination interface Gi0/2`. Prüfe mit `show monitor session 1`. Was ist der Unterschied zu RSPAN/ERSPAN (Layer 2 VLAN bzw. GRE-Transport)?
10. **Flexible NetFlow (optional).** Definiere auf CSR1 Flow Record (`match ipv4 source/destination address`, `match ipv4 protocol`, `match transport source/destination port`, `collect counter bytes/packets`), Exporter (UDP 2055 an COL), Monitor und hänge ihn `ip flow monitor … input` an Gi2. Prüfe mit `show flow monitor … cache`.

### Teil C – EEM

11. **EEM-Applet.** Schreibe auf CSR1 ein Applet, das bei der Syslog-Meldung `%LINK-3-UPDOWN` an Gi2 (Pattern passend zur **vollständigen** Interface-Schreibweise `GigabitEthernet2`) eine eigene Syslog-Zeile ausgibt und `show ip interface brief` in eine Datei im Flash schreibt (`action 1.0 syslog msg "…"`, `action 2.0 cli command "enable"`, `action 3.0 cli command "show ip int brief | redirect flash:ipint.txt"`). Wie unterscheidet sich ein **Applet** von einem **Tcl-Skript**? Welche Events gibt es (syslog, timer, cli, snmp, track)?
12. **Fehlersuche.** Ändere das Pattern bewusst auf `Gi2` und teste einen Link-Flap. Warum löst es nicht aus (der Syslog-Text enthält den langen Namen)?

## Verifikation

```
show platform software yang-management process
show netconf-yang sessions
show ip sla statistics
show track
show monitor session 1
show event manager policy registered
show snmp user
```

## Lösungen

Siehe [`solutions/`](solutions/) und die Python-Beispiele in [`python/`](python/).

## Prüfungsbezug

REST-Verben ↔ CRUD, JSON/XML/YAML-Syntax lesen, NETCONF (SSH 830, XML, `<rpc>`) vs. RESTCONF (HTTPS, JSON/XML), YANG als Datenmodell (nicht Transport), SNMP-Versionen, SPAN/RSPAN/ERSPAN, EEM-Events und -Actions, IP-SLA-Operationen.
