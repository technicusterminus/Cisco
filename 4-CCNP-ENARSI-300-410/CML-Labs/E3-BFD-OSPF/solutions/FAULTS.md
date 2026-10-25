# Fehlerliste – Lab E3 – BFD für schnelle Fehlererkennung mit OSPF

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R2)

- **Symptom:** Beim Test (R2 Gi0/0 `shutdown`) braucht R1 etwa 40 Sekunden, bis die Route umschwenkt; `show bfd neighbors` auf R1 zeigt keine Sitzung zu R2 im Zustand Up.
- **So findest du es:** `show ip ospf interface Gi0/0` auf R2 nennt kein BFD. `show running-config | section router ospf` auf R2 enthält kein `bfd all-interfaces`. Auf R1 bleibt die Sitzung zu R2 Down.
- **Ursache:** R2 hat OSPF nicht als BFD-Client angemeldet. R1 sendet BFD-Pakete, R2 hat dafür keine Sitzung und antwortet nicht. Der OSPF-Dead-Timer bleibt die einzige Erkennung.
- **Fix:** `bfd all-interfaces` unter `router ospf 1` auf R2.
- **Eingebaut:**

```diff
- bfd all-interfaces
```

## Ticket 2 (R1)

- **Symptom:** Die BFD-Sitzung zwischen R1 und R3 fehlt; auf R1 steht für Gi0/1 keine Sitzung in `show bfd neighbors`.
- **So findest du es:** `show running-config interface Gi0/1` auf R1 enthält keine `bfd interval`-Zeile; Gi0/0 hat sie. `show bfd neighbors` zeigt keine Sitzung zu 10.0.13.2.
- **Ursache:** Ohne `bfd interval …` am Interface gibt es keine Timer für die Sitzung. OSPF meldet den Nachbarn zwar an, BFD startet aber nicht.
- **Fix:** `bfd interval 300 min_rx 300 multiplier 3` unter Gi0/1 auf R1.
- **Eingebaut:**

```diff
- bfd interval 300 min_rx 300 multiplier 3
```

## Ticket 3 (R2)

- **Symptom:** Der Umschwenk bei Ausfall von R2 Gi0/0 dauert rund 9 Sekunden statt unter einer Sekunde, obwohl die Sitzung Up ist.
- **So findest du es:** `show bfd neighbors details` auf R1 zeigt beim Nachbarn 10.0.12.2 den Received Multiplier 30. Die Erkennung dauert 30 × 300 ms = 9 s.
- **Ursache:** R2 sendet Multiplier 30. R1 darf den Nachbarn erst nach 30 ausgebliebenen Paketen für tot erklären. Der größere Wert der beiden Seiten bestimmt die Erkennungszeit.
- **Fix:** `bfd interval 300 min_rx 300 multiplier 3` unter Gi0/0 auf R2.
- **Eingebaut:**

```diff
- bfd interval 300 min_rx 300 multiplier 3
+ bfd interval 300 min_rx 300 multiplier 30
```

## Ticket 4 (R1)

- **Symptom:** Trotz funktionierendem Direktweg läuft der Verkehr von R1 zu 10.2.2.2 über R3.
- **So findest du es:** `show ip ospf interface brief` auf R1 zeigt Kosten 10 für Gi0/0. `show ip route 10.2.2.0` zeigt den Next-Hop 10.0.13.2 (R3), nicht 10.0.12.2.
- **Ursache:** Der manuell gesetzte OSPF-Cost 10 macht den Direktweg teurer (11) als den Umweg über R3 (3). Der Backup-Pfad ist der aktive Pfad.
- **Fix:** `ip ospf cost 10` unter Gi0/0 auf R1 entfernen.
- **Eingebaut:**

```diff
+ ip ospf cost 10
```

## Ticket 5 (R3)

- **Symptom:** Zwischen R3 und R2 gibt es keine BFD-Sitzung, auch nachdem R2 BFD im OSPF angemeldet hat.
- **So findest du es:** `show running-config interface Gi0/1` auf R3 enthält `ip ospf bfd disable`. Das überschreibt `bfd all-interfaces` des Prozesses.
- **Ursache:** Die Interface-Einstellung gewinnt gegen die Prozess-Einstellung: OSPF meldet den Nachbarn an Gi0/1 nicht bei BFD an.
- **Fix:** `ip ospf bfd disable` unter Gi0/1 auf R3 entfernen.
- **Eingebaut:**

```diff
+ ip ospf bfd disable
```
