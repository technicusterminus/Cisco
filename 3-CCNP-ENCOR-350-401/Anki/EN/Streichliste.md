# ENCOR Kompendium EN: gestrichene und geteilte Karten

Quelle: ENCOR v1.2 Kompendium 5.2 (1.776 Karten). Ergebnis: 1.524 Karten. Gestrichen: 268. Neu durch Teilung: 16.

Bei 105 gestrichenen Karten stand ein Zusatzdetail, das auf der behaltenen Karte fehlte. Es steht jetzt in der deutschen Erklärung der behaltenen Karte (unten mit „Detail übernommen in …“ markiert).

## Geteilte Karten (Liste mit mehr als 4 Punkten)

- E12-1.2.b-011 → E12-1.2.b-011 + E12-1.2.b-011b
- E12-3.2.a-032 → E12-3.2.a-032 + E12-3.2.a-032b
- E12-3.2.c-053 → E12-3.2.c-053 + E12-3.2.c-053b
- E12-4.5-006 → E12-4.5-006 + E12-4.5-006b
- E12-4.5-026 → E12-4.5-026 + E12-4.5-026b
- E12-4.6-034 → E12-4.6-034 + E12-4.6-034b
- E12-4.6-036 → E12-4.6-036 + E12-4.6-036b
- E12-5.1.a-015 → E12-5.1.a-015 + E12-5.1.a-015b
- E12-5.2.b-018 → E12-5.2.b-018 + E12-5.2.b-018b
- E12-5.3-022 → E12-5.3-022 + E12-5.3-022b
- E12-5.4.b-015 → E12-5.4.b-015 + E12-5.4.b-015b
- E12-5.4.b-019 → E12-5.4.b-019 + E12-5.4.b-019b
- E12-5.4.c-009 → E12-5.4.c-009 + E12-5.4.c-009b
- E12-6.2-001 → E12-6.2-001 + E12-6.2-001b
- E12-6.4-017 → E12-6.4-017 + E12-6.4-017b
- E12-6.6-021 → E12-6.6-021 + E12-6.6-021b

## Gestrichene Karten

### Ziel 1.1.a

- E12-1.1.a-005: Doppelt zu E12-1.1.a-004 (ebenfalls 2-Tier/Collapsed Core für kleinen Standort).

### Ziel 1.1.b

- E12-1.1.b-002: Triviale Definition; die Abgrenzung (FHRP schützt nur das Gateway) fragt E12-1.1.b-007 besser ab.
- E12-1.1.b-010: Doppelt zu E12-1.1.b-004 und E12-1.1.b-021 (SSO + NSF).
- E12-1.1.b-024: Doppelt zu E12-1.1.b-015 (SSO aktivieren, dort zusammen mit der Prüfung). Detail übernommen in E12-1.1.b-015.

### Ziel 1.2.a

- E12-1.2.a-005: Doppelt zu E12-1.2.a-030 (OMP zentral über den Controller statt Sessions zwischen Edges). Detail übernommen in E12-1.2.a-030.
- E12-1.2.a-014: Doppelt zu E12-1.2.a-022 (reservierte VPNs 0 und 512, dort vollständiger). Detail übernommen in E12-1.2.a-022.
- E12-1.2.a-015: Trivial; dass der Manager nie im Datenpfad liegt, fragen E12-1.2.a-001 und E12-1.2.a-016 ab.

### Ziel 1.2.b

- E12-1.2.b-007: Doppelt zu E12-1.2.b-013 (Controller-Ausfall, dort mit der konkreten Zeit). Detail übernommen in E12-1.2.b-013.

### Ziel 1.3.a

- E12-1.3.a-028: Doppelt zu E12-1.3.a-017 (Anycast Gateway beim Wechsel des Edges). Detail übernommen in E12-1.3.a-017.

### Ziel 1.4

- E12-1.4-010: Doppelt zu E12-1.4-009 (AF31 gegen AF33).
- E12-1.4-019: Doppelt zu E12-1.4-018 (Client markiert selbst EF, Trust Boundary).
- E12-1.4-048: Doppelt zu E12-1.4-016 (Priority-Klasse wird nur bei Stau begrenzt). Detail übernommen in E12-1.4-016.
- E12-1.4-062: Doppelt zu E12-1.4-022 (show policy-map interface). Detail übernommen in E12-1.4-022.

### Ziel 2.1.a

- E12-2.1.a-002: Durch E12-2.1.a-001 und E12-2.1.a-008 abgedeckt (Workstation = Typ 2).
- E12-2.1.a-003: Durch E12-2.1.a-001 und E12-2.1.a-008 abgedeckt (ESXi = Typ 1).

### Ziel 2.1.b

- E12-2.1.b-001: Triviale Definition (VM bekommt virtuelle Hardware).
- E12-2.1.b-003: Triviale Definition (vNIC am vSwitch).
- E12-2.1.b-004: Doppelt zu E12-2.1.b-007 (zwei VMs auf demselben Host fallen gemeinsam aus).

