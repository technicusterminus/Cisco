# Aufgabe 2 – REST-API: CRUD, HTTP-Verben, Statuscodes, Authentisierung (Ziel 6.5)

Starte die Mock-API: `python3 ../mock_api/server.py 8080` (zweites Terminal). Schlüssel `lab-key-123` (lesen + schreiben), `lab-ro-key` (nur lesen).

**Teil A – Erkunden mit curl**

```
curl -i -H "X-API-Key: lab-key-123" http://127.0.0.1:8080/api/v1/vlans
curl -i -H "X-API-Key: lab-key-123" http://127.0.0.1:8080/api/v1/vlans/10
curl -i -H "X-API-Key: lab-key-123" -H "Content-Type: application/json" -X POST -d '{"id": 30, "name": "VOICE"}' http://127.0.0.1:8080/api/v1/vlans
curl -i -H "X-API-Key: lab-key-123" -H "Content-Type: application/json" -X PUT -d '{"name": "GUESTS"}' http://127.0.0.1:8080/api/v1/vlans/30
curl -i -H "X-API-Key: lab-key-123" -H "Content-Type: application/json" -X PATCH -d '{"name": "VOICE2"}' http://127.0.0.1:8080/api/v1/vlans/30
curl -i -H "X-API-Key: lab-key-123" -X DELETE http://127.0.0.1:8080/api/v1/vlans/30
```

1. Ordne die HTTP-Verben den CRUD-Operationen zu (Create, Read, Update, Delete). Welcher Verb ersetzt eine Ressource vollständig (PUT), welcher ändert Teile (PATCH)?
2. Welche Statuscodes liefern die sechs Aufrufe (200, 201, 204, …)? Wozu dient der Header `Location`?
3. Provoziere und erkläre: **401** (Schlüssel weglassen), **403** (`lab-ro-key` + POST), **404** (VLAN 999), **409** (VLAN 10 erneut anlegen), **415** (POST ohne `Content-Type`), **400** (`{"id": 5000, "name": "X"}`).
4. Welche **Authentisierungsarten** gibt es (Basic, Bearer-Token/OAuth, API-Key)? Welche nutzt die Mock-API (zusätzlich Basic-Auth: `curl -u admin:'Lab#2026!' …`)? Warum nie über HTTP im Klartext?
5. Wozu dienen Query-Parameter (`?name=USERS`) und wie sähe eine Pagination aus?
6. Was bedeutet *idempotent*? Welche Verben sind idempotent (GET, PUT, DELETE), welche nicht (POST)?
7. Welche Datenformate sind verbreitet (JSON, XML, YAML) und wie trägt der Header `Accept`/`Content-Type` das?

**Teil B – Python-Client:** Implementiere `rest_client.py` so, dass `python3 -m unittest -v test_ex02` grün wird (die Tests starten die Mock-API selbst).
