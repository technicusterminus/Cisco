# Übung 3: DNS und ARP beobachten

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

- MX = Mail-Exchanger, zuständiger Mailserver.
- ARP gilt nur im lokalen Netz. Für fremde Netze fragt dein PC nur nach der MAC des Gateways.
</details>