### Ziel 2.1.c

- E12-2.1.c-003: Triviale Definition (Uplinks des vSwitch); der Trunk-Aspekt steckt in E12-2.1.c-009. Detail übernommen in E12-2.1.c-009.
- E12-2.1.c-005: Doppelt zu E12-2.1.c-009 (VLAN fehlt auf dem Trunk des Hosts).

### Ziel 2.2.a

- E12-2.2.a-002: In E12-2.2.a-001 enthalten (gleiche Präfixe in zwei VRFs).
- E12-2.2.a-013: Doppelt zu E12-2.2.a-031 (show vrf, dort mit RD und Detail).
- E12-2.2.a-014: Durch E12-2.2.a-008 und das Exhibit E12-2.2.a-018 abgedeckt (ping vrf).
- E12-2.2.a-023: Doppelt zu E12-2.2.a-006 (IP-Adresse wird bei vrf forwarding gelöscht).
- E12-2.2.a-024: In E12-2.2.a-003 enthalten (VRF-Lite braucht pro VRF Link und Routing-Instanz). Detail übernommen in E12-2.2.a-003.
- E12-2.2.a-025: Doppelt zu E12-2.2.a-008 und E12-2.2.a-018 (ping ohne vrf scheitert). Detail übernommen in E12-2.2.a-008.
- E12-2.2.a-027: Doppelt zu E12-2.2.a-004 und E12-2.2.a-016 (VRF für IPv4 und IPv6 anlegen). Detail übernommen in E12-2.2.a-004.
- E12-2.2.a-028: Doppelt zu E12-2.2.a-005 (Interface einer VRF zuordnen).
- E12-2.2.a-029: Doppelt zu E12-2.2.a-007 (show ip route vrf).
- E12-2.2.a-030: Doppelt zu E12-2.2.a-008 (ping vrf).
- E12-2.2.a-032: Durch E12-2.2.a-009 und E12-2.2.a-021 abgedeckt (statische Route in VRF, mit global).
- E12-2.2.a-033: Doppelt zu E12-2.2.a-019 (OSPF-Prozess pro VRF).

### Ziel 2.2.b

- E12-2.2.b-014: Allgemein; die Phasen von IKE fragt E12-2.2.b-015 konkreter ab.
- E12-2.2.b-018: In E12-2.2.b-064 enthalten (Transform-Set im IPsec-Profil).
- E12-2.2.b-019: In E12-2.2.b-064 enthalten (tunnel protection am Tunnel). Detail übernommen in E12-2.2.b-064.
- E12-2.2.b-021: Doppelt zu E12-2.2.b-073 (show crypto ikev2 sa).
- E12-2.2.b-026: Doppelt zu E12-2.2.b-061 (Pre-Shared Key für IKEv1-Peer). Detail übernommen in E12-2.2.b-061.
- E12-2.2.b-045: Doppelt zum Exhibit E12-2.2.b-054 (encaps steigt, decaps bleibt 0). Detail übernommen in E12-2.2.b-054.
- E12-2.2.b-050: Doppelt zu E12-2.2.b-005, E12-2.2.b-040 und E12-2.2.b-042 (rekursives Routing).
- E12-2.2.b-052: Doppelt zu E12-2.2.b-001 (GRE unter IPsec wegen Multicast). Detail übernommen in E12-2.2.b-001.
- E12-2.2.b-055: Doppelt zu E12-2.2.b-003 (GRE-Tunnel konfigurieren).
- E12-2.2.b-056: Doppelt zu E12-2.2.b-043 (ip mtu und adjust-mss). Detail übernommen in E12-2.2.b-043.
- E12-2.2.b-057: Doppelt zu E12-2.2.b-044 (GRE-Keepalive). Detail übernommen in E12-2.2.b-044.
- E12-2.2.b-058: Doppelt zu E12-2.2.b-006 (Tunnel prüfen).
- E12-2.2.b-060: Doppelt zu E12-2.2.b-025 (ISAKMP-Policy).
- E12-2.2.b-062: Doppelt zu E12-2.2.b-017 (Transform-Set). Detail übernommen in E12-2.2.b-017.
- E12-2.2.b-066: Doppelt zu E12-2.2.b-020 und dem Exhibit E12-2.2.b-046 (show crypto isakmp sa). Detail übernommen in E12-2.2.b-046.
- E12-2.2.b-067: In E12-2.2.b-020 enthalten (show crypto ipsec sa).
- E12-2.2.b-069: Doppelt zu E12-2.2.b-033 (IKEv2-Proposal). Detail übernommen in E12-2.2.b-033.
- E12-2.2.b-070: Doppelt zu E12-2.2.b-035 (IKEv2-Keyring). Detail übernommen in E12-2.2.b-035.
- E12-2.2.b-071: Doppelt zu E12-2.2.b-036 (IKEv2-Profil).
- E12-2.2.b-072: Doppelt zu E12-2.2.b-037 (IKEv2-Profil im IPsec-Profil).

