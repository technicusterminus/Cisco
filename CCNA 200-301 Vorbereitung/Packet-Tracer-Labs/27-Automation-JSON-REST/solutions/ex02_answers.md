# Antworten Aufgabe 2

1. Create = POST, Read = GET, Update = PUT (ersetzt die ganze Ressource) oder PATCH (ändert Teile), Delete = DELETE.
2. GET Liste 200, GET einzeln 200, POST 201 (Created, `Location: /api/v1/vlans/30`), PUT 200, PATCH 200, DELETE 204 (kein Inhalt). `Location` nennt die URL der neu angelegten Ressource.
3. 401: Anmeldung fehlt/ungültig (nicht authentisiert). 403: authentisiert, aber nicht berechtigt (Read-only-Schlüssel schreibt). 404: Ressource existiert nicht. 409: Konflikt (VLAN existiert schon). 415: nicht unterstützter Content-Type. 400: fehlerhafte Anfrage (id ausserhalb 1–4094, ungültiges JSON).
4. Basic (Benutzer:Passwort Base64, nur über HTTPS), Bearer-/Token (z. B. OAuth 2.0: Token im `Authorization: Bearer …`), API-Key (fester Schlüssel im Header). Die Mock-API nutzt API-Key und zusätzlich Basic. Ohne TLS lesen Dritte Zugangsdaten und Daten mit.
5. Query-Parameter filtern/steuern die Abfrage (`?name=USERS`). Pagination: `?offset=1&limit=50` oder Seitenlinks, damit grosse Listen in Stücken kommen.
6. Idempotent: mehrfache identische Aufrufe führen zum selben Zustand. GET, PUT, DELETE (und HEAD, OPTIONS) sind es, POST in der Regel nicht (jeder Aufruf kann eine neue Ressource anlegen), PATCH nicht garantiert.
7. JSON (am verbreitetsten bei REST), XML (NETCONF, ältere APIs), YAML (Konfigurationsdateien, Ansible). `Content-Type` beschreibt das gesendete Format, `Accept` das gewünschte Antwortformat.
