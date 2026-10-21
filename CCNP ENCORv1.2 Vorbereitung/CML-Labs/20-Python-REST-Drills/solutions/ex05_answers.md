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

1. `interfaces` und `statistics` sind **container**, `interface` ist eine **list** (Schlüssel `name`), `name`, `description`, `enabled`, `mode`, `access-vlan`, `in-octets`, `out-octets` sind **leaf**, `allowed-vlans` ist ein **leaf-list**. `config false` markiert Zustandsdaten (nur lesbar, nicht Teil der Konfiguration).
2. `mode` ist Pflicht (`mandatory true`), der Schlüssel `name` ebenfalls. `enabled` hat den Default `true`. Fehlt `mode`, meldet NETCONF `missing-element` (rpc-error), RESTCONF antwortet mit `400 Bad Request`.
3. ```json
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
4. ```json
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
5. Ungültig sind: (a) die `when`-Bedingung `../mode = 'trunk'` ist nicht erfüllt, (b) 5000 liegt außerhalb `1..4094`, (c) der Schlüssel `name` fehlt, (d) `statistics` ist `config false` und schreibgeschützt.
6. `GET /restconf/data/lab-interfaces:interfaces/interface=GigabitEthernet0%2F1`: Der Schrägstrich im Schlüsselwert wird als `%2F` kodiert.
7. Datenknoten sind Daten (lesen/schreiben), ein RPC ist eine Operation mit Ein-/Ausgabe. RESTCONF: `POST /restconf/operations/lab-interfaces:clear-counters` mit Body
```json
{
  "lab-interfaces:input": {
    "interface-name": "GigabitEthernet0/1"
  }
}
```
8. YANG beschreibt Struktur, Typen und Regeln der Daten. Transport leisten NETCONF (SSH/830) oder RESTCONF (HTTPS). Beispiele: Standard `ietf-interfaces`, Hersteller `Cisco-IOS-XE-native`, OpenConfig `openconfig-interfaces`.