### Ziel 2.3.a

- E12-2.3.a-002: In E12-2.3.a-001 und E12-2.3.a-008 enthalten (EID bleibt beim Umzug gleich).
- E12-2.3.a-004: In E12-2.3.a-010 enthalten (Map-Register an den Map Server). Detail übernommen in E12-2.3.a-010.
- E12-2.3.a-018: Doppelt zu E12-1.3.a-025 (unbekannte EID geht zum Border). Detail übernommen in E12-1.3.a-025.

### Ziel 2.3.b

- E12-2.3.b-003: Doppelt zu E12-2.3.b-004 (VNI 24 Bit, 16 Millionen Segmente).
- E12-2.3.b-007: Doppelt zu E12-1.3.a-018 (LISP findet das Ziel, VXLAN transportiert).

### Ziel 3.1.a

- E12-3.1.a-010: Doppelt zu E12-3.1.a-021 (Gegenseite ohne DTP, auto wird nie Trunk).
- E12-3.1.a-012: In E12-3.1.a-049 enthalten (allowed vlan add/remove).
- E12-3.1.a-016: Doppelt zu E12-3.1.a-003 und E12-3.1.a-023 (Native VLAN muss gleich sein).
- E12-3.1.a-018: Doppelt zu E12-3.1.a-013 (VLAN erlaubt, aber nicht angelegt). Detail übernommen in E12-3.1.a-013.
- E12-3.1.a-020: Doppelt zu E12-3.1.a-014 (erlaubt und aktiv, aber nicht forwarding).
- E12-3.1.a-043: In E12-3.1.a-004 enthalten (show interfaces trunk). Detail übernommen in E12-3.1.a-004.
- E12-3.1.a-046: In E12-3.1.a-004 enthalten (show interfaces switchport). Detail übernommen in E12-3.1.a-004.
- E12-3.1.a-047: In E12-3.1.a-009 enthalten (switchport mode trunk). Detail übernommen in E12-3.1.a-009.
- E12-3.1.a-050: Doppelt zu E12-3.1.a-008 (switchport nonegotiate).

### Ziel 3.1.b

- E12-3.1.b-008: Doppelt zu E12-3.1.b-042 (show etherchannel summary).
- E12-3.1.b-010: In E12-3.1.b-023 enthalten (Flag P = gebündelt). Detail übernommen in E12-3.1.b-023.
- E12-3.1.b-012: Doppelt zu E12-3.1.b-043 (show lacp neighbor).
- E12-3.1.b-024: Doppelt zu E12-3.1.b-013 (abweichende VLAN-Einstellungen eines Mitglieds).
- E12-3.1.b-026: Doppelt zu E12-3.1.b-016 (ein Flow nutzt nur einen Link). Detail übernommen in E12-3.1.b-016.
- E12-3.1.b-027: Doppelt zu E12-3.1.b-019 (min-links).
- E12-3.1.b-036: Doppelt zu E12-3.1.b-031 (LACP System Priority entscheidet).
- E12-3.1.b-037: Doppelt zu E12-3.1.b-007 (channel-group mode active). Detail übernommen in E12-3.1.b-007.
- E12-3.1.b-040: Doppelt zu E12-3.1.b-025 (Layer-3-Port-Channel). Detail übernommen in E12-3.1.b-025.
- E12-3.1.b-041: Doppelt zu E12-3.1.b-033 (load-balance src-dst-ip). Detail übernommen in E12-3.1.b-033.
- E12-3.1.b-046: Doppelt zu E12-3.1.b-019 (min-links).
- E12-3.1.b-047: Doppelt zu E12-3.1.b-032 (lacp rate fast). Detail übernommen in E12-3.1.b-032.

### Ziel 3.1.c

- E12-3.1.c-004: Doppelt zu E12-3.1.c-002 (gleiche Priorität, niedrigere MAC gewinnt). Detail übernommen in E12-3.1.c-002.
- E12-3.1.c-010: In E12-3.1.c-062 enthalten (Proposal/Agreement).
- E12-3.1.c-012: In E12-3.1.c-066 enthalten (spanning-tree mode).
- E12-3.1.c-023: In E12-3.1.c-072 und E12-3.1.c-074 enthalten (PortFast und BPDU Guard).
- E12-3.1.c-028: In E12-3.1.c-026 enthalten (root-inconsistent erholt sich selbst).
- E12-3.1.c-029: Doppelt zu E12-3.1.c-076 (spanning-tree guard root).
- E12-3.1.c-037: In E12-3.1.c-034 enthalten (alle drei Werte müssen gleich sein). Detail übernommen in E12-3.1.c-034.
- E12-3.1.c-048: Doppelt zu E12-3.1.c-042 (Lastverteilung nur pro MST-Instanz).
- E12-3.1.c-063: Doppelt zu E12-3.1.c-003 und E12-3.1.c-015 (4096er-Schritte, 32778).
- E12-3.1.c-068: Doppelt zu E12-3.1.c-014 (spanning-tree vlan priority). Detail übernommen in E12-3.1.c-014.
- E12-3.1.c-079: Doppelt zu E12-3.1.c-058 (errdisable recovery).
- E12-3.1.c-080: Doppelt zu E12-3.1.c-017 (show spanning-tree vlan). Detail übernommen in E12-3.1.c-017.
- E12-3.1.c-083: Doppelt zu E12-3.1.c-030 (show spanning-tree inconsistentports). Detail übernommen in E12-3.1.c-030.
- E12-3.1.c-085: Doppelt zu E12-3.1.c-035 (MST-Region konfigurieren).
- E12-3.1.c-088: Doppelt zu E12-3.1.c-039 (show spanning-tree mst configuration). Detail übernommen in E12-3.1.c-039.

