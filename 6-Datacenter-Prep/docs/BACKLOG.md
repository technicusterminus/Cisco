# Backlog (priorisiert)

Alle Punkte sind offen. Erledigt ist, was in `docs/GAP-ANALYSE.md` als „behoben“ steht.

## Phase 2: Lernplattform

| # | Punkt | Begründung | Umfang |
|---|---|---|---|

## Phase 3: Troubleshooting

| # | Punkt | Begründung |
|---|---|---|

## Phase 4: Erweiterungen

| # | Punkt |
|---|---|
| B-16 | Rest der Contract-Prioritäten: Wirkung von `priorityOverride` (level1–level3 ↔ lowest/medium/highest belegen); Rule Expansion für Inter-VRF vzAny-to-ESG. Table 8 (inkl. ESG- und Inter-VRF-vzAny 10/11, shsrc_any_any_deny 12) und 23 des Contract Guide, Deny+Log und implizites DHCP sind umgesetzt |
| B-17 | Fault-Codes gegen die Fault Reference prüfen. Belegt ist F0467 (Texte und Format nach Cisco TechNote 220876 umgesetzt); alle übrigen Faults tragen S-Codes (simulator-spezifisch). Eine Websuche (Nov. 2026) fand für keinen Kandidaten (z. B. F0523, F0956, F2534) eine Cisco-Quelle, nur Forenbeiträge. Der Test-Fault heißt jetzt S9100 statt F9999 |
| B-18 | Access SPAN. Belegt (Cisco-DevNet-Ansible-Collection, Module `aci_access_span_*` samt Integrationstests): `uni/infra/srcgrp-{name}` (spanSrcGrp, `adminSt`), darunter `spanlbl-{Zielgruppe}` (spanSpanLbl), `src-{name}` (spanSrc, `dir` in/out/both, `spanOnDrop`) mit `rssrcToPathEp-[{Pfad}]` (spanRsSrcToPathEp); `uni/infra/destgrp-{name}` (spanDestGrp) mit spanDest und spanRsDestPathEp bzw. spanRsDestEpg (`ip`, `srcIpPrefix`, `ver`, `mtu`, `ttl`, `flowId`, `dscp`). Offen: die RNs von spanDest, spanRsDestPathEp und spanRsDestEpg, Ausgabeformat von `show monitor session` und Betriebszustand. Erst umsetzen, wenn das belegt ist (z. B. per APIC Management Information Model Reference) |
| B-19 | Static Endpoint (Menüpunkt in der EPG, weiter ohne Funktion). Die Klasse `fvStCEp`, ihre DN-Form und die Relation zum Pfad sind nicht belegt; gefunden wurden nur die Typen silent-host, tep, vep in einem Cisco-Community-Beitrag. Dazu PBR: `thresholdDownAction` bypass, Schwellen bei mehreren Zielen, belegter RN von `vnsRsRedirectHealthGroup` |

## Technik

Keine offenen Punkte. Lint (`ruff`), Typprüfung (`mypy`), Aufteilung der Engine und der GUI-Testrunner sind umgesetzt.
