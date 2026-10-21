# Antworten Aufgabe 5

Baum laut `pyang -f tree`:

```
module: lab-interfaces
  +--rw interfaces
     +--rw interface* [name]
        +--rw name             string
        +--rw description?     string
        +--rw enabled?         boolean
        +--rw mode             enumeration
        +--rw access-vlan?     vlan-id
        +--rw allowed-vlans*   vlan-id
        +--ro statistics
           +--ro in-octets?    uint64
           +--ro out-octets?   uint64

  rpcs:
    +---x clear-counters
       +---w input
       |  +---w interface-name    string
       +--ro output
          +--ro cleared?   boolean
```

1. **Container: `interfaces`, `statistics`. List: `interface` mit Schlüssel `name`. Leaf-List: `allowed-vlans`. Alles andere sind Leafs.** Ein Container gruppiert nur, eine List hat beliebig viele Einträge, die der Schlüssel unterscheidet. Ein Leaf hält genau einen Wert, eine Leaf-List mehrere Werte desselben Typs. `config false` markiert Zustandsdaten: Du kannst sie lesen, aber nicht konfigurieren. Im Baum erkennst du sie an `ro`.
2. **Pflicht sind `mode` und der Schlüssel `name`, einen Default hat nur `enabled` (`true`).** Ein Schlüssel ist immer Pflicht, `mode` hat `mandatory true`. Fehlt `mode`, lehnt das Gerät die Änderung ab: NETCONF antwortet mit einem `rpc-error` vom Typ `missing-element`, RESTCONF mit `400 Bad Request`.
3. **Ein Listeneintrag mit Modulpräfix, `mode` und `access-vlan`.** `description` ist optional, `enabled` darf fehlen, weil es den Default `true` hat.

```json
{
  "lab-interfaces:interface": [
    {
      "name": "GigabitEthernet0/1",
      "description": "H1",
      "mode": "access",
      "access-vlan": 10
    }
  ]
}
```
4. **`mode` auf `trunk`, die VLANs als JSON-Array.** Eine Leaf-List wird in JSON zur Liste. `access-vlan` darf hier nicht stehen, weil seine `when`-Bedingung nur bei Access gilt.

```json
{
  "lab-interfaces:interface": [
    {
      "name": "GigabitEthernet0/2",
      "mode": "trunk",
      "allowed-vlans": [
        10,
        20,
        30
      ]
    }
  ]
}
```
5. **Alle vier sind ungültig.** (a) `allowed-vlans` gilt nur bei `when "../mode = 'trunk'"`, an einem Access-Port darf der Knoten nicht stehen. (b) Der Typ `vlan-id` erlaubt nur `1..4094`. (c) Ohne den Schlüssel `name` lässt sich der Listeneintrag nicht identifizieren. (d) `statistics` ist `config false`, Zustandsdaten kann `edit-config` nicht schreiben.
6. **`GET /restconf/data/lab-interfaces:interfaces/interface=GigabitEthernet0%2F1`.** Ein Listeneintrag wird mit `=Schlüsselwert` adressiert. Der Schrägstrich im Namen muss als `%2F` kodiert werden, sonst hielte RESTCONF ihn für eine neue Pfadebene.
7. **Ein Datenknoten ist ein Zustand, den du liest oder schreibst. Ein RPC ist eine Aktion mit Ein- und Ausgabe.** Einen RPC rufst du per `POST` unter `/restconf/operations/` auf, hier `POST /restconf/operations/lab-interfaces:clear-counters` mit diesem Body:
```json
{
  "lab-interfaces:input": {
    "interface-name": "GigabitEthernet0/1"
  }
}
```
8. **YANG beschreibt nur, wie die Daten aussehen. Transportiert werden sie per NETCONF oder RESTCONF.** Das Modell legt Struktur, Typen und Regeln fest, ähnlich wie ein Datenbankschema. NETCONF überträgt XML über SSH (Port 830), RESTCONF JSON oder XML über HTTPS. Beispiele: Standard `ietf-interfaces`, Hersteller `Cisco-IOS-XE-native`, OpenConfig `openconfig-interfaces`.
