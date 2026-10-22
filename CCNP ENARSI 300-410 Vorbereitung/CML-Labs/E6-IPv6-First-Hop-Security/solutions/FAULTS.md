# Fehlerliste – Lab E6 – IPv6 First Hop Security: RA Guard und DHCPv6 Guard

**Spoiler.** Erst nach eigener Fehlersuche lesen.

## Ticket 1 (SW)

- **Symptom:** H1 sieht weiterhin die Router Advertisements von ATK (`show ipv6 routers` listet zwei Router), obwohl RA Guard eingerichtet ist.
- **So findest du es:** `show ipv6 nd raguard policy HOST-POLICY` listet als Ziel nur Gi0/1. Auf Gi0/2 fehlt die Bindung (`show running-config interface Gi0/2`).
- **Ursache:** Am Angreifer-Port ist keine RA-Guard-Policy gebunden. RAs von ATK werden ungefiltert weitergeleitet.
- **Fix:** `ipv6 nd raguard attach-policy HOST-POLICY` unter Gi0/2.
- **Eingebaut:**

```diff
- ipv6 nd raguard attach-policy HOST-POLICY
```

## Ticket 2 (SW)

- **Symptom:** H1 bekommt keinen Default-Router und keine Adresse aus 2001:DB8:1::/64; `show ipv6 routers` ist leer.
- **So findest du es:** `show ipv6 nd raguard policy HOST-POLICY` listet Gi0/0 (R1), Gi0/1 und Gi0/2 als Ziele. Die Policy ROUTER-POLICY hat kein Ziel.
- **Ursache:** Der Router-Port trägt die Host-Policy. RAs des legitimen Routers werden dort verworfen, H1 sieht nie einen Router.
- **Fix:** `ipv6 nd raguard attach-policy ROUTER-POLICY` unter Gi0/0.
- **Eingebaut:**

```diff
- ipv6 nd raguard attach-policy ROUTER-POLICY
+ ipv6 nd raguard attach-policy HOST-POLICY
```

## Ticket 3 (SW)

- **Symptom:** ATK schickt RAs, und sie erreichen H1, obwohl am Port Gi0/2 die Host-Policy hängt.
- **So findest du es:** `show ipv6 nd raguard policy HOST-POLICY` zeigt `device-role router`. Damit lässt die Policy RAs durch.
- **Ursache:** Die Policy heißt HOST-POLICY, hat aber die Rolle router. Sie erlaubt RAs auf allen Ports, an die sie gebunden ist.
- **Fix:** `device-role host` in HOST-POLICY.
- **Eingebaut:**

```diff
- device-role host
+ device-role router
```

## Ticket 4 (SW)

- **Symptom:** H1 bekommt per DHCPv6 eine Adresse aus 2001:DB8:BAD::/64, obwohl der Port von ATK eine Client-Policy trägt.
- **So findest du es:** `show ipv6 dhcp guard policy CLIENT-POLICY` listet als Ziel nur Gi0/1, nicht Gi0/2.
- **Ursache:** Am Angreifer-Port ist kein DHCPv6 Guard gebunden. Advertise und Reply des Rogue-Servers werden durchgelassen.
- **Fix:** `ipv6 dhcp guard attach-policy CLIENT-POLICY` unter Gi0/2.
- **Eingebaut:**

```diff
- ipv6 dhcp guard attach-policy CLIENT-POLICY
```

## Ticket 5 (SW)

- **Symptom:** H1 bekommt gar keine DHCPv6-Adresse mehr, auch nicht von R1; SLAAC funktioniert.
- **So findest du es:** `show ipv6 dhcp guard policy SERVER-POLICY` zeigt `device-role client`.
- **Ursache:** Der Port von R1 trägt eine Policy mit Rolle client. Server-Nachrichten (Advertise, Reply) von R1 werden verworfen.
- **Fix:** `device-role server` in SERVER-POLICY.
- **Eingebaut:**

```diff
- device-role server
+ device-role client
```