### Ziel 3.2.a

- E12-3.2.a-015: Doppelt zu E12-3.2.a-041 (Referenzbandbreite 100 Mbit/s). Detail übernommen in E12-3.2.a-041.
- E12-3.2.a-016: Doppelt zu E12-3.2.a-041 (1G und 10G haben Kosten 1).
- E12-3.2.a-029: Doppelt zu E12-3.2.a-003 (gleiche LSDB, eigener SPF-Baum). Detail übernommen in E12-3.2.a-003.
- E12-3.2.a-039: In E12-3.2.a-011 und E12-3.2.a-026 enthalten (DUAL, Feasibility Condition). Detail übernommen in E12-3.2.a-011.

### Ziel 3.2.b

- E12-3.2.b-005: Doppelt zu E12-3.2.b-087 (router-id setzen). Detail übernommen in E12-3.2.b-087.
- E12-3.2.b-014: Doppelt zu E12-3.2.a-040 (Zweck des DR).
- E12-3.2.b-019: In E12-3.2.b-094 enthalten (ip ospf network). Detail übernommen in E12-3.2.b-094.
- E12-3.2.b-022: In E12-3.2.b-105, -106 und -107 einzeln enthalten.
- E12-3.2.b-049: Doppelt zu E12-3.2.b-114 (OSPFv3-Nachbarn anzeigen).
- E12-3.2.b-053: In E12-3.2.b-078 enthalten (Timer pro Netztyp). Detail übernommen in E12-3.2.b-078.
- E12-3.2.b-057: In E12-3.2.b-082 und E12-3.2.b-086 enthalten (Topologie und Präfixe getrennt).
- E12-3.2.b-083: Doppelt zu E12-3.2.b-097 (summary-address am ASBR). Detail übernommen in E12-3.2.b-097.
- E12-3.2.b-089: Doppelt zu E12-3.2.b-004 (ip ospf area am Interface). Detail übernommen in E12-3.2.b-004.
- E12-3.2.b-090: Doppelt zu E12-3.2.b-020 (passive-interface default). Detail übernommen in E12-3.2.b-020.
- E12-3.2.b-092: Doppelt zu E12-3.2.b-041 (auto-cost reference-bandwidth).
- E12-3.2.b-096: Doppelt zu E12-3.2.b-030 (area range). Detail übernommen in E12-3.2.b-030.
- E12-3.2.b-098: Doppelt zu E12-3.2.b-080 (Stub und Totally Stubby).
- E12-3.2.b-100: Doppelt zu E12-3.2.b-037 (default-information originate always). Detail übernommen in E12-3.2.b-037.
- E12-3.2.b-102: Doppelt zu E12-3.2.b-079 (HMAC-SHA-256 über Key Chain). Detail übernommen in E12-3.2.b-079.
- E12-3.2.b-104: In E12-3.2.b-033 und E12-3.2.b-034 enthalten (area filter-list). Detail übernommen in E12-3.2.b-033.
- E12-3.2.b-111: In E12-3.2.b-047 enthalten (router ospfv3 mit Address Family).
- E12-3.2.b-112: In E12-3.2.b-047 enthalten (ospfv3 ipv6 area am Interface). Detail übernommen in E12-3.2.b-047.
- E12-3.2.b-113: Doppelt zu E12-3.2.b-046 (OSPFv3 klassische Syntax).

### Ziel 3.2.c

