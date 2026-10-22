LAB = dict(
    slug="C1-BGP-AS-Pfad-und-Backup", num="C1", title="BGP: allowas-in, private AS, GTSM und bedingte Ankündigung",
    minutes=120, level="schwer",
    summary=("Ein Unternehmen mit dem privaten AS 65001 hängt mit Zentrale (HQ) und Filiale (BR) am Provider ISP1, die Zentrale "
             "zusätzlich an ISP2 als Backup. Weil beide Standorte denselben AS nutzen, verwirft die Filiale die Routen der Zentrale. "
             "Du löst das mit `allowas-in`, entfernst den privaten AS beim Provider, schützt eine Sitzung mit GTSM und kündigst das "
             "Netz der Zentrale bei ISP2 nur an, wenn ISP1 ausfällt."),
    goals=["Erklären, warum ein eBGP-Router Routen mit dem eigenen AS im Pfad verwirft, und das mit `allowas-in` gezielt lösen.",
           "Private AS-Nummern beim Provider mit `remove-private-as` entfernen und das im AS-Pfad nachweisen.",
           "Eine Backup-Ankündigung mit `advertise-map` und `non-exist-map` bauen und den Umschwenk messen.",
           "Eine eBGP-Sitzung mit GTSM (`ttl-security`) schützen und erklären, warum beide Seiten es brauchen."],
    tags=[("1.5.c", "BGP: Policies, Communities und Anbindungsdesigns", 6), ("1.5.d", "BGP: AS-Path-Manipulation", 5),
          ("1.5.f", "BGP: Soft Reconfiguration, Route Refresh und Schutz", 4)],
    diagram="""
   BR  AS 65001                            NET  AS 64600
   Lo1 203.0.113.1/24                      Lo1 192.0.2.1/24
        | Gi0/0                      Gi0/0 /          \\ Gi0/1
        |                                 /            \\
        | Gi0/1                    Gi0/2 /              \\ Gi0/1
   ISP1  AS 64501 ----------------------+          ISP2  AS 64502
        | Gi0/0                                          | Gi0/0
        |                                                |
        | Gi0/0                                          | Gi0/1
        +------------------- HQ  AS 65001 ---------------+
                             Lo1 198.51.100.1/24
""",
    nets=[("HQ Gi0/0 – ISP1 Gi0/0", "10.0.11.0/30 (ISP1 .1, HQ .2)"),
          ("HQ Gi0/1 – ISP2 Gi0/0", "10.0.12.0/30 (ISP2 .1, HQ .2)"),
          ("BR Gi0/0 – ISP1 Gi0/1", "10.0.21.0/30 (ISP1 .1, BR .2)"),
          ("ISP1 Gi0/2 – NET Gi0/0", "10.0.31.0/30 (ISP1 .1, NET .2)"),
          ("ISP2 Gi0/1 – NET Gi0/1", "10.0.32.0/30 (ISP2 .1, NET .2)"),
          ("Netze der Standorte (Loopback1)", "HQ 198.51.100.0/24, BR 203.0.113.0/24, NET 192.0.2.0/24")],
    topo_text=("HQ und BR gehören zum selben Unternehmen und nutzen denselben privaten AS 65001, haben aber keine direkte "
               "Verbindung: Ihr Verkehr läuft über ISP1. NET steht für das Internet. ISP1 ist der Hauptprovider der Zentrale, "
               "ISP2 nur Backup. Ausgehend soll HQ ISP1 bevorzugen. Eingehend soll ISP2 das Netz 198.51.100.0/24 nur kennen, "
               "wenn ISP1 ausgefallen ist. Als Merker dafür schickt ISP1 der Zentrale eine Default-Route: Solange sie da ist, "
               "steht die Verbindung zu ISP1."),
    steps=[
        dict(t="eBGP-Sitzungen aufbauen.",
             body="Konfiguriere die Sitzungen laut Skizze: HQ (`router bgp 65001`) zu ISP1 und ISP2, BR (`router bgp 65001`) zu ISP1, "
                  "ISP1 (`router bgp 64501`) zu HQ, BR und NET, ISP2 (`router bgp 64502`) zu HQ und NET, NET (`router bgp 64600`) "
                  "zu ISP1 und ISP2. Setze überall eine `bgp router-id` und kündige mit `network` die Loopback1-Netze von HQ, BR und NET an.",
             check="`show ip bgp summary` zeigt auf ISP1 drei, auf ISP2 und NET je zwei Nachbarn mit einer Präfixzahl statt Active oder Idle. "
                   "NET kennt 198.51.100.0/24 und 203.0.113.0/24.",
             think="BR hat eine Sitzung zu ISP1, und ISP1 kennt 198.51.100.0/24. Warum steht das Netz trotzdem nicht in `show ip bgp` auf BR?"),
        dict(t="Eigenen AS im Pfad zulassen.",
             body="Auf BR `neighbor 10.0.21.1 allowas-in 1`, auf HQ `neighbor 10.0.11.1 allowas-in 1`.",
             check="BR hat 198.51.100.0/24 mit dem AS-Pfad `64501 65001`, HQ hat 203.0.113.0/24 über ISP1. "
                   "`ping 198.51.100.1 source Loopback1` auf BR klappt.",
             think="Was zählt die Zahl hinter `allowas-in`, und welches Risiko gehst du damit ein?"),
        dict(t="Privaten AS beim Provider entfernen.",
             body="Auf ISP1 `neighbor 10.0.31.2 remove-private-as`, auf ISP2 `neighbor 10.0.32.2 remove-private-as`. "
                  "Danach auf ISP1 und ISP2 `clear ip bgp * soft out`.",
             check="`show ip bgp 198.51.100.0` auf NET zeigt die Pfade `64501` und `64502`, beide ohne 65001.",
             think="Warum entfernt ISP1 den privaten AS nur in Richtung NET und nicht auch in Richtung BR?"),
        dict(t="Ausgehend ISP1 bevorzugen und Transit verhindern.",
             body="Auf HQ: `route-map LP-ISP1 permit 10` mit `set local-preference 200`, als `neighbor 10.0.11.1 route-map LP-ISP1 in`. "
                  "Dazu ein Ausgangsfilter zu beiden Providern: `ip prefix-list OWN seq 5 permit 198.51.100.0/24` und "
                  "`neighbor … prefix-list OWN out`. Danach `clear ip bgp * soft`.",
             check="`show ip bgp 192.0.2.0` auf HQ: bester Pfad über 10.0.11.1 mit LocPrf 200.",
             think="Warum braucht HQ den Ausgangsfilter, obwohl es nur ein eigenes Netz hat?"),
        dict(t="Default-Route von ISP1 als Merker.",
             body="Auf ISP1 `neighbor 10.0.11.2 default-originate`.",
             check="HQ hat 0.0.0.0/0 nur von ISP1 (`show ip bgp 0.0.0.0`).",
             think="Warum darf ISP2 der Zentrale keine Default-Route schicken, wenn sie als Merker für ISP1 dienen soll?"),
        dict(t="Backup nur bei Ausfall ankündigen.",
             body="Auf HQ: `ip prefix-list DEFAULT seq 5 permit 0.0.0.0/0`, `route-map ISP1-DEFAULT permit 10` mit "
                  "`match ip address prefix-list DEFAULT` und `route-map ADV-BACKUP permit 10` mit `match ip address prefix-list OWN`. "
                  "Dann `neighbor 10.0.12.1 advertise-map ADV-BACKUP non-exist-map ISP1-DEFAULT`.",
             check="`show ip bgp neighbors 10.0.12.1 | include Condition` zeigt den Status *Withdraw*. "
                   "ISP2 hat 198.51.100.0/24 nicht mehr von HQ, NET kennt das Netz nur über ISP1.",
             think="Warum dauert es nach einem Ausfall bis zu einer Minute, bis die Backup-Route erscheint?"),
        dict(t="Ausfall testen.",
             body="Auf HQ unter `interface GigabitEthernet0/0` `shutdown`. Warte bis zu 60 Sekunden.",
             check="Der Status springt auf *Advertise*, NET erreicht 198.51.100.1 über ISP2 "
                   "(`traceroute 198.51.100.1 source Loopback1` auf NET). Danach `no shutdown`, der Status geht zurück auf *Withdraw*.",
             think="Wie kommt der Verkehr von BR zur Zentrale, solange der Link HQ–ISP1 ausgefallen ist?"),
        dict(t="GTSM zu ISP2.",
             body="Auf HQ `neighbor 10.0.12.1 ttl-security hops 1`, auf ISP2 `neighbor 10.0.12.2 ttl-security hops 1`.",
             check="Die Sitzung baut sich nach dem Reset wieder auf. `show ip bgp neighbors 10.0.12.1` auf HQ nennt eine minimale "
                   "eingehende TTL von 254.",
             think="Was passiert, wenn nur eine Seite `ttl-security` konfiguriert?")],
    answers=[
        ("1", "**Weil der eigene AS 65001 schon im AS-Pfad steht.** Das ist der Schleifenschutz von eBGP: BR sieht `64501 65001` "
              "und verwirft die Route beim Empfang. ISP1 schickt sie trotzdem, entschieden wird beim Empfänger. "
              "`show ip bgp neighbors 10.0.21.1` auf BR führt solche Präfixe bei den abgelehnten als AS-Pfad-Schleife."),
        ("2", "**Wie oft der eigene AS im Pfad stehen darf, hier einmal.** Das Risiko: Der Schleifenschutz ist für diesen Nachbarn "
              "teilweise aus. Kommt eine eigene Route über einen Umweg zurück, in dem 65001 nur einmal steht, nimmt BR sie an. "
              "Deshalb so klein wie möglich und nur bei den Nachbarn, die es brauchen."),
        ("3", "**Weil der private AS nur das Internet nicht erreichen soll, im Provider-Netz aber gebraucht wird.** Gegenüber BR ist "
              "65001 ein gültiger Kunden-AS. Würde ISP1 ihn auch dort entfernen, bräuchte BR zwar kein `allowas-in` mehr, verlöre aber "
              "den Schleifenschutz für diese Routen. Ohne `all` entfernt `remove-private-as` private AS übrigens nur, wenn der Pfad "
              "ausschließlich aus privaten AS besteht."),
        ("4", "**Damit HQ kein Transit-AS wird.** Ohne Filter würde HQ die Routen von ISP1 an ISP2 weitergeben und umgekehrt, dazu "
              "das Netz der Filiale. Fällt beim Provider ein Link aus, liefe fremder Verkehr über die Zentrale. Der Filter lässt nur "
              "198.51.100.0/24 hinaus."),
        ("5", "**Weil die Bedingung genau dann greifen soll, wenn die Verbindung zu ISP1 fehlt.** Bekäme HQ auch von ISP2 eine "
              "Default-Route, stünde 0.0.0.0/0 nach einem Ausfall von ISP1 weiter in der BGP-Tabelle, und die Backup-Ankündigung "
              "würde nie ausgelöst."),
        ("6", "**Weil der BGP-Scanner die Bedingungen nur periodisch prüft, standardmäßig alle 60 Sekunden.** Schneller wird der "
              "Umschwenk nicht über die Bedingung, sondern über die Erkennung des Ausfalls selbst: Ein Link-Down beendet die eBGP-Sitzung "
              "sofort (Fast External Fallover), bei einem Ausfall hinter einem Switch helfen BFD oder kürzere Timer."),
        ("7", "**Über ISP1, NET und ISP2.** BR hat 198.51.100.0/24 jetzt mit dem Pfad `64501 64600 64502`: ISP1 lernt das Netz von NET, "
              "und den privaten AS 65001 hat ISP2 entfernt. Weil 65001 nicht mehr im Pfad steht, bräuchte BR dafür nicht einmal "
              "`allowas-in`."),
        ("8", "**Die Sitzung kommt nicht zustande.** Die Seite mit `ttl-security hops 1` erwartet Pakete mit einer TTL von mindestens "
              "254, die andere sendet eBGP standardmäßig mit TTL 1. Die Pakete werden verworfen, bevor BGP sie sieht. GTSM gehört deshalb "
              "immer auf beide Seiten, und es schließt `ebgp-multihop` für denselben Nachbarn aus.")],
    nodes=[
        dict(name="HQ", type="router", x=400, y=450,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.11.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.12.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 198.51.100.1 255.255.255.0""",
             sol="""
ip prefix-list DEFAULT seq 5 permit 0.0.0.0/0
ip prefix-list OWN seq 5 permit 198.51.100.0/24
route-map LP-ISP1 permit 10
 set local-preference 200
route-map ADV-BACKUP permit 10
 match ip address prefix-list OWN
route-map ISP1-DEFAULT permit 10
 match ip address prefix-list DEFAULT
router bgp 65001
 bgp router-id 10.255.0.1
 bgp log-neighbor-changes
 network 198.51.100.0 mask 255.255.255.0
 neighbor 10.0.11.1 remote-as 64501
 neighbor 10.0.11.1 allowas-in 1
 neighbor 10.0.11.1 prefix-list OWN out
 neighbor 10.0.11.1 route-map LP-ISP1 in
 neighbor 10.0.12.1 remote-as 64502
 neighbor 10.0.12.1 ttl-security hops 1
 neighbor 10.0.12.1 advertise-map ADV-BACKUP non-exist-map ISP1-DEFAULT
 neighbor 10.0.12.1 prefix-list OWN out"""),
        dict(name="ISP1", type="router", x=150, y=280,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.11.1 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.21.1 255.255.255.252
 no shutdown
interface GigabitEthernet0/2
 ip address 10.0.31.1 255.255.255.252
 no shutdown""",
             sol="""
router bgp 64501
 bgp router-id 10.255.0.11
 bgp log-neighbor-changes
 neighbor 10.0.11.2 remote-as 65001
 neighbor 10.0.11.2 default-originate
 neighbor 10.0.21.2 remote-as 65001
 neighbor 10.0.31.2 remote-as 64600
 neighbor 10.0.31.2 remove-private-as"""),
        dict(name="ISP2", type="router", x=650, y=280,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.12.1 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.32.1 255.255.255.252
 no shutdown""",
             sol="""
router bgp 64502
 bgp router-id 10.255.0.12
 bgp log-neighbor-changes
 neighbor 10.0.12.2 remote-as 65001
 neighbor 10.0.12.2 ttl-security hops 1
 neighbor 10.0.32.2 remote-as 64600
 neighbor 10.0.32.2 remove-private-as"""),
        dict(name="BR", type="router", x=150, y=80,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.21.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 203.0.113.1 255.255.255.0""",
             sol="""
router bgp 65001
 bgp router-id 10.255.0.2
 bgp log-neighbor-changes
 network 203.0.113.0 mask 255.255.255.0
 neighbor 10.0.21.1 remote-as 64501
 neighbor 10.0.21.1 allowas-in 1"""),
        dict(name="NET", type="router", x=500, y=80,
             base="""
interface GigabitEthernet0/0
 ip address 10.0.31.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 10.0.32.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 192.0.2.1 255.255.255.0""",
             sol="""
router bgp 64600
 bgp router-id 10.255.0.100
 bgp log-neighbor-changes
 network 192.0.2.0 mask 255.255.255.0
 neighbor 10.0.31.1 remote-as 64501
 neighbor 10.0.32.1 remote-as 64502""")],
    links=[("HQ", "Gi0/0", "ISP1", "Gi0/0"), ("HQ", "Gi0/1", "ISP2", "Gi0/0"), ("BR", "Gi0/0", "ISP1", "Gi0/1"),
           ("ISP1", "Gi0/2", "NET", "Gi0/0"), ("ISP2", "Gi0/1", "NET", "Gi0/1")],
    staggered=True,
    tickets=["BR erreicht das Netz der Zentrale nicht: `ping 198.51.100.1 source Loopback1` scheitert, und `show ip bgp` auf BR "
             "enthält 198.51.100.0/24 nicht, obwohl ISP1 das Netz kennt.",
             "Die BGP-Sitzung zwischen HQ und ISP2 bleibt down, obwohl `ping 10.0.12.1` von HQ klappt.",
             "Der Internet-Router NET sieht 198.51.100.0/24 und 203.0.113.0/24 mit dem privaten AS 65001 im Pfad.",
             "ISP2 bekommt 198.51.100.0/24 von HQ, obwohl ISP1 läuft. NET hat das Netz von beiden Providern in der BGP-Tabelle.",
             "Ausfalltest: Nach `shutdown` auf HQ Gi0/0 erreicht NET das Netz 198.51.100.0/24 auch nach zwei Minuten nicht. "
             "ISP2 bekommt die Backup-Route nie."],
    faults=[
        dict(node="BR", old=" neighbor 10.0.21.1 allowas-in 1", new=None,
             find="Auf ISP1 zeigt `show ip bgp 198.51.100.0` das Netz mit dem Pfad `65001`, an BR geht es also als `64501 65001`. "
                  "`show ip bgp neighbors 10.0.21.1` auf BR zählt abgelehnte Präfixe wegen AS-Pfad-Schleife. In der BGP-Konfiguration "
                  "von BR fehlt `allowas-in`.",
             cause="Ohne `allowas-in` verwirft BR jede Route, in deren AS-Pfad der eigene AS 65001 steht. Das ist der normale "
                   "eBGP-Schleifenschutz, hier aber unerwünscht, weil beide Standorte denselben AS nutzen.",
             fix="`neighbor 10.0.21.1 allowas-in 1` unter `router bgp 65001` auf BR."),
        dict(node="ISP2", old=" neighbor 10.0.12.2 ttl-security hops 1", new=None,
             find="`show ip bgp summary` auf HQ zeigt 10.0.12.1 in *Idle* oder *Active*. `show ip bgp neighbors 10.0.12.1` auf HQ nennt "
                  "GTSM mit einer minimalen eingehenden TTL von 254. Auf ISP2 fehlt `ttl-security` für 10.0.12.2.",
             cause="GTSM nur auf einer Seite: HQ erwartet eine TTL von mindestens 254, ISP2 sendet eBGP-Pakete mit TTL 1. "
                   "HQ verwirft sie, bevor BGP sie sieht.",
             fix="`neighbor 10.0.12.2 ttl-security hops 1` unter `router bgp 64502` auf ISP2."),
        dict(node="ISP1", old=" neighbor 10.0.31.2 remove-private-as", new=None,
             find="`show ip bgp` auf NET: Pfad `64501 65001`. In der Konfiguration von ISP1 fehlt für 10.0.31.2 die Zeile "
                  "`remove-private-as`, ISP2 hat sie für seinen Nachbarn NET.",
             cause="ISP1 gibt den AS-Pfad unverändert an NET weiter. Private AS-Nummern (64512 bis 65534) gehören nicht ins Internet.",
             fix="`neighbor 10.0.31.2 remove-private-as` auf ISP1, danach `clear ip bgp 10.0.31.2 soft out`."),
        dict(node="ISP1", old=" neighbor 10.0.11.2 default-originate", new=None,
             find="`show ip bgp 0.0.0.0` auf HQ: keine Default-Route. Damit ist die Non-Exist-Bedingung erfüllt, "
                  "`show ip bgp neighbors 10.0.12.1 | include Condition` zeigt *Advertise*. Auf ISP1 fehlt `default-originate` "
                  "für 10.0.11.2.",
             cause="Die Default-Route von ISP1 ist der Merker für die Bedingung. Fehlt sie, hält HQ ISP1 für ausgefallen und "
                   "kündigt das Netz dauerhaft bei ISP2 an.",
             fix="`neighbor 10.0.11.2 default-originate` unter `router bgp 64501` auf ISP1."),
        dict(node="HQ", old="ip prefix-list DEFAULT seq 5 permit 0.0.0.0/0", new="ip prefix-list DEFAULT seq 5 permit 0.0.0.0/0 le 32",
             find="`show ip bgp neighbors 10.0.12.1 | include Condition` auf HQ bleibt auch nach dem Ausfall bei *Withdraw*. "
                  "`show ip prefix-list DEFAULT` zeigt `0.0.0.0/0 le 32`: Die Liste passt auf jede Route, auch auf 192.0.2.0/24 "
                  "von ISP2.",
             cause="Mit `le 32` beschreibt die Prefix-Liste nicht mehr nur die Default-Route, sondern alle Präfixe. Die Bedingung "
                   "gilt als erfüllt, solange irgendeine passende Route existiert, und von ISP2 kommen weiter Routen. Die "
                   "Backup-Ankündigung wird deshalb nie ausgelöst.",
             fix="`no ip prefix-list DEFAULT seq 5` und `ip prefix-list DEFAULT seq 5 permit 0.0.0.0/0` auf HQ.")],
    verify=["show ip bgp summary", "show ip bgp", "show ip bgp 198.51.100.0", "show ip bgp neighbors 10.0.12.1 | include Condition|TTL",
            "ping 198.51.100.1 source Loopback1          ! auf BR und NET",
            "traceroute 198.51.100.1 source Loopback1    ! auf NET, auch beim Ausfalltest"],
    verify_table=[("`show ip bgp 198.51.100.0` auf BR", "Pfad `64501 65001`, gültig und best"),
                  ("`show ip bgp 198.51.100.0` auf NET", "ein Pfad über ISP1 mit AS-Pfad `64501`, ohne 65001"),
                  ("`show ip bgp 192.0.2.0` auf HQ", "bester Pfad über 10.0.11.1 mit LocPrf 200"),
                  ("`show ip bgp neighbors 10.0.12.1` auf HQ", "Condition-Map mit Status Withdraw, GTSM mit minimaler TTL 254"),
                  ("Ausfalltest (`shutdown` auf HQ Gi0/0)", "nach höchstens 60 s Status Advertise, NET erreicht 198.51.100.1 über ISP2")],
    caveat=("Die bedingte Ankündigung reagiert erst mit der nächsten Runde des BGP-Scanners. Warte beim Ausfalltest bis zu "
            "60 Sekunden, bevor du einen Fehler vermutest."),
    teilc=[("Zwei Standorte im selben AS sollen sich über einen Provider erreichen. Welche drei Lösungen gibt es, und wo werden sie konfiguriert?",
            "**`allowas-in` beim Kunden, `as-override` beim Provider oder eine Default-Route statt der Kundenrouten.** `allowas-in` "
            "lässt den eigenen AS im Pfad zu. Mit `as-override` ersetzt der Provider-Router den Kunden-AS durch seinen eigenen, "
            "typisch im MPLS-L3VPN. Mit einer Default-Route braucht der Standort die Routen des anderen gar nicht. Die ersten beiden "
            "schwächen den Schleifenschutz, bei mehrfach angebundenen Standorten gehört Site of Origin (SoO) dazu."),
           ("Ein Router soll nach einer Firmenübernahme vorübergehend unter dem alten AS 65002 mit einem Provider sprechen, intern aber AS 65001 sein. Wie löst du das?",
            "**Mit `neighbor … local-as 65002`, meist mit `no-prepend replace-as`.** Der Router meldet sich beim Nachbarn als 65002. "
            "`no-prepend` verhindert, dass 65002 in empfangene Routen eingefügt wird, `replace-as` ersetzt in gesendeten Routen den "
            "echten AS durch 65002. Mit `dual-as` akzeptiert der Router beide AS-Nummern, so kann der Provider in Ruhe umstellen."),
           ("HQ könnte das Netz bei ISP2 auch dauerhaft mit `as-path prepend` ankündigen. Was ist der Unterschied zur bedingten Ankündigung?",
            "**Prepending macht ISP2 nur unattraktiver, die bedingte Ankündigung versteckt den Weg ganz.** Mit Prepending sieht das "
            "Internet beide Wege. Provider, die Kundenrouten per Local Preference bevorzugen, schicken trotzdem über ISP2. Dafür schwenkt "
            "der Verkehr nach einem Ausfall sofort um. Die bedingte Ankündigung garantiert, dass ISP2 nur im Fehlerfall Verkehr bekommt, "
            "braucht dafür aber bis zu einer Scanner-Runde."),
           ("Was unterscheidet `remove-private-as` von `remove-private-as all replace-as`?",
            "**Ohne Zusatz entfernt IOS private AS nur, wenn der Pfad ausschließlich aus privaten AS besteht.** `all` entfernt sie auch "
            "aus gemischten Pfaden, `replace-as` ersetzt sie durch den eigenen AS, damit die Pfadlänge für die Best-Path-Wahl erhalten bleibt.")],
    exam=["Schleifenschutz in eBGP: Steht der eigene AS im Pfad, wird die Route verworfen. Lösungen: `allowas-in` (Kunde), `as-override` (Provider).",
          "`remove-private-as [all] [replace-as]` entfernt private AS (64512 bis 65534) vor der Weitergabe ins Internet.",
          "Bedingte Ankündigung: `neighbor … advertise-map A non-exist-map B` (oder `exist-map`), geprüft vom BGP-Scanner, standardmäßig alle 60 s.",
          "GTSM: `ttl-security hops n` auf beiden Seiten, schließt `ebgp-multihop` aus.",
          "Local Preference wirkt nur im eigenen AS und wird auf eingehende Routen gesetzt (`route-map … in`)."],
)
