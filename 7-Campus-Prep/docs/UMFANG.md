# Umfang und Phasen

Ein Projekt, eine Welt: ein simulierter C9800-WLC mit Access Points und WLAN-Clients, dazu ein simuliertes Catalyst Center, das diese Welt verwaltet. Beide lesen denselben Zustand (`campusprep/world.py`); das Catalyst Center hat keinen eigenen Gerätebestand.

| Phase | Inhalt | Stand |
|---|---|---|
| 1 | WLC-Kern: WLAN, Policy Profile, Policy Tag, AP-Tagging, Client-Assoziation mit Begründung; Show-Befehle mit belegtem Format; Catalyst Center: Token und Geräteinventar per REST | umgesetzt |
| 2a | WLC-Weboberfläche: Dashboard, Monitoring (APs, Clients), Configuration (WLANs, Policy, Tags, AP-Tags), CLI-Ansicht, Client-Diagnose; jeder Dialog zeigt sein CLI-Äquivalent | umgesetzt |
| 2b | Catalyst-Center-Weboberfläche | offen |
| 2c | Lab-Engine (geführt/Prüfung, Hinweisstufen, Funktion und Sicherheit getrennt, Verständnisfragen) und sechs WLC-Labs | umgesetzt |
| 2d | Persistenz: automatischer Zustand, benannte Stände, Lab-Fortschritt | umgesetzt |
| 2e | Eigenständige Browser-Variante `WLC-Simulator.html` (Engine in JavaScript, lokaler Speicher), Paritätstest gegen die Python-Engine | umgesetzt |
| 3a | FlexConnect: Flex Profile, Site Tag, lokales Switching, AP-Modus; Labs 07 und 08 (CCNP Enterprise Wireless) | umgesetzt |
| 3b | 802.1X mit RADIUS: RADIUS-Server, Server Group, Authentication List, WLAN mit WPA2 Enterprise, AAA Override, Server-Redundanz; `show aaa servers`; Labs 09 bis 11 | umgesetzt |
| 3c | Local Web Authentication: lokale Benutzer, Login-Liste, Autorisierung, Parameter Map, Web Auth im WLAN; Zustand Webauth Pending; Labs 12 und 13 | umgesetzt |
| 3d | Mobility: Gruppenname, Peers, Tunnelzustand, Inter-Controller-Roaming; `show wireless mobility summary`; Labs 14 und 15 | umgesetzt |
| 3e | RF-Profile und RF Tags: Profile je Band, Sendeleistung, Band an/aus, Zuordnung per AP; Labs 16 und 17 | umgesetzt |
| 3f | WLC: QoS, Multicast, Location; weitere belegte Show-Befehle | offen |
| 4 | Catalyst Center: Sites, Network Settings, Provisioning des WLC, Assurance, Templates (nur mit belegten Antwortformaten) | offen |
