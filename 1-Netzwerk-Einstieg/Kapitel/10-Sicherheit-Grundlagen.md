# 10. Sicherheit: Die Grundlagen

> **Darum geht's:** Sicherheit ist kein Produkt, sondern viele kleine Gewohnheiten. Die Schutzziele sagen, was du schützen willst, die Maßnahmen, wie.
>
> **Danach kannst du:** die drei Schutzziele erklären · typische Bedrohungen erkennen · grundlegende Schutzmaßnahmen begründen.

## Schutzziele (CIA)

- **C**onfidentiality: Nur Berechtigte lesen die Daten.
- **I**ntegrity: Daten werden nicht unbemerkt verändert.
- **A**vailability: Dienste sind verfügbar, wenn man sie braucht.

## Typische Bedrohungen

| Bedrohung | Kurz erklärt |
|---|---|
| Phishing | Gefälschte Nachrichten, die Zugangsdaten abgreifen |
| Malware | Schadsoftware (Virus, Wurm, Trojaner, Ransomware) |
| DoS/DDoS | Überlastung eines Dienstes |
| Man-in-the-Middle | Angreifer sitzt unbemerkt zwischen zwei Partnern |
| Passwortangriffe | Raten, Wörterbuch, gestohlene Zugangsdaten |

Die häufigste Schwachstelle ist der **Mensch**. Technik hilft, ersetzt aber keine Sorgfalt.

## Grundmaßnahmen

1. **Updates** einspielen (Patch-Management).
2. **Starke, einzigartige Passwörter**, Passwortmanager nutzen.
3. **Mehrfaktor-Authentifizierung (MFA)** wo möglich.
4. **Least Privilege**: Nur so viele Rechte wie nötig.
5. **Segmentierung**: Netze trennen (VLANs, Firewalls).
6. **Backups**: 3-2-1-Regel (3 Kopien, 2 Medien, 1 extern).
7. **Verschlüsselung**: HTTPS, VPN, WPA2/3.

## Firewall, IDS, IPS

- **Firewall**: Erlaubt oder blockiert Verkehr nach Regeln.
- **IDS**: Erkennt Angriffe und meldet sie.
- **IPS**: Erkennt und blockiert, weil es im Datenpfad sitzt.

## VPN

Ein verschlüsselter Tunnel durch ein unsicheres Netz. Damit verbindest du Standorte (Site-to-Site) oder Einzelne (Remote Access) sicher mit dem Firmennetz.

## Das Wichtigste in Kürze

- Schutzziele: Vertraulichkeit, Integrität, Verfügbarkeit (CIA).
- Die häufigste Schwachstelle ist der Mensch, z. B. durch Phishing.
- Updates, starke Passwörter mit MFA, Backups und getrennte Netze bilden die Basis.

## Selbsttest

1. Was verletzt ein Angreifer, der Daten mitliest?
2. Was ist der Unterschied zwischen IDS und IPS?
3. Warum ist MFA stark?

<details><summary>Antworten</summary>

1. **Die Vertraulichkeit.** Er sieht Daten, die nicht für ihn bestimmt sind. Ändert er sie, wäre zusätzlich die Integrität verletzt.
2. **Ein IDS meldet nur, ein IPS kann blockieren.** Das IPS sitzt dafür direkt im Datenweg, das IDS bekommt nur eine Kopie.
3. **Weil ein gestohlenes Passwort allein nicht reicht.** Der Angreifer bräuchte zusätzlich den zweiten Faktor, z. B. dein Handy.

</details>

Zurück: [9. WLAN](09-WLAN.md) · Weiter: [11. Fehlersuche](11-Fehlersuche.md)
