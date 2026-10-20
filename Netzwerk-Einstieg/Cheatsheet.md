# Cheatsheet Netzwerk-Grundlagen

Eine Seite zum Ausdrucken oder Daneben-Legen.

## OSI-Schichten

| 7 | Anwendung | HTTP, DNS, SSH |
|---|---|---|
| 6 | Darstellung | TLS, JSON |
| 5 | Sitzung | |
| 4 | Transport | TCP, UDP (Segment) |
| 3 | Vermittlung | IP (Paket) |
| 2 | Sicherung | Ethernet, MAC (Frame) |
| 1 | Bitübertragung | Kabel, Funk (Bits) |

## Wichtige Ports

| 20/21 FTP | 22 SSH | 23 Telnet | 25 SMTP |
|---|---|---|---|
| 53 DNS | 67/68 DHCP | 69 TFTP | 80 HTTP |
| 110 POP3 | 123 NTP | 143 IMAP | 161/162 SNMP |
| 443 HTTPS | 514 Syslog | 1812/1813 RADIUS | 49 TACACS+ |

## Subnetting-Tabelle

| Präfix | Maske | Hosts | Block |
|---|---|---|---|
| /24 | .0 | 254 | 256 |
| /25 | .128 | 126 | 128 |
| /26 | .192 | 62 | 64 |
| /27 | .224 | 30 | 32 |
| /28 | .240 | 14 | 16 |
| /29 | .248 | 6 | 8 |
| /30 | .252 | 2 | 4 |

Hosts = 2^Hostbits − 2.

## Private Adressen

`10.0.0.0/8` · `172.16.0.0/12` · `192.168.0.0/16`
Loopback `127.0.0.1` · APIPA `169.254.0.0/16`

## Administrative Distance

Connected 0 · Static 1 · eBGP 20 · EIGRP 90 · OSPF 110 · RIP 120 · iBGP 200

## Windows-Befehle

`ipconfig /all` · `ping` · `tracert` · `nslookup` · `arp -a` · `netstat -an`

## Cisco-CLI

| Modus | Befehl |
|---|---|
| Privilegiert | `enable` |
| Konfiguration | `configure terminal` |
| Interface | `interface g0/1` |
| Speichern | `copy running-config startup-config` |

Nützliche Show-Befehle:
`show ip interface brief` · `show vlan brief` · `show mac address-table` · `show ip route` · `show running-config`

## Fehlersuche in fünf Schritten

Kabel → Switch/VLAN → IP/Gateway → Erreichbarkeit/Ports → DNS/Anwendung.
Ping-Reihenfolge: `127.0.0.1` → eigene IP → Gateway → `8.8.8.8` → Name.