- E12-3.2.c-004: Doppelt zu E12-3.2.c-062 (eBGP-Nachbar konfigurieren).
- E12-3.2.c-005: Doppelt zu E12-3.2.c-063 (network mask).
- E12-3.2.c-009: Doppelt zu E12-3.2.c-082 (show ip bgp summary).
- E12-3.2.c-010: Doppelt zum Exhibit E12-3.2.c-050 (Zahl in State/PfxRcd).
- E12-3.2.c-014: In E12-3.2.c-047 enthalten (unerreichbarer Next Hop).
- E12-3.2.c-016: In E12-3.2.c-018 enthalten (Weight wirkt nur lokal). Detail übernommen in E12-3.2.c-018.
- E12-3.2.c-024: Doppelt zu E12-3.2.c-044 (MED nur bei gleichem Nachbar-AS). Detail übernommen in E12-3.2.c-044.
- E12-3.2.c-028: Doppelt zu E12-3.2.c-046 (Longest Match vor BGP-Pfadwahl).
- E12-3.2.c-029: Doppelt zu E12-3.2.c-083 (show ip bgp prefix).
- E12-3.2.c-042: Doppelt zu E12-3.2.c-006 (network braucht exakte Maske).
- E12-3.2.c-058: Doppelt zu E12-3.2.c-081 (clear ip bgp soft in). Detail übernommen in E12-3.2.c-081.
- E12-3.2.c-060: Doppelt zu E12-3.2.c-069 (neighbor password). Detail übernommen in E12-3.2.c-069.
- E12-3.2.c-064: In E12-3.2.c-059 enthalten (update-source und ebgp-multihop).
- E12-3.2.c-066: Doppelt zu E12-3.2.c-037 (IPv6-BGP-Nachbar aktivieren). Detail übernommen in E12-3.2.c-037.
- E12-3.2.c-075: Doppelt zu E12-3.2.c-032 (neighbor weight). Detail übernommen in E12-3.2.c-032.
- E12-3.2.c-076: Doppelt zu E12-3.2.c-054 (set local-preference). Detail übernommen in E12-3.2.c-054.
- E12-3.2.c-077: Doppelt zu E12-3.2.c-056 (set as-path prepend). Detail übernommen in E12-3.2.c-056.

### Ziel 3.2.d

- E12-3.2.d-006: Doppelt zu E12-3.2.d-010 (deny in PBR heißt nicht verwerfen). Detail übernommen in E12-3.2.d-010.
- E12-3.2.d-009: In E12-3.2.d-022 enthalten (show ip policy).
- E12-3.2.d-012: Doppelt zu E12-3.2.d-005 (kein PBR-Treffer, normales Routing).
- E12-3.2.d-015: Doppelt zu E12-3.2.d-005 (Routing-Tabelle entscheidet ohne PBR-Treffer). Detail übernommen in E12-3.2.d-005.
- E12-3.2.d-020: Doppelt zu E12-3.2.d-014 (verify-availability mit Track). Detail übernommen in E12-3.2.d-014.

### Ziel 3.3.a

- E12-3.3.a-003: In E12-3.3.a-001 enthalten (jede Stufe zählt eins hoch).
- E12-3.3.a-009: In E12-3.3.a-027 enthalten (NTP nutzt UDP 123).
- E12-3.3.a-037: Doppelt zu E12-3.3.a-021 (ntp source).
- E12-3.3.a-039: Doppelt zu E12-3.3.a-006 (show ntp status/associations). Detail übernommen in E12-3.3.a-006.
- E12-3.3.a-040: Doppelt zu E12-3.3.a-025 (Zeitzone und Sommerzeit).

### Ziel 3.3.b

- E12-3.3.b-010: Doppelt zu E12-3.3.b-004 und dem Exhibit E12-3.3.b-029 (Pool erschöpft).
- E12-3.3.b-022: Doppelt zu E12-3.3.b-004 und E12-3.3.b-029 (Pool-Adressen erschöpft).
- E12-3.3.b-026: Doppelt zu E12-3.3.b-038 (clear ip nat translation). Detail übernommen in E12-3.3.b-038.
- E12-3.3.b-030: Doppelt zu E12-3.3.b-006 (ip nat inside/outside).
- E12-3.3.b-031: Doppelt zu E12-3.3.b-007 (statisches NAT). Detail übernommen in E12-3.3.b-007.
- E12-3.3.b-032: Doppelt zu E12-3.3.b-012 (Port-Weiterleitung).
- E12-3.3.b-033: Doppelt zu E12-3.3.b-011 (NAT-Pool anlegen). Detail übernommen in E12-3.3.b-011.
- E12-3.3.b-035: Doppelt zu E12-3.3.b-008 (PAT auf Interface-Adresse). Detail übernommen in E12-3.3.b-008.
- E12-3.3.b-037: Doppelt zu E12-3.3.b-013 (show ip nat translations/statistics). Detail übernommen in E12-3.3.b-013.

### Ziel 3.3.c

