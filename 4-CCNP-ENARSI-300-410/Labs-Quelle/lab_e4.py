LAB = dict(
    slug="E4-uRPF", num="E4", title="Unicast Reverse Path Forwarding: Strict, Loose, ACL", minutes=75, level="mittel",
    summary=("Ein Provider-Edge-Router (PE) schützt sich mit uRPF vor gefälschten Absenderadressen: Strict Mode zum Kunden, "
             "Loose Mode zum Internet, eine Ausnahme-ACL für einen Altbestand. Du siehst, was ein Default-Route im Loose Mode "
             "bewirkt und warum Strict Mode bei asymmetrischem Routing Verkehr verwirft."),
    goals=["uRPF im Strict Mode (`rx`) und Loose Mode (`any`) konfigurieren und die Wirkung testen.",
           "Erklären, wann ein Paket den uRPF-Check besteht und welche Rolle `allow-default` spielt.",
           "Eine Ausnahme-ACL für Pakete einsetzen, die den Check nicht bestehen.",
           "Mit `show ip interface` und `show access-lists` nachweisen, ob uRPF Pakete verwirft."],
    tags=[("3.2.c", "uRPF: Fehlersuche", 10)],
    diagram="""
   CE ───Gi0/0── PE ──Gi0/1─── NET (Internet)
   Lo1 203.0.113.1/24 (Kunde)   Lo9 10.200.0.1/24 (anderer Kunde)   Lo1 192.0.2.88/32
   Lo2 10.200.0.77/24 (fremde Adresse)                              Lo2 10.99.99.1/24 (Bogon)
   Lo3 10.77.0.1/24 (Altbestand)
   Lo4 10.66.66.1/24 (unbekannt)
""",
    nets=[("CE Gi0/0 – PE Gi0/0", "198.51.100.0/30 (PE .1, CE .2)"),
          ("PE Gi0/1 – NET Gi0/0", "192.0.2.0/30 (PE .1, NET .2)")],
    topo_text=("Der Kunde (CE) besitzt 203.0.113.0/24. Die anderen Loopbacks auf CE stehen für Absenderadressen, die er **nicht** verwenden darf: "
               "10.200.0.77 liegt im Netz eines anderen Kunden (PE hat dafür eine Route über Lo9), 10.66.66.1 ist dem PE ganz unbekannt, "
               "10.77.0.1 ist ein Altbestand, der ausnahmsweise erlaubt sein soll. Der PE hat eine Default-Route zum Internet und, wie im Internet üblich, eine spezifische Route zu 192.0.2.88/32. "
               "Zum Prüfen schickst du Pings mit `source` und liest die Zähler am PE ab; Antworten brauchst du nicht."),
    steps=[
        dict(t="Ausgangslage prüfen.", body="Alle Routen sind gesetzt. Auf CE: `ping 192.0.2.88 source Loopback1`.",
             check="Der Ping geht durch. Das ist der legitime Kundenverkehr, er muss auch nach dem Einschalten von uRPF funktionieren.",
             think="Warum kommt die Antwort von NET zurück? Welche Routen braucht NET dafür?"),
        dict(t="Strict Mode zum Kunden.", body="Auf PE unter Gi0/0: `ip verify unicast source reachable-via rx`. Sende dann auf CE `ping 192.0.2.88 source Loopback2` (fremde Adresse) und `ping 192.0.2.88 source Loopback1` (legitim).",
             check="`show ip interface Gi0/0` auf dem PE nennt „IP verify source reachable-via RX“ und zählt die Verwürfe (`verification drops`) für Loopback2 hoch. Der Ping von Loopback1 geht weiter durch.",
             think="Warum besteht 10.200.0.77 den Check nicht, obwohl der PE eine Route zu 10.200.0.0/24 hat?"),
        dict(t="Loose Mode zum Internet.", body="Auf PE unter Gi0/1: `ip verify unicast source reachable-via any`. Sende auf NET `ping 203.0.113.1 source Loopback2` (Absender 10.99.99.1, im PE unbekannt).",
             check="Das Paket kommt nicht an, der Zähler an Gi0/1 des PE steigt.",
             think="Der PE hat eine Default-Route, die auf jede Adresse passt. Warum wird das Paket trotzdem verworfen?"),
        dict(t="`allow-default` einordnen.", body="Das Schlüsselwort `allow-default` ergänzt du hier nicht, du denkst nur darüber nach.",
             think="Was würde `reachable-via any allow-default` am PE ändern, und wann ist das sinnvoll?"),
        dict(t="Ausnahme-ACL.", body="Sende auf CE `ping 192.0.2.88 source Loopback3` (10.77.0.1). Lege dann auf dem PE `access-list 120 permit ip 10.77.0.0 0.0.0.255 any` an und ändere Gi0/0 auf `ip verify unicast source reachable-via rx 120`.",
             check="Vor der ACL steigt der Verwurfs-Zähler an Gi0/0, nachher zählt `show access-lists 120` Treffer und das Paket wird weitergeleitet.",
             think="Wann wird die ACL ausgewertet: vor oder nach dem uRPF-Check?"),
        dict(t="Grenzen von Strict Mode.", body="Dieses Lab hat nur einen Uplink je Kunde.",
             think="Was passiert mit Strict Mode, wenn der Kunde zwei Uplinks an zwei PEs hat und das Routing asymmetrisch ist? Was ist die Voraussetzung dafür, dass uRPF überhaupt funktioniert?")],
    answers=[
        ("1", "NET braucht eine Route zum Kundennetz 203.0.113.0/24 (statisch über den PE). Ohne sie käme die Antwort nicht zurück. Für den uRPF-Test selbst ist die Antwort egal, es geht um das Verwerfen am PE."),
        ("2", "Im Strict Mode muss die Route zur Absenderadresse **über genau das Interface** führen, an dem das Paket ankommt. Die Route zu 10.200.0.0/24 zeigt auf Lo9, nicht auf Gi0/0. Das Paket besteht den Check nicht."),
        ("3", "Im Loose Mode muss die Absenderadresse nur **irgendwo in der FIB** vorkommen. Die Default-Route zählt dabei nicht mit, solange `allow-default` fehlt. Das Paket mit 10.99.99.1 hat keine spezifischere Route und fällt durch."),
        ("4", "Mit `allow-default` zählt auch die Default-Route als gültiger Rückweg. Bei einem Router mit Default-Route besteht dann jede Absenderadresse den Loose-Check, der Schutz entfällt. Sinnvoll ist `allow-default` nur dort, wo die Default-Route wirklich der einzige legitime Rückweg ist, zum Beispiel an einem Stub-Kunden (und dort im Strict Mode)."),
        ("5", "Die ACL wird **nur für Pakete ausgewertet, die den uRPF-Check nicht bestehen**. Erlaubt sie das Paket, wird es weitergeleitet, verbietet sie es, wird es verworfen. Pakete, die den Check bestehen, kommen an der ACL gar nicht vorbei."),
        ("6", "Bei Asymmetrie verwirft Strict Mode legitimen Verkehr, weil die Rückroute über einen anderen Uplink führt als der Weg des Pakets. Dort nimmt man Loose Mode oder eine ACL. Voraussetzung für uRPF ist **CEF**: Der Check schaut in die FIB, nicht in die Routing-Tabelle.")],
    nodes=[
        dict(name="CE", type="router", x=100, y=150,
             base="""
interface GigabitEthernet0/0
 ip address 198.51.100.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 203.0.113.1 255.255.255.0
interface Loopback2
 ip address 10.200.0.77 255.255.255.0
interface Loopback3
 ip address 10.77.0.1 255.255.255.0
interface Loopback4
 ip address 10.66.66.1 255.255.255.0
ip route 0.0.0.0 0.0.0.0 198.51.100.1""", sol=""),
        dict(name="PE", type="router", x=350, y=150,
             base="""
interface GigabitEthernet0/0
 ip address 198.51.100.1 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 ip address 192.0.2.1 255.255.255.252
 no shutdown
interface Loopback9
 ip address 10.200.0.1 255.255.255.0
ip route 0.0.0.0 0.0.0.0 192.0.2.2
ip route 192.0.2.88 255.255.255.255 192.0.2.2
ip route 203.0.113.0 255.255.255.0 198.51.100.2""",
             sol="""
ip cef
access-list 120 permit ip 10.77.0.0 0.0.0.255 any
interface GigabitEthernet0/0
 ip verify unicast source reachable-via rx 120
interface GigabitEthernet0/1
 ip verify unicast source reachable-via any"""),
        dict(name="NET", type="router", x=600, y=150,
             base="""
interface GigabitEthernet0/0
 ip address 192.0.2.2 255.255.255.252
 no shutdown
interface Loopback1
 ip address 192.0.2.88 255.255.255.255
interface Loopback2
 ip address 10.99.99.1 255.255.255.0
ip route 203.0.113.0 255.255.255.0 192.0.2.1
ip route 0.0.0.0 0.0.0.0 192.0.2.1""", sol="")],
    links=[("CE", "Gi0/0", "PE", "Gi0/0"), ("PE", "Gi0/1", "NET", "Gi0/0")],
    tickets=["Ein Test mit gefälschter Absenderadresse (`ping 192.0.2.88 source Loopback2` auf CE) kommt durch; die Verwurfs-Zähler an PE Gi0/0 bleiben bei 0.",
             "Pakete aus dem Internet mit Absender 10.99.99.1 (`ping 203.0.113.1 source Loopback2` auf NET) erreichen den Kunden, obwohl Loose Mode eingeschaltet ist.",
             "Der Altbestand 10.77.0.1 wird verworfen, obwohl die Ausnahme-ACL dafür existiert; `show access-lists 120` zählt keine Treffer.",
             "Der legitime Kundenverkehr (`ping 192.0.2.88 source Loopback1` auf CE) kommt nicht mehr durch; der Zähler der Verwürfe an PE Gi0/0 steigt mit jedem Ping."],
    faults=[
        dict(node="PE", old=" ip verify unicast source reachable-via rx 120", new=" ip verify unicast source reachable-via any 120",
             find="`show ip interface Gi0/0` nennt „IP verify source reachable-via ANY, ACL 120“ statt RX.",
             cause="Am Kundenport steht Loose statt Strict. Die Absenderadresse 10.200.0.77 liegt in einem Netz, das der PE kennt (Lo9), also besteht sie den Loose-Check.",
             fix="`ip verify unicast source reachable-via rx 120` unter Gi0/0."),
        dict(node="PE", old=" ip verify unicast source reachable-via any", new=" ip verify unicast source reachable-via any allow-default",
             find="`show ip interface Gi0/1` zeigt „allow default“ in der uRPF-Zeile. `show ip route 0.0.0.0` bestätigt die Default-Route.",
             cause="Mit `allow-default` zählt die Default-Route als gültiger Rückweg. Jeder Absender hat damit einen „Weg“ und besteht den Loose-Check.",
             fix="`ip verify unicast source reachable-via any` ohne `allow-default` unter Gi0/1."),
        dict(node="PE", old="access-list 120 permit ip 10.77.0.0 0.0.0.255 any", new="access-list 120 permit ip 10.77.1.0 0.0.0.255 any",
             find="`show access-lists 120` zeigt das Netz 10.77.1.0 statt 10.77.0.0 und keine Treffer.",
             cause="Die Ausnahme-ACL passt auf das falsche Netz. Der Altbestand 10.77.0.1 fällt durch den Strict-Check und trifft auf kein permit.",
             fix="`access-list 120 permit ip 10.77.0.0 0.0.0.255 any`."),
        dict(node="PE", old="ip route 203.0.113.0 255.255.255.0 198.51.100.2", new="ip route 203.0.131.0 255.255.255.0 198.51.100.2",
             find="`show ip route 203.0.113.1` auf dem PE liefert nur die Default-Route zu NET. `show ip route static` zeigt 203.0.131.0/24 (Zahlendreher).",
             cause="Das Kundennetz fehlt im PE (Route zeigt auf 203.0.131.0/24). Die Absenderadresse 203.0.113.1 hat keine Route über Gi0/0, der Strict-Check schlägt fehl und die ACL erlaubt sie nicht.",
             fix="`ip route 203.0.113.0 255.255.255.0 198.51.100.2`.")],
    verify=["show ip interface GigabitEthernet0/0 | include verify|drops", "show ip interface GigabitEthernet0/1 | include verify|drops",
            "show access-lists 120", "show ip route 203.0.113.1", "show cef interface GigabitEthernet0/0 | include RPF",
            "ping 192.0.2.88 source Loopback1     ! auf CE, muss durchgehen"],
    verify_table=[("`show ip interface Gi0/0` auf dem PE", "„IP verify source reachable-via RX, ACL 120“ und steigende Verwurfs-Zähler bei Loopback2/Loopback4"),
                  ("`show ip interface Gi0/1` auf dem PE", "„reachable-via ANY“ ohne „allow default“"),
                  ("Ping von CE mit Loopback1 / Loopback3", "geht durch (Loopback3 über die ACL)"),
                  ("Ping von CE mit Loopback2 / Loopback4", "wird am PE verworfen")],
    caveat=("uRPF braucht CEF und wird hier mit den Zählern am Interface geprüft. Die genaue Ausgabe von `show ip interface` (Zeilen zu "
            "`verification drops`) unterscheidet sich je nach IOS-Version leicht. Der Ablauf ist nicht in einer laufenden Simulation getestet."),
    teilc=[("Ein Kunde ist an zwei Provider-Routern angeschlossen (Multihoming). Strict Mode verwirft legitimen Verkehr. Warum, und was änderst du?",
            "**Weil die beste Route zum Kundennetz über den anderen Uplink führt.** Das Paket kommt am zweiten PE an, dessen beste Rückroute zeigt aber über ein anderes Interface (oder einen anderen PE). Lösung: Loose Mode (`any`), oder Strict Mode mit Ausnahme-ACL, oder das Routing so gestalten, dass der Hin- und der Rückweg über denselben Uplink laufen."),
           ("Was ändert sich im Loose Mode, wenn der Router eine Default-Route hat und `allow-default` fehlt?",
            "**Nichts am Schutz.** Die Default-Route zählt ohne `allow-default` nicht als Rückroute. Nur Absender mit einer spezifischeren Route (oder einer Verbindung) bestehen den Check. Mit `allow-default` ginge jedes Paket durch."),
           ("Warum hilft uRPF nicht gegen gefälschte Absender aus dem eigenen Kundennetz?",
            "**Weil der Check nur die Route zur Absenderadresse prüft.** Fälscht ein Kunde eine andere Adresse aus *seinem* eigenen Präfix, besteht das Paket den Check. Dagegen helfen Rate-Limits und Filter auf Anwendungsebene, nicht uRPF.")],
    exam=["Strict (`rx`): Rückroute muss über das Eingangs-Interface führen. Loose (`any`): Absender muss in der FIB stehen.",
          "`allow-default`: die Default-Route zählt als gültiger Rückweg. Ohne das Schlüsselwort fällt ein Absender ohne spezifische Route durch.",
          "ACL am Ende des Befehls: nur für Pakete, die den Check nicht bestehen, permit leitet sie weiter, deny verwirft sie.",
          "uRPF braucht CEF und wirkt am Eingang (ingress). Typischer Einsatz: Strict zum Kunden, Loose im Transit.",
          "Strict + asymmetrisches Routing = verworfener Verkehr; das ist die häufigste Fehlerursache."],
)
