# Übung 3: DNS und ARP beobachten

**Ziel:** Du siehst, wie Namen zu Adressen werden (DNS) und wie dein Rechner zu einer IP-Adresse die MAC findet (ARP).

## DNS

```
nslookup www.example.com
nslookup -type=MX example.com
nslookup 8.8.8.8
```

1. Welche IP-Adressen hat `www.example.com`? Ändert sich das Ergebnis bei erneutem Aufruf?
2. Welcher DNS-Server hat geantwortet?
3. Was liefert der zweite Befehl, und wofür steht MX?
4. Was liefert der dritte (Rückwärtsauflösung, PTR)?

## ARP

```
arp -a
```

1. Welche Einträge siehst du? Findest du die MAC deines Gateways?
2. Ping ein anderes Gerät im LAN (Drucker, Handy) und führe `arp -a` erneut aus. Was ist neu?
3. Warum gibt es keine ARP-Einträge für Server im Internet?

<details><summary>Lösungshinweise</summary>

- **DNS 1:** Große Seiten haben oft mehrere Adressen, die sich bei jedem Aufruf ändern können (Lastverteilung).
- **DNS 2:** Ganz oben steht der DNS-Server, den du nutzt, meist dein Router oder der des Providers.
- **DNS 3:** Der MX-Eintrag nennt den zuständigen Mailserver (Mail Exchanger) der Domain.
- **DNS 4:** Die Rückwärtsauflösung (PTR) liefert zu einer IP den Namen, bei 8.8.8.8 z. B. `dns.google`.
- **ARP 1:** Die MAC deines Gateways steht in der Liste, weil dein Rechner fast alles über das Gateway schickt.
- **ARP 2:** Nach dem Ping ist das angepingte Gerät mit seiner MAC dazugekommen.
- **ARP 3:** ARP gilt nur im lokalen Netz. Für Ziele im Internet braucht dein PC nur die MAC des Gateways, den Rest erledigen die Router.

</details>