- E12-3.3.c-004: Doppelt zu E12-1.1.b-022 und E12-3.3.c-030 (HSRP ohne Preempt).
- E12-3.3.c-006: Doppelt zu E12-3.3.c-037 (show standby brief).
- E12-3.3.c-015: Doppelt zu E12-3.3.c-039 (show vrrp brief).
- E12-3.3.c-016: Doppelt zu E12-1.1.a-023 (STP-Root und HSRP-Active auf demselben Switch).
- E12-3.3.c-031: In E12-3.3.c-005 enthalten (HSRPv2 mit VIP). Detail übernommen in E12-3.3.c-005.
- E12-3.3.c-034: Doppelt zu E12-3.3.c-028 (HSRP-MD5).
- E12-3.3.c-035: In E12-3.3.c-008 und E12-3.3.c-017 enthalten (Tracking mit decrement). Detail übernommen in E12-3.3.c-008.
- E12-3.3.c-036: Doppelt zu E12-3.3.c-026 (HSRP IPv6 autoconfig).
- E12-3.3.c-038: Doppelt zu E12-3.3.c-027 (VRRPv3).

### Ziel 3.3.d

- E12-3.3.d-004: Doppelt zu E12-3.3.d-003 (RPF-Check verwirft).
- E12-3.3.d-016: Doppelt zu E12-3.3.d-011 (SSM braucht IGMPv3).
- E12-3.3.d-023: In E12-3.3.d-054 und E12-3.3.d-058 enthalten (show ip mroute, show ip rpf).
- E12-3.3.d-026: Doppelt zu E12-3.3.d-013 und E12-3.3.d-014 (SSM ohne RP).
- E12-3.3.d-030: Doppelt zu E12-3.3.d-018 (Bidir-PIM ohne Zustand pro Quelle). Detail übernommen in E12-3.3.d-018.
- E12-3.3.d-031: Doppelt zu E12-3.3.d-020 (MSDP zwischen RPs). Detail übernommen in E12-3.3.d-020.
- E12-3.3.d-033: Doppelt zu E12-3.3.d-011 und E12-3.3.d-043 (SSM braucht IGMPv3 oder SSM-Mapping).
- E12-3.3.d-044: Doppelt zu E12-3.3.d-012 (IGMP Snooping). Detail übernommen in E12-3.3.d-012.

### Ziel 4.1

- E12-4.1-002: In E12-4.1-042 und E12-4.1-043 enthalten (ping mit source, Extended Ping).
- E12-4.1-003: Doppelt zu E12-4.1-038 (Traceroute über TTL).
- E12-4.1-004: Doppelt zum Exhibit E12-4.1-041 (Stern an einem Hop).
- E12-4.1-007: Doppelt zu E12-4.1-046 (undebug all).
- E12-4.1-015: In E12-4.1-014 enthalten (authPriv = Verschlüsselung).
- E12-4.1-027: Doppelt zu E12-4.1-001 (andere Absenderadresse, andere Rückroute). Detail übernommen in E12-4.1-001.
- E12-4.1-032: In E12-4.1-058 bis E12-4.1-061 einzeln enthalten (SNMPv3 View, Gruppe, Benutzer, Traps). Detail übernommen in E12-4.1-058.
- E12-4.1-045: Doppelt zu E12-4.1-021 (terminal monitor).
- E12-4.1-047: Doppelt zu E12-4.1-024 (debug condition interface).
- E12-4.1-052: In E12-4.1-031 enthalten (logging buffered). Detail übernommen in E12-4.1-031.
- E12-4.1-056: In E12-4.1-031 enthalten (logging console warnings). Detail übernommen in E12-4.1-031.

### Ziel 4.2

- E12-4.2-004: In E12-4.2-025 und E12-4.2-002 enthalten (Flow Record mit match/collect).
- E12-4.2-006: Doppelt zu E12-4.2-027 (Record und Exporter im Monitor).
- E12-4.2-007: Doppelt zu E12-4.2-028 (ip flow monitor input).
- E12-4.2-008: Doppelt zu E12-4.2-029 (show flow monitor cache / exporter).
- E12-4.2-010: Doppelt zu E12-4.2-017 (Template fehlt beim Collector). Detail übernommen in E12-4.2-017.
- E12-4.2-014: In E12-4.2-025 enthalten (5-Tupel als match-Felder).
- E12-4.2-015: In E12-4.2-003 und E12-4.2-018 enthalten (fehlendes match-Feld fasst Flows zusammen).

### Ziel 4.3

- E12-4.3-004: Doppelt zu E12-4.3-029 (show monitor session).
- E12-4.3-005: Doppelt zu E12-4.3-016 (überlasteter Zielport).
- E12-4.3-006: Doppelt zu E12-4.3-018 (Zielport leitet keinen normalen Verkehr).
- E12-4.3-010: In E12-4.3-019 enthalten (RSPAN-VLAN auf allen Switches und Trunks).
- E12-4.3-012: In E12-4.3-017 enthalten (ERSPAN, Routing und MTU). Detail übernommen in E12-4.3-017.
- E12-4.3-023: Doppelt zu E12-4.3-002 (lokaler SPAN).
- E12-4.3-025: Doppelt zu E12-4.3-021 (filter vlan). Detail übernommen in E12-4.3-021.
- E12-4.3-026: Doppelt zu E12-4.3-007 (remote-span VLAN).
- E12-4.3-027: In E12-4.3-008 und E12-4.3-009 enthalten (RSPAN Quelle und Ziel).
- E12-4.3-028: Doppelt zu E12-4.3-013 (ERSPAN-Quellsession). Detail übernommen in E12-4.3-013.

