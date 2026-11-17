# Umfang und Phasen

Ein Projekt, eine Welt: ein simulierter C9800-WLC mit Access Points und WLAN-Clients, dazu ein simuliertes Catalyst Center, das diese Welt verwaltet. Beide lesen denselben Zustand (`campusprep/world.py`); das Catalyst Center hat keinen eigenen Gerätebestand.

| Phase | Inhalt | Stand |
|---|---|---|
| 1 | WLC-Kern: WLAN, Policy Profile, Policy Tag, AP-Tagging, Client-Assoziation mit Begründung; Show-Befehle mit belegtem Format; Catalyst Center: Token und Geräteinventar per REST | umgesetzt |
| 2a | WLC-Weboberfläche: Dashboard, Monitoring (APs, Clients), Configuration (WLANs, Policy, Tags, AP-Tags), CLI-Ansicht, Client-Diagnose; jeder Dialog zeigt sein CLI-Äquivalent | umgesetzt |
| 2b | Catalyst-Center-Weboberfläche, Lab-Engine wie im Datacenter Prep | offen |
| 3 | WLC: 802.1x/RADIUS, FlexConnect, RF-Profile, Mobility; weitere belegte Show-Befehle | offen |
| 4 | Catalyst Center: Sites, Network Settings, Provisioning des WLC, Assurance, Templates (nur mit belegten Antwortformaten) | offen |
