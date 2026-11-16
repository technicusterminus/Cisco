# Quelle der ENCOR-Labs 32 bis 36 und Live-Test

Die Labs 01 bis 31 liegen nur als fertige Dateien vor. Ab Lab 32 entsteht jedes Lab aus einer Definition (`lab_NN.py`): Topologie, Aufgabentexte, Musterlösung und die Fehler für Teil B stehen an einer Stelle. Daraus werden die CML- und die EVE-NG-Fassung erzeugt, sie können also nicht auseinanderlaufen.

| Datei | Zweck |
|---|---|
| `lab_32.py` … `lab_36.py` | Lab-Definitionen |
| `lablib.py` | erzeugt YAML, READMEs, Konfigurationen und Fehlerlisten, prüft Links, Adressen und Fehler |
| `build_labs.py` | schreibt alle Labs nach `../CML-Labs` und `../EVE-NG-Labs` |
| `live_test.py` | spielt die Labs in einer laufenden CML- oder EVE-NG-Instanz durch |
| `update_ticket_trainer.py` | trägt die Tickets der Labs 32 bis 36 in `../Trainer/ticket-trainer.html` ein |
| `update_simulation.py` | trägt die 26 Fragen zu den Themen der Labs 32 bis 36 in die Prüfungssimulation ein |
| `test_live.py` | prüft den Telnet-Zugang des Live-Tests gegen eine nachgebaute Konsole |

## Labs neu erzeugen

```bash
pip install pyyaml
python3 Labs-Quelle/build_labs.py
python3 EVE-NG-Labs/tools/build_eve_import.py --paket ENCOR
```

Beide Befehle aus dem Ordner `3-CCNP-ENCOR-350-401` starten. Die Übersichtstabellen in den READMEs und `ZIELE.md` sind von Hand gepflegt.

## Live-Test: Labs in einer laufenden Instanz sicherstellen

Die Prüfung per Skript beweist, dass Dateien, Kabel und Adressen stimmen. Sie beweist nicht, dass ein IOS-Image jede Zeile annimmt und dass ein eingebauter Fehler wirklich das Symptom aus dem Ticket erzeugt. Dafür ist der Live-Test da. Je Lab läuft er so ab:

1. **Musterlösung einspielen** und jede Konfigurationszeile auf eine Ablehnung durch den Parser prüfen.
2. **Gesunden Zustand prüfen:** die Befehle aus `checks` der Lab-Definition, jeweils gegen ein erwartetes Muster.
3. **Jeden Fehler einzeln einbauen** (`inject`): Die zugehörige Probe muss fehlschlagen. Dann **zurücknehmen** (`revert`): Die Probe muss wieder passen. So ist für jedes Ticket belegt, dass der Fehler wirkt und der Fix aus `FAULTS.md` ihn behebt.

Am Ende steht `live-test-bericht.md` mit jeder Abweichung samt Befehl, Muster und echter Geräteausgabe.

### CML

```bash
pip install virl2_client "pyats[full]"
export CML_PASSWORD='…'
python3 Labs-Quelle/live_test.py cml https://<CML-Adresse> --user <Benutzer> --insecure
```

Das Skript importiert `topology.yaml`, startet das Lab, testet und löscht es wieder (`--keep` lässt es stehen). `--lab 32 36` beschränkt auf einzelne Labs. `--insecure` nur bei selbstsigniertem Zertifikat. Ein Durchlauf aller fünf Labs dauert rund eine Stunde, der größte Teil ist Wartezeit auf Protokoll-Timer.

### EVE-NG

```bash
python3 Labs-Quelle/live_test.py eve <EVE-Adresse> --lab 36 --ports R1=32769 R2=32770
```

Vorher das Lab *Bauen* aus `EVE-Import.zip` öffnen und alle Nodes starten. Die Telnet-Ports zeigt EVE-NG je Node an. Hier wird ein Lab pro Aufruf getestet.

### Syntaxprüfung für alle Labs, auch 01 bis 31

Für die älteren Labs gibt es keine maschinenlesbaren Proben je Ticket. Prüfen lässt sich aber, ob das Image jede Konfigurationszeile annimmt. Mit `--syntax` spielt das Skript je Lab die vollständige Reparatur-Konfiguration aller Geräte ein (Basis, Lösung und eingebaute Fehler) und meldet jede abgelehnte Zeile:

```bash
python3 Labs-Quelle/live_test.py cml https://<CML-Adresse> --user <Benutzer> --insecure --syntax
```

```bash
python3 Labs-Quelle/live_test.py eve <EVE-Adresse> --syntax --lab 05 --ports SW1=32769 SW2=32770
```

Das belegt nicht, dass ein Ticket das beschriebene Symptom zeigt. Es findet aber die häufigste Ursache für ein Lab, das „hakt“: einen Befehl, den die Image-Version nicht kennt. Die Labs 15, 16 und 19 brauchen besondere Images (LISP, NX-OSv 9000, CSR1000v).

### Ohne Geräte

```bash
python3 Labs-Quelle/live_test.py selftest
python3 Labs-Quelle/test_live.py
```

Das prüft nur den Ablauf des Skripts und den Telnet-Zugang, nicht die Labs.

### Stand

Der Live-Test ist gegen einen Platzhalter und eine nachgebaute Konsole geprüft. **Gegen ein echtes CML oder EVE-NG ist er noch nicht gelaufen**, weil in der Entstehungsumgebung keine Instanz und keine Cisco-Images zur Verfügung standen. Rechne beim ersten Lauf mit zwei Arten von Meldungen:

- **Parser:** Das Image lehnt eine Zeile ab. Dann ist die Lab-Definition zu korrigieren.
- **Prüfung oder Ticket:** Die Ausgabe sieht anders aus als das Muster erwartet, oder ein Timer braucht länger als `settle`. Der Bericht zeigt die Ausgabe. Meist ist dann das Muster oder die Wartezeit anzupassen, nicht das Lab.

Ein Issue mit dem Bericht im Anhang genügt, um beides zu beheben.
