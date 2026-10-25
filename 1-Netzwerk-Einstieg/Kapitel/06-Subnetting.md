# 6. Subnetting leicht gemacht

> **Darum geht's:** Subnetting heißt: ein großes Netz in kleinere teilen, wie ein Grundstück in Parzellen. Das sieht nach Mathematik aus, ist aber immer derselbe Rechenweg mit einer kleinen Tabelle.
>
> **Danach kannst du:** zu jedem Präfix Maske, Hostzahl und Blockgröße angeben · zu einer Adresse Netz, Broadcast und Hostbereich berechnen · für eine Hostzahl das passende Präfix wählen.

Du brauchst nur **eine Tabelle** und **zwei Regeln**.

## Die Präfixlänge

`/24` bedeutet: Die ersten 24 Bit sind der Netzanteil, die restlichen 8 Bit der Hostanteil.

| Präfix | Maske | Hostbits | Nutzbare Hosts | Blockgröße (letztes Oktett) |
|---|---|---|---|---|
| /24 | 255.255.255.0 | 8 | 254 | 256 |
| /25 | 255.255.255.128 | 7 | 126 | 128 |
| /26 | 255.255.255.192 | 6 | 62 | 64 |
| /27 | 255.255.255.224 | 5 | 30 | 32 |
| /28 | 255.255.255.240 | 4 | 14 | 16 |
| /29 | 255.255.255.248 | 3 | 6 | 8 |
| /30 | 255.255.255.252 | 2 | 2 | 4 |

**Regel 1:** Nutzbare Hosts = 2<sup>Hostbits</sup> − 2 (Netzadresse und Broadcast abziehen).
**Regel 2:** Subnetze beginnen bei Vielfachen der **Blockgröße**.

## Beispiel: In welchem Subnetz liegt 192.168.1.77/26?

1. Blockgröße bei /26 = 64. Die Subnetze beginnen bei .0, .64, .128, .192.
2. 77 liegt zwischen 64 und 127 → Netzadresse **192.168.1.64**.
3. Broadcast = nächstes Netz − 1 → **192.168.1.127**.
4. Hosts: **.65 bis .126** (62 Stück).

## Beispiel: Ich brauche 50 Hosts. Welches Präfix?

Suche die kleinste Potenz von 2, die mindestens 52 ergibt (50 + 2): 2<sup>6</sup> = 64 → 6 Hostbits → **/26** (32 − 6).

## Zwei Hosts im selben Subnetz?

`10.1.1.20/25` und `10.1.1.200/25`: /25 teilt bei .128. Der erste liegt in .0–.127, der zweite in .128–.255. **Verschiedene Subnetze**, also nur über einen Router erreichbar.

## Größere Masken

Für /17 bis /23 wendest du dieselbe Methode im dritten Oktett an. Beispiel /20: Blockgröße im dritten Oktett = 16, `172.16.35.99/20` liegt in `172.16.32.0`.

## Üben, bis es sitzt

Jeden Tag 10 bis 15 Minuten mit dem [Subnetting-Trainer](../../2-CCNA-200-301/Trainer/subnetting-trainer.html). Nach zwei Wochen sind die Blockgrößen im Kopf.

## Das Wichtigste in Kürze

- Nutzbare Hosts = 2^Hostbits − 2.
- Subnetze beginnen bei Vielfachen der Blockgröße, der Broadcast liegt eins vor dem nächsten Netz.
- Für eine Hostzahl suchst du die kleinste Zweierpotenz, die Hosts + 2 abdeckt.

## Selbsttest

1. Wie viele Hosts hat ein /27?
2. Netz- und Broadcastadresse von `192.168.5.200/28`?
3. Welches Präfix für 100 Hosts?

<details><summary>Antworten</summary>

1. **30.** Ein /27 hat 5 Hostbits: 2^5 = 32, minus Netzadresse und Broadcast.
2. **Netz 192.168.5.192, Broadcast 192.168.5.207.** Bei /28 ist die Blockgröße 16. Die Netze beginnen bei 176, 192, 208 … 200 liegt im Block 192 bis 207.
3. **/25.** Du brauchst 100 + 2 = 102 Adressen. Die nächste Zweierpotenz ist 128 = 2^7, also 7 Hostbits und 32 − 7 = 25 Netzbits.

</details>

Zurück: [5. IP-Adressen](05-IP-Adressen.md) · Weiter: [7. Router und Routing](07-Router-und-Routing.md)