### Ziel 4.4

- E12-4.4-016: Doppelt zu E12-4.4-008 (Messung hängt an der Route, die sie steuert). Detail übernommen in E12-4.4-008.
- E12-4.4-023: Doppelt zu E12-4.4-002 (ICMP-Messung alle 10 Sekunden).
- E12-4.4-024: In E12-4.4-002 und E12-4.4-003 enthalten (ip sla schedule).
- E12-4.4-027: Doppelt zu E12-4.4-004 und E12-4.4-005 (show ip sla statistics / configuration). Detail übernommen in E12-4.4-004.
- E12-4.4-028: Doppelt zu E12-4.4-006 und E12-4.4-007 (Track und getrackte Route). Detail übernommen in E12-4.4-007.
- E12-4.4-029: Doppelt zu E12-4.4-019 (delay down/up).

### Ziel 4.5

- E12-4.5-008: In E12-4.5-007 enthalten (Abweichung vom gelernten Normalverhalten).

### Ziel 4.6

- E12-4.6-003: In E12-4.6-002 enthalten (RESTCONF Port 443).
- E12-4.6-004: Doppelt zu E12-4.6-041 (netconf-yang). Detail übernommen in E12-4.6-041.
- E12-4.6-010: Doppelt zu E12-4.6-029 (commit fehlt nach Candidate-Änderung). Detail übernommen in E12-4.6-029.
- E12-4.6-022: In E12-4.6-021 enthalten (source running).
- E12-4.6-023: In E12-4.6-034b enthalten (DELETE).
- E12-4.6-042: Doppelt zu E12-4.6-005 (restconf, ip http secure-server, ip http authentication local). Detail übernommen in E12-4.6-005.

### Ziel 5.1.a

- E12-5.1.a-002: In E12-5.1.a-029 enthalten (lokaler Benutzer mit secret und Privilege 15).
- E12-5.1.a-004: In E12-5.1.a-030 enthalten (transport input ssh, login local). Detail übernommen in E12-5.1.a-030.
- E12-5.1.a-007: In E12-5.1.a-030 enthalten (access-class an den VTYs).
- E12-5.1.a-010: Doppelt zu E12-5.1.a-036 (show ip ssh, show users).
- E12-5.1.a-017: In E12-5.1.a-033 enthalten (login block-for).
- E12-5.1.a-031: Doppelt zu E12-5.1.a-005 (SSH vorbereiten). Detail übernommen in E12-5.1.a-005.
- E12-5.1.a-032: Doppelt zu E12-5.1.a-008 (exec-timeout 5 0).
- E12-5.1.a-035: Doppelt zu E12-5.1.a-018 (privilege exec level).

### Ziel 5.1.b

- E12-5.1.b-003: Doppelt zu E12-5.1.b-043 (aaa new-model).
- E12-5.1.b-020: Doppelt zu E12-5.1.b-002 (Anmeldung ok, Autorisierung nicht). Detail übernommen in E12-5.1.b-002.
- E12-5.1.b-044: Doppelt zu E12-5.1.b-011 (TACACS+-Server und Servergruppe).
- E12-5.1.b-045: Doppelt zu E12-5.1.b-016 (RADIUS-Server mit Ports und Key).
- E12-5.1.b-047: Doppelt zu E12-5.1.b-012 (EXEC-Autorisierung per TACACS+).
- E12-5.1.b-048: In E12-5.1.b-019 enthalten (Befehlsautorisierung Level 15). Detail übernommen in E12-5.1.b-019.
- E12-5.1.b-049: Doppelt zu E12-5.1.b-013 (Accounting für Level-15-Befehle).
- E12-5.1.b-051: Doppelt zu E12-5.1.b-028 (ip tacacs/radius source-interface). Detail übernommen in E12-5.1.b-028.
- E12-5.1.b-052: Doppelt zu E12-5.1.b-029 (test aaa group).

### Ziel 5.2.a

- E12-5.2.a-012: Doppelt zu E12-5.2.a-003 (erster Treffer entscheidet).
- E12-5.2.a-017: In E12-5.2.a-032 und E12-5.2.a-042 enthalten (established prüft nur ACK/RST).
- E12-5.2.a-048: Doppelt zu E12-5.2.a-019 und E12-5.2.a-024 (zeitbasierte ACL).
- E12-5.2.a-056: Doppelt zu E12-5.2.a-026 und E12-5.2.a-027 (IPv6-ACL mit traffic-filter). Detail übernommen in E12-5.2.a-027.
- E12-5.2.a-058: Doppelt zu E12-5.2.a-019 und E12-5.2.a-024 (zeitbasierte ACL).
- E12-5.2.a-061: Doppelt zu E12-5.2.a-015 (show access-lists, show ip interface). Detail übernommen in E12-5.2.a-015.

