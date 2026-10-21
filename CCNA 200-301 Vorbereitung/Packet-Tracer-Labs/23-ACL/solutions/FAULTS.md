# Fehlerliste – Lab 23 – Access Control Lists: Standard, Extended, Named

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R1)

- **Symptom:** Der Gast (PC2) kann die Webseite des Servers öffnen, obwohl er gesperrt sein soll.
- **So findest du es:** `show access-lists LANA-IN` zeigt Treffer auf der Web-Zeile, die Gast-Zeile darunter bleibt bei 0.
- **Ursache:** Die Permit-Zeile für Web steht vor dem Gast-Deny: Die Gast-Regel wird nie erreicht (First Match).
- **Fix:** Gast-Deny vor die Web-Permit-Zeile ziehen.
- **Eingebaut:**

```diff
-  deny ip host 192.168.23.12 10.23.2.0 0.0.0.255
-  permit tcp 192.168.23.0 0.0.0.255 host 10.23.2.10 eq 80
+  permit tcp 192.168.23.0 0.0.0.255 host 10.23.2.10 eq 80
+  deny ip host 192.168.23.12 10.23.2.0 0.0.0.255
```

## Ticket 2 (R1)

- **Symptom:** Die ACL greift nicht wie vorgesehen: Der Gast erreicht den Server, der Zähler von `LANA-IN` bleibt 0.
- **So findest du es:** `show ip interface gi0/0` meldet „Outgoing access list is LANA-IN“.
- **Ursache:** ACL in der falschen Richtung (`out` statt `in`) angewendet: Sie betrachtet Verkehr zum LAN statt aus dem LAN.
- **Fix:** `ip access-group LANA-IN in`.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0
-  ip access-group LANA-IN in
+ interface GigabitEthernet0/0
+  ip access-group LANA-IN out
```

## Ticket 3 (R1)

- **Symptom:** Web per IP (`http://10.23.2.10`) geht für PC1, per Name nicht (`www.lab.local`).
- **So findest du es:** `show access-lists LANA-IN` enthält keine Zeile für UDP 53.
- **Ursache:** Die DNS-Zeile fehlt: UDP/53 läuft in das implizite Deny bzw. die Server-Sperre.
- **Fix:** `permit udp any host 10.23.2.10 eq 53` ergänzen.
- **Eingebaut:**

```diff
-  permit udp any host 10.23.2.10 eq 53
```

## Ticket 4 (R1)

- **Symptom:** PC1 und PC2 erreichen 8.8.8.8 nicht mehr (Server geht).
- **So findest du es:** `show access-lists LANA-IN` endet ohne Zeile für das Internet. Der Zähler der letzten Deny-Zeile steigt.
- **Ursache:** Die abschließende Permit-Zeile für das Internet fehlt (implizites Deny).
- **Fix:** `permit ip 192.168.23.0 0.0.0.255 any` am Ende.
- **Eingebaut:**

```diff
-  permit ip 192.168.23.0 0.0.0.255 any
```

## Ticket 5 (R1)

- **Symptom:** Selbst PC1 kann sich nicht mehr per Telnet an R1 anmelden.
- **So findest du es:** `show access-lists VTY-ADMIN` erlaubt 192.168.23.111 statt .11.
- **Ursache:** Die Standard-ACL erlaubt die falsche Verwaltungsadresse (.111).
- **Fix:** `permit host 192.168.23.11`.
- **Eingebaut:**

```diff
- ip access-list standard VTY-ADMIN
-  permit host 192.168.23.11
+ ip access-list standard VTY-ADMIN
+  permit host 192.168.23.111
```

