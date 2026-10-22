# Fehlerliste – Lab E4 – Unicast Reverse Path Forwarding: Strict, Loose, ACL

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (PE)

- **Symptom:** Ein Test mit gefälschter Absenderadresse (`ping 192.0.2.88 source Loopback2` auf CE) kommt durch; die Verwurfs-Zähler an PE Gi0/0 bleiben bei 0.
- **So findest du es:** `show ip interface Gi0/0` nennt „IP verify source reachable-via ANY, ACL 120“ statt RX.
- **Ursache:** Am Kundenport steht Loose statt Strict. Die Absenderadresse 10.200.0.77 liegt in einem Netz, das der PE kennt (Lo9), also besteht sie den Loose-Check.
- **Fix:** `ip verify unicast source reachable-via rx 120` unter Gi0/0.
- **Eingebaut:**

```diff
- ip verify unicast source reachable-via rx 120
+ ip verify unicast source reachable-via any 120
```

## Ticket 2 (PE)

- **Symptom:** Pakete aus dem Internet mit Absender 10.99.99.1 (`ping 203.0.113.1 source Loopback2` auf NET) erreichen den Kunden, obwohl Loose Mode eingeschaltet ist.
- **So findest du es:** `show ip interface Gi0/1` zeigt „allow default“ in der uRPF-Zeile. `show ip route 0.0.0.0` bestätigt die Default-Route.
- **Ursache:** Mit `allow-default` zählt die Default-Route als gültiger Rückweg. Jeder Absender hat damit einen „Weg“ und besteht den Loose-Check.
- **Fix:** `ip verify unicast source reachable-via any` ohne `allow-default` unter Gi0/1.
- **Eingebaut:**

```diff
- ip verify unicast source reachable-via any
+ ip verify unicast source reachable-via any allow-default
```

## Ticket 3 (PE)

- **Symptom:** Der Altbestand 10.77.0.1 wird verworfen, obwohl die Ausnahme-ACL dafür existiert; `show access-lists 120` zählt keine Treffer.
- **So findest du es:** `show access-lists 120` zeigt das Netz 10.77.1.0 statt 10.77.0.0 und keine Treffer.
- **Ursache:** Die Ausnahme-ACL passt auf das falsche Netz. Der Altbestand 10.77.0.1 fällt durch den Strict-Check und trifft auf kein permit.
- **Fix:** `access-list 120 permit ip 10.77.0.0 0.0.0.255 any`.
- **Eingebaut:**

```diff
-access-list 120 permit ip 10.77.0.0 0.0.0.255 any
+access-list 120 permit ip 10.77.1.0 0.0.0.255 any
```

## Ticket 4 (PE)

- **Symptom:** Der legitime Kundenverkehr (`ping 192.0.2.88 source Loopback1` auf CE) kommt nicht mehr durch; der Zähler der Verwürfe an PE Gi0/0 steigt mit jedem Ping.
- **So findest du es:** `show ip route 203.0.113.1` auf dem PE liefert nur die Default-Route zu NET. `show ip route static` zeigt 203.0.131.0/24 (Zahlendreher).
- **Ursache:** Das Kundennetz fehlt im PE (Route zeigt auf 203.0.131.0/24). Die Absenderadresse 203.0.113.1 hat keine Route über Gi0/0, der Strict-Check schlägt fehl und die ACL erlaubt sie nicht.
- **Fix:** `ip route 203.0.113.0 255.255.255.0 198.51.100.2`.
- **Eingebaut:**

```diff
-ip route 203.0.113.0 255.255.255.0 198.51.100.2
+ip route 203.0.131.0 255.255.255.0 198.51.100.2
```