### Ziel 5.2.b

- E12-5.2.b-005: In E12-5.2.b-022 enthalten (CoPP-Klasse per ACL und class-map).
- E12-5.2.b-009: Doppelt zu E12-5.2.b-025 (show policy-map control-plane).
- E12-5.2.b-012: Doppelt zu E12-5.2.b-010 (CoPP wirkt nicht auf Transitverkehr).
- E12-5.2.b-014: Doppelt zu E12-5.2.b-008 (deny in CoPP-ACL heißt nur: nicht diese Klasse). Detail übernommen in E12-5.2.b-008.
- E12-5.2.b-023: Doppelt zu E12-5.2.b-006 (police in der CoPP-Klasse). Detail übernommen in E12-5.2.b-006.
- E12-5.2.b-024: Doppelt zu E12-5.2.b-004 (service-policy input unter control-plane). Detail übernommen in E12-5.2.b-004.

### Ziel 5.3

- E12-5.3-002: Doppelt zu E12-5.3-009 (HTTPS ohne Zertifikatsprüfung).
- E12-5.3-006: In E12-5.3-010 enthalten (Least Privilege für lesende Accounts).

### Ziel 5.4.a

- E12-5.4.a-009: Doppelt zu E12-5.4.a-003 (Talos).
- E12-5.4.a-019: In E12-5.4.a-010 und E12-5.4.a-025 enthalten (Umbrella stoppt bei der DNS-Anfrage).

### Ziel 5.4.b

- E12-5.4.b-034: In E12-5.4.b-020 und E12-5.4.b-015b enthalten (host-mode multi-domain / multi-auth).
- E12-5.4.b-035: Doppelt zu E12-5.4.b-022 (authentication open). Detail übernommen in E12-5.4.b-022.
- E12-5.4.b-037: Doppelt zu E12-5.1.b-037 (aaa server radius dynamic-author). Detail übernommen in E12-5.1.b-037.

### Ziel 5.4.c

- E12-5.4.c-003: In E12-5.4.c-007 und E12-5.4.c-014 enthalten (Inhalt ohne Entschlüsselung unsichtbar). Detail übernommen in E12-5.4.c-007.
- E12-5.4.c-016: In E12-5.4.c-025 bis E12-5.4.c-028 schrittweise enthalten (ZBF-Konfiguration). Detail übernommen in E12-5.4.c-025, E12-5.4.c-028.

### Ziel 5.4.d

- E12-5.4.d-010: In E12-5.4.d-005 und E12-5.4.d-013 enthalten (SGACL und MACsec ersetzen sich nicht).
- E12-5.4.d-021: In E12-5.4.d-034 und E12-5.4.d-035 schrittweise enthalten (MACsec mit Pre-Shared Key).
- E12-5.4.d-029: Doppelt zu E12-5.4.d-026 (cts role-based enforcement). Detail übernommen in E12-5.4.d-026.

### Ziel 6.2

- E12-6.2-016: In E12-6.2-013 enthalten (verschachteltes Objekt mit null und Array).

### Ziel 6.4

- E12-6.4-003: In E12-6.4-018 enthalten (Token-Endpunkt).
- E12-6.4-004: In E12-6.4-018 und E12-5.3-019 enthalten (X-Auth-Token).
- E12-6.4-008: In E12-6.4-021 enthalten (JSESSIONID und XSRF-Token).
- E12-6.4-010: In E12-6.4-013 und E12-6.4-016 enthalten (Task-ID heißt nur angenommen).
- E12-6.4-011: Doppelt zu E12-6.4-014 (Pagination).

### Ziel 6.5

- E12-6.5-006: Doppelt zu E12-5.3-003 (401 vs. 403).
- E12-6.5-011: In E12-6.5-017 enthalten (200 mit isError:true).

### Ziel 6.6

- E12-6.6-009: In E12-6.6-015 enthalten (Labels werden als Text sortiert).
- E12-6.6-011: Doppelt zu E12-6.6-035 (show event manager policy registered / history).
- E12-6.6-018: Doppelt zu E12-6.6-010 (Rückkopplungsschleife).
- E12-6.6-028: Doppelt zu E12-6.6-005 (event syslog pattern).
- E12-6.6-029: In E12-6.6-014 enthalten (Konfigurationsbefehle per cli command).
- E12-6.6-031: In E12-6.6-002 und E12-6.6-022 enthalten (watchdog und cron).
- E12-6.6-033: Doppelt zu E12-6.6-023 (event track state down).
- E12-6.6-034: Doppelt zu E12-6.6-003 und E12-6.6-004 (event none, event manager run).

### Ziel 6.7

- E12-6.7-004: In E12-6.7-003 enthalten (agentenlos heißt: Dienste wie SSH müssen laufen). Detail übernommen in E12-6.7-003.
