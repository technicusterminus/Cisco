# Antworten Aufgabe 3

1. Inventory = Liste der Zielgeräte/Gruppen; Playbook = YAML-Datei mit Plays; Play = Zuordnung Hosts → Tasks; Task = ein Modulaufruf; Modul = Code, der die Aufgabe ausführt (`cisco.ios.ios_config`); Handler = Task, der nur bei `notify` läuft; Variable = Parameter (`{{ var }}`).
2. Ansible verbindet sich von einem Kontrollknoten per SSH/NETCONF/API und braucht keine Software auf dem Zielgerät. Puppet/Chef arbeiten mit einem Agenten, der den Sollzustand beim Master abholt (Pull). Netzwerkgeräte können meist keinen Agenten ausführen, daher passt agentenlos.
3. Idempotent: Mehrfachausführung ergibt denselben Zustand. `ios_config` vergleicht `lines` mit der laufenden Konfiguration und ändert nur Abweichungen; beim zweiten Lauf meldet Ansible `ok` statt `changed`.
4. Fehler: `hosts` fehlt, `connection: local` statt `ansible.netcommon.network_cli`, `gather_facts` nicht abgeschaltet, Modul `ios_config` nicht voll qualifiziert, `lines` kein Listenformat, `parents` kein Listenformat, Handler `speichern` fehlt. Lösung: `solutions/ex03_playbook_fixed.yml`.
5. Deklarativ: Du beschreibst den gewünschten Zielzustand, das Werkzeug berechnet die Schritte (Terraform, teils Ansible-Module). Imperativ: Du beschreibst jeden Schritt (Skripte).
6. `provider` = Plug-in zur Plattform (AWS), `resource` = zu verwaltendes Objekt (VPC, Subnetz), `variable` = Eingabeparameter, `output` = Ausgabewert nach dem Lauf.
7. `init` lädt Provider, `plan` zeigt die Änderungen gegenüber dem Ist-Zustand, `apply` führt sie aus, `destroy` baut alles ab. Die State-Datei speichert, welche reale Ressource zu welchem Code-Objekt gehört (Abgleich Ist/Soll).
8. IaC macht Infrastruktur reproduzierbar, versionierbar (Git), prüfbar (Reviews, Tests) und dokumentiert den Zustand im Code.
9. Ansible: Konfiguration und Betrieb bestehender Geräte (agentenlos, Push, Playbooks). Terraform: Bereitstellung/Lebenszyklus von Infrastruktur, besonders Cloud, mit Zustandsverwaltung; beide ergänzen sich (Terraform erstellt, Ansible konfiguriert).
