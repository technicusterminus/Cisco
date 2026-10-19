# Aufgabe 3 – Konfigurationsmanagement: Ansible und Terraform (Ziel 6.6)

**Teil A – Ansible lesen und reparieren**

1. Was sind **Inventory**, **Playbook**, **Play**, **Task**, **Modul**, **Handler**, **Variable**? Zeige jedes in `playbook_broken.yml`.
2. Warum ist Ansible **agentenlos** (SSH/NETCONF/API), und was unterscheidet das von Puppet/Chef (Agent, Pull-Modell)?
3. Was heisst **idempotent** bei `ios_config`? Was passiert beim zweiten Lauf, wenn die Zeilen schon vorhanden sind?
4. **Reparatur:** `playbook_broken.yml` hat Fehler. Behebe sie, bis `python3 check_playbook.py` „OK“ meldet.

**Teil B – Terraform lesen** (`main.tf`, nur lesen, keine Installation nötig)

5. Was bedeutet *deklarativ* (Zielzustand beschreiben) gegenüber *imperativ* (Schritte beschreiben)?
6. Wofür stehen `provider`, `resource`, `variable`, `output` in `main.tf`?
7. Was machen `terraform init`, `plan`, `apply`, `destroy`? Wozu dient die **State-Datei**?
8. Was bedeutet *Infrastructure as Code* für Review, Versionierung (Git) und Wiederholbarkeit?
9. Vergleiche: Wann Ansible (Konfiguration vorhandener Geräte/Server, Push), wann Terraform (Bereitstellung von Infrastruktur, Cloud, Zustandsverwaltung)?
