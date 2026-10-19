# Fehlerliste – Lab 12 – Multicast mit IGMP und PIM Sparse Mode

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (R3)

- **Symptom:** R3 hat keinen PIM-Nachbarn zu R2; REC1 bekommt keine Pakete, REC2 funktioniert.
- **Ursache:** `ip pim sparse-mode` fehlt auf dem Uplink von R3.
- **Fix:** PIM auf R3 Gi0/0 aktivieren.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/0
-  ip pim sparse-mode
+ interface GigabitEthernet0/0
```

## Ticket 2 (R4)

- **Symptom:** REC2 empfängt keine Pakete, `show ip pim rp mapping` auf R4 zeigt einen anderen RP als auf den übrigen Routern.
- **Ursache:** R4 kennt eine falsche RP-Adresse, sein (*,G)-Join geht ins Leere.
- **Fix:** RP-Adresse auf 10.255.0.2 korrigieren.
- **Eingebaut:**

```diff
- ip pim rp-address 10.255.0.2
+ ip pim rp-address 10.255.0.9
```

## Ticket 3 (R1)

- **Symptom:** Weder REC1 noch REC2 empfangen etwas, obwohl alle Join-Zustände stehen. Auf R1 gibt es keine `(S,G)`-Einträge.
- **Ursache:** Das Quell-LAN-Interface von R1 (Gi0/1) ist nicht PIM-aktiv: Der First-Hop-Router erkennt die Quelle nicht und sendet keine Register-Nachricht.
- **Fix:** PIM Sparse Mode auf R1 Gi0/1.
- **Eingebaut:**

```diff
- interface GigabitEthernet0/1
-  ip pim sparse-mode
+ interface GigabitEthernet0/1
```

## Ticket 4 (R2)

- **Symptom:** Der RP zeigt `(*,G)`-Einträge nicht und Multicast wird auf R2 nicht weitergeleitet.
- **Ursache:** `ip multicast-routing` fehlt auf R2: Der Router lässt keinen Multicast-Verkehr zu.
- **Fix:** Befehl global auf R2 setzen.
- **Eingebaut:**

```diff
- ip multicast-routing
```

