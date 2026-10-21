# 11. Fehlersuche mit einfachen Mitteln

> **Darum geht's:** Bei einer Störung hilft kein Raten, sondern eine feste Reihenfolge. Du arbeitest dich vom Kabel bis zur Anwendung vor, und wo der erste Test scheitert, liegt das Problem.
>
> **Danach kannst du:** die wichtigsten Diagnosebefehle einsetzen · mit Ping von nah nach fern eine Störung eingrenzen · typische Fehlerbilder einer Ursache zuordnen.

Bei Netzwerkproblemen hilft eine feste Reihenfolge, von unten nach oben:

```
1. Kabel / Link-LED          (Layer 1)
2. Switch-Port / VLAN        (Layer 2)
3. IP-Adresse / Gateway      (Layer 3)
4. Erreichbarkeit / Ports    (Layer 3/4)
5. DNS / Anwendung           (Layer 7)
```

## Die wichtigsten Werkzeuge

| Befehl (Windows) | Linux / macOS | Was er zeigt |
|---|---|---|
| `ipconfig /all` | `ip addr` / `ifconfig` | Eigene IP, Maske, Gateway, DNS |
| `ping 192.168.1.1` | `ping` | Ist das Ziel erreichbar? |
| `tracert 8.8.8.8` | `traceroute` | Weg und Hops zum Ziel |
| `nslookup name` | `dig name` | Namensauflösung |
| `arp -a` | `arp -a` | ARP-Tabelle (IP ↔ MAC) |
| `netstat -an` | `ss -tuln` | Offene Ports und Verbindungen |

## Der Standardablauf (von nahe nach fern)

1. `ping 127.0.0.1`: Funktioniert der Netzwerk-Stack?
2. `ping <eigene IP>`: Ist die eigene Adresse richtig eingerichtet?
3. `ping <Gateway>`: Funktioniert das lokale Netz?
4. `ping 8.8.8.8`: Funktioniert der Weg ins Internet?
5. `ping www.example.com`: Funktioniert DNS?

Wo der erste Ping scheitert, liegt das Problem.

## Typische Fehlerbilder

| Beobachtung | Wahrscheinliche Ursache |
|---|---|
| IP `169.254.x.x` | Kein DHCP erreicht |
| Gateway ping geht, 8.8.8.8 nicht | Routing/Provider/NAT |
| 8.8.8.8 geht, Name nicht | DNS |
| Nur das eigene Subnetz erreichbar | Gateway fehlt oder falsch |
| Langsam, viele Fehler am Port | Kabel oder Duplex-Mismatch |

## Wireshark in einem Satz

Mit Wireshark siehst du jedes Paket: Welche MAC fragt per ARP? Ging der DNS-Query raus? Kam ein SYN/ACK zurück? Fürs Verständnis unbezahlbar (siehe [Übungen](../Uebungen/)).

## Das Wichtigste in Kürze

- Von unten nach oben: Kabel, Switch-Port, Adresse und Gateway, Erreichbarkeit, DNS und Anwendung.
- Ping von nah nach fern: Loopback, eigene IP, Gateway, Internet-Adresse, Name.
- Der erste Test, der scheitert, zeigt dir die Stelle.

## Selbsttest

1. Ping auf das Gateway klappt, Ping auf 8.8.8.8 nicht. Wo suchst du?
2. Ping auf 8.8.8.8 klappt, auf einen Namen nicht. Was ist es?
3. Welcher Befehl zeigt den Weg zum Ziel?

<details><summary>Antworten</summary>

1. **Hinter dem Gateway.** Das lokale Netz funktioniert. Prüfe Routing, NAT und die Verbindung zum Provider.
2. **DNS.** Das Internet ist erreichbar, nur die Übersetzung von Namen in Adressen klappt nicht. Prüfe den DNS-Server mit `nslookup`.
3. **`tracert` unter Windows, `traceroute` unter Linux und macOS.** Er zeigt jede Station auf dem Weg.

</details>

Zurück: [10. Sicherheit](10-Sicherheit-Grundlagen.md) · Weiter: [12. Cisco-CLI und Weg zur CCNA](12-Cisco-CLI-und-Weg-zur-CCNA.md)
