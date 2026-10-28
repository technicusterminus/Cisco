"""Erzeugt die Lab-Dateien in ../labs/*.json.

Aufruf: python3 Labs-Quelle/build_labs.py
Jedes Lab: Startkonfiguration (APIC-JSON), simulierte Hosts/Router, Aufgaben,
automatische Pruefungen und Musterloesung.
"""
import json
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'labs')
L101, L102, L103, L104 = 'SAL1931LA01', 'SAL1931LA02', 'SAL1931LA03', 'SAL1931LA04'


# ----------------------------------------------------------------------------
# Bausteine
# ----------------------------------------------------------------------------

def mo(cls, attrs=None, *children):
    body = {'attributes': attrs or {}}
    if children:
        body['children'] = [c for c in children if c]
    return {cls: body}


def access(pool, vfrom, vto, dom, aaep, ipg, ifp, sel, pfrom, pto, swp, nfrom, nto, l3=False, pg_cls='infraAccPortGrp',
           pg_extra=(), extra_infra=()):
    domcls = 'l3extDomP' if l3 else 'physDomP'
    domdn = ('uni/l3dom-%s' if l3 else 'uni/phys-%s') % dom
    pgrn = ('accportgrp-%s' if pg_cls == 'infraAccPortGrp' else 'accbundle-%s') % ipg
    return mo('polUni', {},
              mo('infraInfra', {},
                 mo('fvnsVlanInstP', {'name': pool, 'allocMode': 'static'},
                    mo('fvnsEncapBlk', {'from': 'vlan-%d' % vfrom, 'to': 'vlan-%d' % vto})),
                 mo('infraAttEntityP', {'name': aaep}, mo('infraRsDomP', {'tDn': domdn})),
                 *extra_infra,
                 mo('infraFuncP', {}, mo(pg_cls, dict({'name': ipg}, **({'lagT': 'node'} if pg_cls == 'infraAccBndlGrp' else {})),
                                         mo('infraRsAttEntP', {'tDn': 'uni/infra/attentp-%s' % aaep}), *pg_extra)),
                 mo('infraAccPortP', {'name': ifp},
                    mo('infraHPortS', {'name': sel, 'type': 'range'},
                       mo('infraPortBlk', {'name': 'block2', 'fromPort': str(pfrom), 'toPort': str(pto)}),
                       mo('infraRsAccBaseGrp', {'tDn': 'uni/infra/funcprof/%s' % pgrn}))),
                 mo('infraNodeP', {'name': swp},
                    mo('infraLeafS', {'name': '%d-%d' % (nfrom, nto), 'type': 'range'},
                       mo('infraNodeBlk', {'name': 'blk', 'from_': str(nfrom), 'to_': str(nto)})),
                    mo('infraRsAccPortP', {'tDn': 'uni/infra/accportprof-%s' % ifp}))),
              mo(domcls, {'name': dom}, mo('infraRsVlanNs', {'tDn': 'uni/infra/vlanns-[%s]-static' % pool})))


def bd(name, vrf, subnet=None, scope='private', l3out=None, **kw):
    a = {'name': name}
    a.update(kw)
    return mo('fvBD', a, mo('fvRsCtx', {'tnFvCtxName': vrf}),
              mo('fvSubnet', {'ip': subnet, 'scope': scope}) if subnet else None,
              mo('fvRsBDToOut', {'tnL3extOutName': l3out}) if l3out else None)


def path(node, port):
    return 'topology/pod-1/paths-%d/pathep-[%s]' % (node, port)


def epg(name, bdname, dom='uni/phys-PhysDom-Server', ports=(), prov=(), cons=()):
    kids = [mo('fvRsBd', {'tnFvBDName': bdname})]
    if dom:
        kids.append(mo('fvRsDomAtt', {'tDn': dom}))
    for tdn, vlan in ports:
        kids.append(mo('fvRsPathAtt', {'tDn': tdn, 'encap': 'vlan-%d' % vlan, 'mode': 'regular'}))
    kids += [mo('fvRsProv', {'tnVzBrCPName': c}) for c in prov]
    kids += [mo('fvRsCons', {'tnVzBrCPName': c}) for c in cons]
    return mo('fvAEPg', {'name': name}, *kids)


def filt(name, *entries):
    return mo('vzFilter', {'name': name}, *[mo('vzEntry', e) for e in entries])


def contract(name, filters, scope='context', rev='yes'):
    return mo('vzBrCP', {'name': name, 'scope': scope},
              mo('vzSubj', {'name': 'subj', 'revFltPorts': rev}, *[mo('vzRsSubjFiltAtt', {'tnVzFilterName': f}) for f in filters]))


def host(name, mac, ip, gw, vlan, links, bond='none', descr=''):
    return {'name': name, 'mac': mac, 'ip': ip, 'gw': gw, 'vlan': vlan, 'links': links, 'bond': bond, 'descr': descr}


def router(name, serial, port, ip, proto, vlan=0, mtu=1500, area='0.0.0.1', asn='65100', peer_as='65001',
           networks=('8.8.8.0/24', '1.1.1.0/24'), advertise=('0.0.0.0/0',), static_back=(), rid='172.16.255.1'):
    return {'name': name, 'serial': serial, 'port': port, 'vlan': vlan, 'ip': ip, 'mtu': mtu, 'protocol': proto,
            'routerId': rid,
            'ospf': {'area': area, 'areaType': 'regular', 'hello': 10, 'dead': 40, 'nwT': 'bcast', 'mtuIgnore': False},
            'bgp': {'asn': asn, 'peerAs': peer_as}, 'networks': list(networks), 'advertise': list(advertise),
            'staticBack': list(static_back)}


SERVER_ACCESS = access('VLAN-Pool-Server', 100, 199, 'PhysDom-Server', 'AAEP-Server', 'IPG-Server-Access',
                       'IntProf-Leaf101-102', 'Server-Ports', 1, 10, 'SwProf-Leaf101-102', 101, 102)

WEB1 = host('web1', '00:50:56:10:10:11', '10.10.10.11/24', '10.10.10.1', 110, [[L101, 'eth1/1']], descr='Webserver')
APP1 = host('app1', '00:50:56:10:20:11', '10.10.20.11/24', '10.10.20.1', 120, [[L102, 'eth1/2']], descr='Applikationsserver')
JUMP1 = host('jump1', '00:50:56:10:40:11', '10.10.40.11/24', '10.10.40.1', 140, [[L101, 'eth1/5']], descr='Jump-Host der Admins')


def shop_tenant(with_contracts=False, with_mgmt=False, web_l3out=None):
    kids = [mo('fvCtx', {'name': 'Prod'}),
            bd('BD-Web', 'Prod', '10.10.10.1/24', 'public' if web_l3out else 'private', web_l3out),
            bd('BD-App', 'Prod', '10.10.20.1/24')]
    if with_mgmt:
        kids.append(bd('BD-Mgmt', 'Prod', '10.10.40.1/24'))
    web_cons = ['web-to-app'] if with_contracts else []
    app_prov = ['web-to-app'] if with_contracts else []
    eps = [epg('Web', 'BD-Web', ports=[(path(101, 'eth1/1'), 110)], cons=web_cons),
           epg('App', 'BD-App', ports=[(path(102, 'eth1/2'), 120)], prov=app_prov)]
    if with_mgmt:
        eps.append(epg('Mgmt', 'BD-Mgmt', ports=[(path(101, 'eth1/5'), 140)]))
    kids.append(mo('fvAp', {'name': 'Webshop'}, *eps))
    if with_contracts:
        kids.append(filt('tcp-8080', {'name': 'tcp-8080', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '8080', 'dToPort': '8080'}))
        kids.append(contract('web-to-app', ['tcp-8080', 'icmp']))
    return mo('fvTenant', {'name': 'Shop'}, *kids)


def check(desc, typ, **kw):
    d = {'desc': desc, 'type': typ}
    d.update(kw)
    return d


def task(title, text, hint=None):
    t = {'title': title, 'text': text}
    if hint:
        t['hint'] = hint
    return t


LABS = []
BGP_TREE = mo('polUni', {}, mo('fabricInst', {}, mo('bgpInstPol', {'name': 'default'}, mo('bgpAsP', {'asn': '65001'}),
                                                    mo('bgpRRP', {}, mo('bgpRRNodePEp', {'id': '201'}), mo('bgpRRNodePEp', {'id': '202'})))))


def lab(**kw):
    LABS.append(kw)


# ----------------------------------------------------------------------------
# Lab 00 - Day 0: APIC-Ersteinrichtung
# ----------------------------------------------------------------------------
SETUP00 = {'fabricName': 'DC-FRA', 'fabricId': '1', 'ctrlCount': '1', 'podId': '1', 'standby': 'NO', 'ctrlId': '1',
           'ctrlName': 'apic1', 'tepPool': '10.0.0.0/16', 'infraVlan': '3967', 'gipo': '225.0.0.0/15',
           'oobIp': '192.168.10.1/24', 'oobGw': '192.168.10.254', 'speed': 'auto', 'strong': 'Y', 'pwd': 'Fabric!2026'}
lab(id='00-day0-apic-setup', title='00 Day 0: APIC-Ersteinrichtung', topic='Fabric-Inbetriebnahme', level='Einstieg',
    duration='20 min', fabric='factory',
    goals=['Den Setup-Dialog des APIC an der Konsole durchlaufen', 'Wissen, welche Werte sich später nicht mehr ändern lassen '
           '(TEP-Pool, Infra-VLAN, Fabric-Name, Pod-ID)', 'Die Werte am APIC per CLI verifizieren'],
    intro='Der APIC steht frisch ausgepackt im Rack, die Konsole (CIMC-KVM) ist offen. Nach dem Laden des Labs startet der '
          '**Setup-Dialog** – die GUI ist erst danach erreichbar.\n\n**Vorgaben aus dem Low-Level-Design:**\n'
          '- Fabric Name **DC-FRA**, Fabric ID 1, **ein** Controller, Pod 1, Controller-Name apic1\n'
          '- TEP-Pool **10.0.0.0/16**, Infra-VLAN **3967**, GIPo 225.0.0.0/15\n'
          '- OOB **192.168.10.1/24**, Gateway **192.168.10.254**\n'
          '- Admin-Passwort **Fabric!2026** (Strong Passwords an)',
    tasks=[
        task('Setup-Dialog', 'Beantworte die Fragen an der Konsole mit den Werten aus dem Design. Mit Enter übernimmst du den '
             'Vorschlag in eckigen Klammern.',
             'Achtung bei „number of active controllers“: Der Vorschlag ist 3. Mit nur einem APIC wäre der Cluster dann nie Fully Fit.'),
        task('Prüfen und anwenden', 'Lies die Zusammenfassung genau. Einmal angewendet, lassen sich TEP-Pool, Infra-VLAN und '
             'Fabric-Name nur durch Neuaufsetzen ändern (`acidiag touch clean` und `acidiag reboot`).'),
        task('Anmelden und verifizieren', 'In der GUI mit admin und dem neuen Passwort anmelden. In der APIC-CLI: '
             '`cat /data/data_admin/sam_exported.config`, `acidiag avread` und `show controller`. Unter **System > Controllers** stehen dieselben Werte.'),
        task('Erster Leaf', 'Unter **Fabric > Inventory > Fabric Membership** leaf101 (SAL1931LA01, Node 101, leaf101) und '
             'leaf102 (SAL1931LA02, Node 102, leaf102) registrieren. Auf leaf101 zeigt `show vlan extended` das Infra-VLAN zum APIC auf eth1/48.'),
    ],
    checks=[check('Fabric Name DC-FRA', 'setup', attrs={'fabricName': 'DC-FRA'}),
            check('Ein Controller im Cluster', 'setup', attrs={'ctrlCount': '1'}),
            check('TEP-Pool 10.0.0.0/16 und Infra-VLAN 3967', 'setup', attrs={'tepPool': '10.0.0.0/16', 'infraVlan': '3967'}),
            check('OOB 192.168.10.1/24 mit Gateway 192.168.10.254', 'setup', attrs={'oobIp': '192.168.10.1/24', 'oobGw': '192.168.10.254'}),
            check('leaf101 aktiv (101)', 'node', serial=L101, id=101, name='leaf101'),
            check('leaf102 aktiv (102)', 'node', serial=L102, id=102, name='leaf102')],
    solution='Setup-Antworten: Fabric name **DC-FRA**, fabric ID 1, number of active controllers **1**, POD ID 1, controller ID 1, '
             'name apic1, TEP pool 10.0.0.0/16, infra VLAN 3967, GIPo 225.0.0.0/15, OOB 192.168.10.1/24, Gateway 192.168.10.254, '
             'Strong Passwords Y, Passwort Fabric!2026. Danach im Fabric Membership die beiden Leafs registrieren.')

# ----------------------------------------------------------------------------
# Lab 01 - Fabric Discovery
# ----------------------------------------------------------------------------
lab(id='01-fabric-discovery', title='01 Fabric Discovery und BGP Route Reflector', topic='Fabric-Inbetriebnahme',
    level='Einstieg', duration='20 min', fabric='empty',
    goals=['Die Reihenfolge der Fabric Discovery verstehen (APIC-Leaf, Spines, übrige Leafs)',
           'Switches unter Fabric Membership registrieren', 'Den MP-BGP Route Reflector für die Fabric einrichten'],
    intro='Die Fabric ist frisch verkabelt, aber noch kein Switch ist registriert. Der APIC sieht per LLDP zunächst '
          'nur die Leafs, an denen er direkt hängt. Erst wenn ein Switch registriert und aktiv ist, entdeckt die '
          'Fabric dessen Nachbarn.\n\n**Ausgangslage:** 1 APIC, 2 Spines, 4 Leafs, alles unregistriert. Ein '
          'Discovery-Schritt dauert im Simulator 20 Sekunden (einstellbar unter Simulation > Einstellungen).',
    tasks=[
        task('Leafs am APIC registrieren', 'Öffne **Fabric > Inventory > Fabric Membership > Nodes Pending '
             'Registration** und registriere die Switches nach dieser Tabelle:\n'
             '- SAL1931LA01 → Node ID **101**, Name **leaf101**\n- SAL1931LA02 → Node ID **102**, Name **leaf102**',
             'Pod ID bleibt 1. Nach der Registrierung wechselt der Status auf *discovering*, dann auf *active*.'),
        task('Spines registrieren', 'Sobald leaf101 aktiv ist, erscheinen die Spines. Registriere:\n'
             '- FDO2219SP01 → **201**, **spine201**\n- FDO2219SP02 → **202**, **spine202**',
             'Die Spines erscheinen erst, wenn ein Leaf mit Uplink zu ihnen aktiv ist.'),
        task('Restliche Leafs registrieren', '- SAL1931LA03 → **103**, **leaf103**\n- SAL1931LA04 → **104**, **leaf104**'),
        task('Kontrolle per CLI', 'Öffne die CLI (oben rechts) und prüfe auf dem APIC mit `acidiag fnvread`, dass alle '
             'sechs Switches *active* sind. Schau dir mit `ssh leaf101` und `show lldp neighbors` die Nachbarn an.'),
        task('BGP Route Reflector', 'Unter **System > System Settings > BGP Route Reflector** die Fabric-AS **65001** '
             'eintragen und **spine201** und **spine202** (Node 201 und 202) als Route Reflector hinzufügen.',
             'Ohne diese Policy verteilt die Fabric keine externen Routen von L3Outs an die anderen Leafs.'),
    ],
    checks=[check('leaf101 aktiv (101)', 'node', serial=L101, id=101, name='leaf101'),
            check('leaf102 aktiv (102)', 'node', serial=L102, id=102, name='leaf102'),
            check('spine201 aktiv (201)', 'node', serial='FDO2219SP01', id=201, name='spine201'),
            check('spine202 aktiv (202)', 'node', serial='FDO2219SP02', id=202, name='spine202'),
            check('leaf103 aktiv (103)', 'node', serial=L103, id=103, name='leaf103'),
            check('leaf104 aktiv (104)', 'node', serial=L104, id=104, name='leaf104'),
            check('Fabric-AS 65001', 'exists', dn='uni/fabric/bgpInstP-default/as', attrs={'asn': '65001'}),
            check('spine201 ist Route Reflector', 'exists', dn='uni/fabric/bgpInstP-default/rr/node-201'),
            check('spine202 ist Route Reflector', 'exists', dn='uni/fabric/bgpInstP-default/rr/node-202')],
    solution='Fabric Membership: die sechs Seriennummern in der Reihenfolge leaf101/leaf102 → spine201/spine202 → '
             'leaf103/leaf104 registrieren. Per REST geht das mit `POST /api/mo/uni/controller/nodeidentpol.json` und '
             '`{"fabricNodeIdentP":{"attributes":{"serial":"SAL1931LA01","nodeId":"101","name":"leaf101"}}}`.\n\n'
             'BGP Route Reflector: `uni/fabric/bgpInstP-default/as` mit `asn=65001`, darunter `rr/node-201` und `rr/node-202`.')

# ----------------------------------------------------------------------------
# Lab 02 - Access Policies
# ----------------------------------------------------------------------------
lab(id='02-access-policies', title='02 Access Policies: vom VLAN-Pool zum Switch-Profil', topic='Access Policies',
    level='Einstieg', duration='30 min', fabric='discovered',
    goals=['Die Kette VLAN Pool → Domain → AAEP → Policy Group → Interface-Profil → Switch-Profil bauen',
           'Fault F0467 lesen und beheben', 'Endpoints in einer EPG lernen lassen'],
    intro='Der Tenant **Lab02** ist schon fertig: EPG **Server** hängt an der Physical Domain **PhysDom-Server** und hat '
          'Static Ports auf leaf101 eth1/1 und leaf102 eth1/1 mit **vlan-100**. Die Hosts **h1** und **h2** sind '
          'angeschlossen. Trotzdem lernt die Fabric keine Endpoints, und die EPG zeigt Faults – denn die Access Policies fehlen.\n\n'
          'Lege alles unter **Fabric > Access Policies** an. Achte genau auf die Namen: Die EPG verweist schon auf '
          '`PhysDom-Server`.',
    config=[mo('fvTenant', {'name': 'Lab02'}, mo('fvCtx', {'name': 'VRF1'}), bd('BD-Server', 'VRF1', '10.0.100.1/24'),
               mo('fvAp', {'name': 'AP1'}, epg('Server', 'BD-Server', ports=[(path(101, 'eth1/1'), 100), (path(102, 'eth1/1'), 100)])))],
    hosts=[host('h1', '00:50:56:02:00:01', '10.0.100.11/24', '10.0.100.1', 100, [[L101, 'eth1/1']]),
           host('h2', '00:50:56:02:00:02', '10.0.100.12/24', '10.0.100.1', 100, [[L102, 'eth1/1']])],
    tasks=[
        task('Fault ansehen', 'Öffne **Tenants > Lab02 > Application Profiles > AP1 > Application EPGs > Server** und '
             'dort den Tab **Faults**. Welcher Grund steht im Fault F0467?'),
        task('VLAN Pool', '**Pools > VLAN**: Pool **VLAN-Pool-Server**, *Static Allocation*, Encap Block vlan-100 bis vlan-199.'),
        task('Physical Domain', '**Physical and External Domains > Physical Domains**: **PhysDom-Server** mit dem VLAN Pool.'),
        task('AAEP', '**Policies > Global > Attachable Access Entity Profiles**: **AAEP-Server** mit der Domain PhysDom-Server.'),
        task('Interface Policy Group', '**Interfaces > Leaf Interfaces > Policy Groups > Leaf Access Port**: '
             '**IPG-Server-Access** mit dem AAEP.'),
        task('Interface Profile', '**Interfaces > Leaf Interfaces > Profiles**: **IntProf-Leaf101-102** mit einem Access '
             'Port Selector **Server-Ports** für die Ports 1/1-10 und der Policy Group.'),
        task('Switch Profile', '**Switches > Leaf Switches > Profiles**: **SwProf-Leaf101-102** mit Leaf Selector für die Nodes '
             '101-102 und dem Interface Profile.',
             'Das Interface Profile hängt am Switch Profile, nicht am Leaf Selector.'),
        task('Ergebnis prüfen', 'Die Faults der EPG verschwinden, unter **Operational** stehen h1 und h2. Teste unter '
             '**Operations > Visibility & Troubleshooting** einen Ping von h1 nach h2. Auf leaf101: `show vlan extended`, `show endpoint`.'),
    ],
    checks=[check('VLAN Pool VLAN-Pool-Server (static)', 'exists', dn='uni/infra/vlanns-[VLAN-Pool-Server]-static'),
            check('Physical Domain PhysDom-Server', 'exists', dn='uni/phys-PhysDom-Server'),
            check('AAEP-Server enthält PhysDom-Server', 'exists', dn='uni/infra/attentp-AAEP-Server/rsdomP-[uni/phys-PhysDom-Server]'),
            check('Kein F0467 mehr im Tenant Lab02', 'nofaults', under='uni/tn-Lab02', code='F0467'),
            check('h1 in EPG Server gelernt', 'endpoint', host='h1', epg='uni/tn-Lab02/ap-AP1/epg-Server'),
            check('h2 in EPG Server gelernt', 'endpoint', host='h2', epg='uni/tn-Lab02/ap-AP1/epg-Server'),
            check('Ping h1 → h2', 'traffic', src='h1', dst='h2', proto='icmp', expect=True)],
    solution='Die komplette Kette als JSON (POST an /api/mo/uni.json):\n\n`' + json.dumps(SERVER_ACCESS) + '`')

# ----------------------------------------------------------------------------
# Lab 03 - Tenant
# ----------------------------------------------------------------------------
lab(id='03-tenant-epg', title='03 Tenant, VRF, Bridge Domains und EPGs', topic='Tenant-Design', level='Einstieg',
    duration='30 min', fabric='discovered',
    goals=['Einen Tenant mit VRF, Bridge Domains und Subnetzen anlegen', 'EPGs mit Domain und Static Ports verbinden',
           'Verstehen, dass zwischen EPGs ohne Contract nichts fließt'],
    intro='Die Access Policies aus Lab 02 sind vorhanden (Ports 1/1-10 auf leaf101 und leaf102). Baue den Tenant '
          'für einen Webshop. **web1** hängt an leaf101 eth1/1 und sendet mit VLAN 110, **app1** an leaf102 eth1/2 mit VLAN 120.',
    config=[SERVER_ACCESS], hosts=[WEB1, APP1],
    tasks=[
        task('Tenant und VRF', 'Tenant **Shop**, darin VRF **Prod** (Policy Enforcement: Enforced).'),
        task('Bridge Domains', '**BD-Web** mit Gateway **10.10.10.1/24** und **BD-App** mit **10.10.20.1/24**, beide im VRF Prod.'),
        task('Application Profile und EPGs', 'AP **Webshop** mit den EPGs **Web** (BD-Web) und **App** (BD-App). '
             'Beide bekommen die Physical Domain **PhysDom-Server**.'),
        task('Static Ports', 'Web: leaf101 eth1/1, **vlan-110**, Trunk. App: leaf102 eth1/2, **vlan-120**, Trunk.'),
        task('Testen', 'web1 kann sein Gateway 10.10.10.1 pingen. Ein Ping von web1 zu app1 scheitert – warum? '
             'Schau dir auf leaf101 `show zoning-rule` an.'),
    ],
    checks=[check('VRF Shop/Prod', 'exists', dn='uni/tn-Shop/ctx-Prod'),
            check('BD-Web mit 10.10.10.1/24 im VRF Prod', 'exists', dn='uni/tn-Shop/BD-BD-Web/subnet-[10.10.10.1/24]'),
            check('BD-App mit 10.10.20.1/24', 'exists', dn='uni/tn-Shop/BD-BD-App/subnet-[10.10.20.1/24]'),
            check('web1 gelernt in EPG Web', 'endpoint', host='web1', epg='uni/tn-Shop/ap-Webshop/epg-Web'),
            check('app1 gelernt in EPG App', 'endpoint', host='app1', epg='uni/tn-Shop/ap-Webshop/epg-App'),
            check('web1 pingt sein Gateway', 'traffic', src='web1', dst='10.10.10.1', expect=True),
            check('app1 pingt sein Gateway', 'traffic', src='app1', dst='10.10.20.1', expect=True),
            check('web1 → app1 ist ohne Contract blockiert', 'traffic', src='web1', dst='app1', expect=False)],
    solution='Tenant-JSON:\n\n`' + json.dumps(shop_tenant()) + '`\n\nOhne Contract greift im VRF der Implicit Deny '
             '(Zoning-Rule `any_any_any(21)` mit `deny,log`).')

# ----------------------------------------------------------------------------
# Lab 04 - Contracts
# ----------------------------------------------------------------------------
vzany_solution = [filt('ssh', {'name': 'ssh', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '22', 'dToPort': '22'}),
                  contract('mgmt-ssh', ['ssh'])]
lab(id='04-contracts', title='04 Contracts, Filter und vzAny', topic='Policy / Contracts', level='Mittel',
    duration='35 min', fabric='discovered',
    goals=['Filter und Contracts anlegen', 'Provider und Consumer richtig zuordnen',
           'Reverse Filter Ports verstehen', 'vzAny für einen Contract an alle EPGs im VRF nutzen'],
    intro='Der Tenant **Shop** aus Lab 03 steht. Zusätzlich gibt es die EPG **Mgmt** mit dem Jump-Host **jump1** '
          '(10.10.40.11). Jetzt kommt die Policy.\n\n**Anforderungen:**\n- Web darf App auf **TCP 8080** und per **Ping** erreichen.\n'
          '- App darf von sich aus keine Verbindung zu Web aufbauen.\n- jump1 soll **jede** EPG im VRF Prod per **SSH (TCP 22)** erreichen.',
    config=[SERVER_ACCESS, shop_tenant(with_mgmt=True)], hosts=[WEB1, APP1, JUMP1],
    tasks=[
        task('Filter', 'Unter **Contracts > Filters** einen Filter **tcp-8080** mit einem Entry: EtherType IP, Protocol tcp, '
             'Destination Port 8080.',
             'Für Ping gibt es im Tenant common schon den Filter **icmp** – den kannst du direkt verwenden.'),
        task('Contract', 'Contract **web-to-app** (Scope VRF) mit einem Subject, das die Filter tcp-8080 und icmp enthält.'),
        task('Provider und Consumer', 'Die EPG **App** stellt den Dienst bereit (**Provided**), die EPG **Web** nutzt ihn '
             '(**Consumed**). Am EPG unter **Contracts** hinzufügen.'),
        task('Testen', 'web1 → app1: TCP 8080 und ICMP klappen, TCP 22 nicht. app1 → web1 auf TCP 8080 ist blockiert. '
             'Auf leaf101: `show zoning-rule` – erkennst du die Regeln bi-dir und uni-dir-ignore?'),
        task('vzAny', 'Filter **ssh** (tcp/22) und Contract **mgmt-ssh** anlegen. Unter **VRF Prod > EPG Collection for VRF** '
             'den Contract als **Provided** eintragen, an der EPG **Mgmt** als **Consumed**.',
             'vzAny steht für alle EPGs im VRF. Weil nur Mgmt konsumiert, darf Web trotzdem nicht per SSH zu App.'),
    ],
    checks=[check('web1 → app1 TCP 8080 erlaubt', 'traffic', src='web1', dst='app1', proto='tcp', port=8080, expect=True),
            check('web1 → app1 Ping erlaubt', 'traffic', src='web1', dst='app1', proto='icmp', expect=True),
            check('web1 → app1 TCP 22 blockiert', 'traffic', src='web1', dst='app1', proto='tcp', port=22, expect=False),
            check('app1 → web1 TCP 8080 blockiert (Provider baut nicht auf)', 'traffic', src='app1', dst='web1', proto='tcp', port=8080, expect=False),
            check('jump1 → web1 SSH erlaubt', 'traffic', src='jump1', dst='web1', proto='tcp', port=22, expect=True),
            check('jump1 → app1 SSH erlaubt', 'traffic', src='jump1', dst='app1', proto='tcp', port=22, expect=True)],
    solution='Contract web-to-app: `' + json.dumps(contract('web-to-app', ['tcp-8080', 'icmp'])) + '`\n\nvzAny: '
             '`POST /api/mo/uni/tn-Shop/ctx-Prod/any.json` mit `{"vzRsAnyToProv":{"attributes":{"tnVzBrCPName":"mgmt-ssh"}}}`, '
             'an der EPG Mgmt `fvRsCons` mit `tnVzBrCPName=mgmt-ssh`.')

# ----------------------------------------------------------------------------
# Lab 05 - vPC
# ----------------------------------------------------------------------------
lab(id='05-vpc-lacp', title='05 vPC mit LACP für einen Datenbankserver', topic='Access Policies / vPC', level='Mittel',
    duration='35 min', fabric='discovered',
    goals=['Eine Explicit vPC Protection Group anlegen', 'Eine vPC Interface Policy Group mit LACP bauen',
           'Einen vPC-Pfad als Static Port verwenden'],
    intro='Der Datenbankserver **db1** (10.10.30.11/24, VLAN 130) ist mit zwei NICs per **LACP active** an '
          '**leaf103 eth1/10** und **leaf104 eth1/10** angeschlossen. Der Tenant Shop mit Web und App läuft schon.',
    config=[SERVER_ACCESS, shop_tenant(with_contracts=True)],
    hosts=[WEB1, APP1, host('db1', '00:50:56:10:30:11', '10.10.30.11/24', '10.10.30.1', 130,
                            [[L103, 'eth1/10'], [L104, 'eth1/10']], 'lacp-active', 'Datenbank mit LACP-Bond')],
    tasks=[
        task('vPC-Domäne', '**Fabric > Access Policies > Policies > Switch > Virtual Port Channel default**: Explicit vPC '
             'Protection Group **vpc-103-104**, ID **34**, Switches 103 und 104.'),
        task('Port Channel Policy', '**Policies > Interface > Port Channel**: **LACP-Active** mit Mode *LACP Active*.'),
        task('vPC Policy Group', '**Policy Groups > PC/VPC Interface**: **IPG-vPC-db1**, Typ *Virtual Port Channel*, AAEP '
             '**AAEP-Server**, Port Channel Policy LACP-Active.'),
        task('Interface- und Switch-Profil', 'Interface Profile **IntProf-Leaf103-104** mit Selector **db1** für Port 1/10 → '
             'IPG-vPC-db1. Switch Profile **SwProf-Leaf103-104** für die Nodes 103-104.'),
        task('Tenant', 'Im Tenant Shop: **BD-DB** mit **10.10.30.1/24** im VRF Prod, EPG **DB** im AP Webshop mit Domain '
             'PhysDom-Server und Static Port **Virtual Port Channel** IPG-vPC-db1, **vlan-130**.',
             'Den vPC-Pfad gibt es erst, wenn die vPC Policy Group auf Ports beider Leafs angewendet ist.'),
        task('Contract', 'Filter **mysql** (tcp/3306), Contract **app-to-db**: DB provided, App consumed.'),
        task('Prüfen', 'Auf leaf103: `show vpc brief` und `show port-channel summary`. Was passiert, wenn du die Port '
             'Channel Policy auf *Static Channel - Mode On* stellst?'),
    ],
    checks=[check('vPC-Gruppe 103/104', 'class', cls='fabricExplicitGEp', attrs={'id': '34'}),
            check('db1 gelernt in EPG DB', 'endpoint', host='db1', epg='uni/tn-Shop/ap-Webshop/epg-DB'),
            check('app1 → db1 TCP 3306 erlaubt', 'traffic', src='app1', dst='db1', proto='tcp', port=3306, expect=True),
            check('web1 → db1 blockiert', 'traffic', src='web1', dst='db1', proto='tcp', port=3306, expect=False)],
    solution='Access-Teil: `' + json.dumps(access('VLAN-Pool-Server', 100, 199, 'PhysDom-Server', 'AAEP-Server', 'IPG-vPC-db1',
                                                 'IntProf-Leaf103-104', 'db1', 10, 10, 'SwProf-Leaf103-104', 103, 104,
                                                 pg_cls='infraAccBndlGrp',
                                                 pg_extra=[mo('infraRsLacpPol', {'tnLacpLagPolName': 'LACP-Active'})],
                                                 extra_infra=[mo('lacpLagPol', {'name': 'LACP-Active', 'mode': 'active'})])) +
             '`\n\nvPC-Pfad für den Static Port: `topology/pod-1/protpaths-103-104/pathep-[IPG-vPC-db1]`. Mit Mode On '
             'statt LACP sendet die ACI keine LACP-PDUs, der Host suspendiert seine Links und db1 verschwindet.')

# ----------------------------------------------------------------------------
# Lab 06 - L3Out OSPF
# ----------------------------------------------------------------------------
wan_router = router('wan1', L103, 'eth1/48', '172.16.0.2/30', 'ospf')
lab(id='06-l3out-ospf', title='06 L3Out mit OSPF ins WAN', topic='External Routing', level='Fortgeschritten',
    duration='45 min', fabric='discovered',
    goals=['Ein L3Out mit OSPF und Routed Interface bauen', 'Das MTU-Problem (EXSTART) erkennen und lösen',
           'External EPG, Contract und Advertised Externally zusammenbringen', 'Die Rolle des MP-BGP Route Reflectors verstehen'],
    intro='Der WAN-Router **wan1** hängt an **leaf103 eth1/48** (Routed, 172.16.0.2/30, OSPF **Area 0.0.0.1**, MTU **1500**). '
          'Er kennt das Internet (8.8.8.0/24, 1.1.1.0/24) und kündigt eine Default Route an. web1 soll ins Internet '
          '(Ping und HTTPS), app1 nicht.\n\nTenant Shop mit Web, App und Contract web-to-app ist vorhanden. Die BGP Route '
          'Reflector Policy ist **nicht** konfiguriert.',
    config=[SERVER_ACCESS, shop_tenant(with_contracts=True)], hosts=[WEB1, APP1], routers=[wan_router],
    tasks=[
        task('Access Policies für den Border Leaf', 'L3 Domain **L3Dom-WAN** (VLAN Pool **VLAN-Pool-WAN** 300-399, static), '
             'AAEP **AAEP-WAN** mit der L3 Domain, Policy Group **IPG-WAN**, Interface Profile **IntProf-Leaf103** mit Port '
             '1/48 und Switch Profile **SwProf-Leaf103** für Node 103.'),
        task('L3Out', 'Im Tenant Shop: L3Out **WAN**, VRF Prod, L3 Domain L3Dom-WAN, **OSPF** Area **0.0.0.1** (regular).'),
        task('Node- und Interface-Profil', 'Logical Node Profile **border**, Node **103** mit Router ID **1.1.1.103**. '
             'Logical Interface Profile **eth48** mit OSPF Interface Profile (Policy default) und einem **Routed Interface** '
             'auf leaf103 eth1/48 mit **172.16.0.1/30**.'),
        task('Nachbarschaft prüfen', 'Unter **Simulation > Externe Router** oder auf leaf103 mit '
             '`show ip ospf neighbors vrf Shop:Prod`. Warum bleibt die Nachbarschaft in **EXSTART** hängen? Behebe es.',
             'Die ACI nutzt bei MTU *inherit* 9000 Byte, der Router 1500. Entweder MTU am Interface auf 1500 setzen oder '
             'in einer eigenen OSPF Interface Policy *MTU ignore* aktivieren.'),
        task('External EPG', 'External EPG **Internet** mit Subnetz **0.0.0.0/0** (External Subnets for External EPG).'),
        task('Contract', 'Contract **web-to-internet** mit den Filtern icmp und **https** (tcp/443). Internet = Provider, '
             'Web = Consumer.'),
        task('Route nach außen', 'Am **BD-Web**: Subnetz auf **Advertised Externally** stellen und den BD mit dem L3Out '
             '**WAN** verknüpfen. Prüfe, ob wan1 jetzt 10.10.10.0/24 kennt.'),
        task('Traffic testen', 'Ping von web1 zu **8.8.8.8**. Wenn es scheitert: Wo genau? Tipp: web1 hängt an leaf101, das '
             'L3Out an leaf103. Prüfe `show ip route vrf Shop:Prod` auf beiden Leafs.',
             'System > System Settings > BGP Route Reflector: AS 65001, spine201 und spine202.'),
    ],
    checks=[check('OSPF-Nachbarschaft zu wan1 ist FULL', 'router', name='wan1', adj='FULL'),
            check('web1 → 8.8.8.8 Ping', 'traffic', src='web1', dst='8.8.8.8', proto='icmp', expect=True),
            check('web1 → 1.1.1.1 HTTPS', 'traffic', src='web1', dst='1.1.1.1', proto='tcp', port=443, expect=True),
            check('web1 → 8.8.8.8 SSH blockiert', 'traffic', src='web1', dst='8.8.8.8', proto='tcp', port=22, expect=False),
            check('app1 → 8.8.8.8 blockiert', 'traffic', src='app1', dst='8.8.8.8', proto='icmp', expect=False)],
    solution='Wichtige Objekte: `l3extOut WAN` mit `l3extRsEctx(Prod)`, `l3extRsL3DomAtt(uni/l3dom-L3Dom-WAN)`, '
             '`ospfExtP areaId=0.0.0.1`; `l3extRsNodeL3OutAtt tDn=topology/pod-1/node-103 rtrId=1.1.1.103`; '
             '`l3extRsPathL3OutAtt tDn=topology/pod-1/paths-103/pathep-[eth1/48] ifInstT=l3-port addr=172.16.0.1/30 '
             'mtu=1500` plus `ospfIfP`; `l3extInstP Internet` mit `l3extSubnet 0.0.0.0/0` und `fvRsProv web-to-internet`; '
             'BD-Web: `fvSubnet scope=public` und `fvRsBDToOut WAN`. Dazu die BGP Route Reflector Policy (AS 65001, RR 201/202).')

# ----------------------------------------------------------------------------
# Lab 07 - Troubleshooting
# ----------------------------------------------------------------------------
ops_access = access('VLAN-Pool-Ops', 100, 149, 'PhysDom-Ops', 'AAEP-Ops', 'IPG-Ops', 'IntProf-Ops', 'Ops-Ports', 1, 10,
                    'SwProf-Ops', 101, 102)
OD = 'uni/phys-PhysDom-Ops'
ops_tenant = mo('fvTenant', {'name': 'Ops'},
                mo('fvCtx', {'name': 'Ops'}),
                bd('BD-Web', 'Ops', '10.20.10.1/24'),
                bd('BD-App', 'Ops', '10.20.20.1/24', unicastRoute='no'),
                bd('BD-Backup', 'Ops', '10.20.30.1/24'),
                filt('http', {'name': 'http', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '8080', 'dToPort': '8080'}),
                contract('web-to-app', ['http', 'icmp'], rev='no'),
                mo('fvAp', {'name': 'Ops'},
                   epg('Web', 'BD-Web', OD, [(path(101, 'eth1/1'), 110)], cons=['web-to-app']),
                   epg('App', 'BD-App', OD, [(path(102, 'eth1/1'), 120)], prov=['web-to-app']),
                   epg('Clients', 'BD-Web', OD, [(path(101, 'eth1/2'), 150)]),
                   epg('Files', 'BD-Backup', OD, [(path(102, 'eth1/12'), 130)]),
                   epg('Backup', 'BD-Bakup', OD, [(path(101, 'eth1/3'), 140)])))
lab(id='07-troubleshooting', title='07 Troubleshooting: sechs Tickets', topic='Troubleshooting', level='Fortgeschritten',
    duration='45 min', fabric='discovered',
    goals=['Faults gezielt lesen (F0467, unaufgelöste Relationen)', 'Mit Traffic-Test, CLI und EP Tracker eingrenzen',
           'Typische Fehler in Access Policies, BDs und Contracts finden'],
    intro='Im Tenant **Ops** laufen sechs Tickets auf. Ändere die Konfiguration so, dass alle Tickets gelöst sind. Die '
          'Hosts sind richtig konfiguriert – der Fehler liegt immer in der ACI.\n\n'
          '- web1: leaf101 eth1/1, VLAN 110, 10.20.10.11\n- app1: leaf102 eth1/1, VLAN 120, 10.20.20.11\n'
          '- pc1: leaf101 eth1/2, VLAN 150, 10.20.10.50\n- files1: leaf102 eth1/12, VLAN 130, 10.20.30.20\n'
          '- backup1: leaf101 eth1/3, VLAN 140, 10.20.30.11',
    config=[ops_access, ops_tenant],
    hosts=[host('web1', '00:50:56:20:10:11', '10.20.10.11/24', '10.20.10.1', 110, [[L101, 'eth1/1']]),
           host('app1', '00:50:56:20:20:11', '10.20.20.11/24', '10.20.20.1', 120, [[L102, 'eth1/1']]),
           host('pc1', '00:50:56:20:10:50', '10.20.10.50/24', '10.20.10.1', 150, [[L101, 'eth1/2']]),
           host('files1', '00:50:56:20:30:20', '10.20.30.20/24', '10.20.30.1', 130, [[L102, 'eth1/12']]),
           host('backup1', '00:50:56:20:30:11', '10.20.30.11/24', '10.20.30.1', 140, [[L101, 'eth1/3']])],
    tasks=[
        task('Ticket 1', '„Mein PC (pc1) bekommt keine Verbindung."\n\n**Finden mit:** Tab *Faults* der EPG **Clients** '
             '(oder `moquery -c faultInst -f \'fault.Inst.code=="F0467"\'` auf dem APIC).',
             'Lies den Grund im F0467 genau: Welches VLAN, welcher Pool?'),
        task('Ticket 2', '„Der Fileserver files1 an leaf102 Port 12 ist nicht erreichbar."\n\n**Finden mit:** Tab *Faults* der '
             'EPG **Files**, danach die Access Port Selectors unter *Fabric > Access Policies*.',
             'invalid-path heißt: Für diesen Port gibt es keine Access Policy mit der Domain.'),
        task('Ticket 3', '„web1 erreicht app1 nicht auf TCP 80." (Die Anwendung läuft auf Port 80.)\n\n**Finden mit:** '
             '*Operations > Visibility & Troubleshooting* (web1 → app1, TCP 80), danach `show zoning-rule` auf leaf101.'),
        task('Ticket 4', '„app1 kann nicht einmal sein Gateway 10.20.20.1 pingen."\n\n**Finden mit:** Traffic-Test app1 → '
             '10.20.20.1 und `show ip route vrf Ops:Ops` auf leaf102.'),
        task('Ticket 5', '„backup1 wird in der Fabric nicht gelernt."\n\n**Finden mit:** Tab *Faults* der EPG **Backup** und '
             '`show endpoint` auf leaf101.',
             'Schau dir die Bridge-Domain-Zuordnung der EPG Backup genau an.'),
        task('Ticket 6', '„Seit dem Fix für Ticket 3 kommt die Anfrage an, aber keine Antwort zurück."\n\n**Finden mit:** '
             'Traffic-Test web1 → app1 TCP 80: Er zeigt Anfrage und Antwort getrennt.',
             'Was regelt die Option *Reverse Filter Ports* am Subject?'),
    ],
    checks=[check('Ticket 1: pc1 gelernt', 'endpoint', host='pc1', epg='uni/tn-Ops/ap-Ops/epg-Clients'),
            check('Ticket 2: files1 gelernt', 'endpoint', host='files1', epg='uni/tn-Ops/ap-Ops/epg-Files'),
            check('Ticket 4: app1 pingt sein Gateway', 'traffic', src='app1', dst='10.20.20.1', expect=True),
            check('Ticket 5: backup1 gelernt', 'endpoint', host='backup1', epg='uni/tn-Ops/ap-Ops/epg-Backup'),
            check('Ticket 3+6: web1 → app1 TCP 80', 'traffic', src='web1', dst='app1', proto='tcp', port=80, expect=True),
            check('Keine F0467-Faults mehr im Tenant Ops', 'nofaults', under='uni/tn-Ops', code='F0467')],
    solution='1. VLAN Pool VLAN-Pool-Ops reicht nur bis 149, pc1 nutzt 150 → Encap Block erweitern (z. B. bis 199).\n'
             '2. Interface Selector Ops-Ports deckt nur 1/1-10 ab → Port 12 ergänzen (Port Block 12-12).\n'
             '3. Filter http hat Destination Port 8080 → auf 80 (http) ändern.\n'
             '4. BD-App hat Unicast Routing aus → einschalten.\n'
             '5. EPG Backup zeigt auf BD **BD-Bakup** (Tippfehler) → BD-Backup wählen.\n'
             '6. Subject im Contract web-to-app hat Reverse Filter Ports aus → einschalten, sonst passt die Antwort '
             '(Quellport 80) nicht auf den Filter.')

# ----------------------------------------------------------------------------
# Lab 08 - Automation
# ----------------------------------------------------------------------------
lab(id='08-rest-api', title='08 Automatisierung über die REST-API', topic='Automation', level='Mittel',
    duration='30 min', fabric='discovered',
    goals=['Mit aaaLogin ein Token holen', 'Objekte per POST anlegen und per GET mit Filtern abfragen',
           'Ansible (cisco.aci), Python oder Terraform gegen den Simulator laufen lassen'],
    intro='Der Simulator spricht die APIC-REST-API. Beispiele liegen im Ordner `beispiele/` (curl, Python, Ansible, '
          'Terraform). Schalte vorher den **API Inspector** (oben rechts) ein: Jede Aktion in der GUI zeigt dort den '
          'REST-Aufruf, den du nachbauen kannst.',
    tasks=[
        task('Anmelden', '`curl -c cookie.txt -X POST http://localhost:8080/api/aaaLogin.json -d \'{"aaaUser":{"attributes":{"name":"admin","pwd":"admin"}}}\'`'),
        task('Tenant per POST', 'Lege mit einem einzigen POST an `/api/mo/uni.json` den Tenant **Automation** mit VRF **v1**, '
             'BD **bd1** (Subnetz **192.168.1.1/24**), AP **app** und EPG **epg1** (BD bd1) an.',
             'Ein Tenant-Objekt mit `children`. Vorlage: `beispiele/curl-tenant.sh`.'),
        task('Abfragen', 'Frage alle Bridge Domains mit Unicast Routing ab: '
             '`/api/class/fvBD.json?query-target-filter=eq(fvBD.unicastRoute,"yes")`. Und den ganzen Tenant: '
             '`/api/mo/uni/tn-Automation.json?rsp-subtree=full`.'),
        task('Fehler provozieren', 'Sende einen BD mit `"arpFlood":"vielleicht"`. Welchen Fehlercode liefert die API?'),
        task('Ansible (optional)', 'Mit `ansible-playbook beispiele/ansible-tenant.yml` (Collection cisco.aci, '
             '`use_ssl: false`, Port 8080) denselben Tenant erzeugen.'),
    ],
    checks=[check('Tenant Automation mit VRF v1', 'exists', dn='uni/tn-Automation/ctx-v1'),
            check('BD bd1 mit 192.168.1.1/24', 'exists', dn='uni/tn-Automation/BD-bd1/subnet-[192.168.1.1/24]'),
            check('bd1 im VRF v1', 'exists', dn='uni/tn-Automation/BD-bd1/rsctx', attrs={'tnFvCtxName': 'v1'}),
            check('EPG epg1 mit BD bd1', 'exists', dn='uni/tn-Automation/ap-app/epg-epg1/rsbd', attrs={'tnFvBDName': 'bd1'})],
    solution='`' + json.dumps(mo('fvTenant', {'name': 'Automation'}, mo('fvCtx', {'name': 'v1'}),
                                 bd('bd1', 'v1', '192.168.1.1/24'), mo('fvAp', {'name': 'app'}, epg('epg1', 'bd1', dom=None)))) +
             '`\n\nDer Fehler bei arpFlood ist Code **801** (property failed validation).')

# ----------------------------------------------------------------------------
# Lab 09 - L3Out eBGP Sub-Interface
# ----------------------------------------------------------------------------
lab(id='09-l3out-bgp', title='09 L3Out mit eBGP über Sub-Interface', topic='External Routing', level='Fortgeschritten',
    duration='45 min', fabric='discovered',
    goals=['eBGP-L3Out mit Routed Sub-Interface bauen', 'VLAN für Sub-Interfaces in der L3 Domain bereitstellen',
           'BGP-Peer, Remote-AS und Fabric-AS richtig setzen'],
    intro='Der Provider-Router **isp1** hängt an **leaf104 eth1/47** und spricht **eBGP** über ein 802.1Q-Sub-Interface '
          '**VLAN 301** (172.16.1.2/30, AS **65100**). Er erwartet die ACI als AS **65001** und kündigt eine Default Route an.\n\n'
          'Tenant Shop mit Web, App und web-to-app ist vorhanden. BGP Route Reflector Policy und Access Policies für leaf104 fehlen.',
    config=[SERVER_ACCESS, shop_tenant(with_contracts=True)], hosts=[WEB1, APP1],
    routers=[router('isp1', L104, 'eth1/47', '172.16.1.2/30', 'bgp', vlan=301, rid='100.64.0.1')],
    tasks=[
        task('Fabric-AS', 'BGP Route Reflector Policy: AS **65001**, spine201 und spine202 als Route Reflector.'),
        task('Access Policies', 'L3 Domain **L3Dom-ISP** mit VLAN Pool **VLAN-Pool-ISP** (vlan-300 bis vlan-310, static), AAEP '
             '**AAEP-ISP**, Policy Group **IPG-ISP**, Interface Profile für Port 1/47 und Switch Profile für Node 104.'),
        task('L3Out', 'L3Out **ISP**, VRF Prod, L3 Domain L3Dom-ISP, Routing-Protokoll **BGP**. Node Profile mit Node 104 '
             '(Router ID 1.1.1.104). Interface Profile mit **Routed Sub-Interface** eth1/47, **vlan-301**, **172.16.1.1/30**.'),
        task('BGP-Peer', 'Am Interface einen BGP Peer **172.16.1.2** mit Remote AS **65100** anlegen.',
             'Den Peer findest du unter dem Interface im Baum (BGP Peers).'),
        task('Policy und Ankündigung', 'External EPG **Internet** (0.0.0.0/0), Contract **web-to-isp** (icmp) mit '
             'Internet als Provider und Web als Consumer, BD-Web *Advertised Externally* und mit L3Out ISP verknüpft.'),
        task('Prüfen', 'Auf leaf104: `show bgp ipv4 unicast summary vrf Shop:Prod`. Ping von web1 zu 1.1.1.1.'),
    ],
    checks=[check('BGP zu isp1 Established', 'router', name='isp1', adj='Established'),
            check('web1 → 1.1.1.1 Ping', 'traffic', src='web1', dst='1.1.1.1', proto='icmp', expect=True),
            check('isp1 → web1 Ping', 'traffic', src='isp1', dst='web1', proto='icmp', expect=True),
            check('app1 → 1.1.1.1 blockiert', 'traffic', src='app1', dst='1.1.1.1', expect=False)],
    solution='Interface: `l3extRsPathL3OutAtt tDn=topology/pod-1/paths-104/pathep-[eth1/47] ifInstT=sub-interface '
             'encap=vlan-301 addr=172.16.1.1/30`, darunter `bgpPeerP addr=172.16.1.2` mit `bgpAsP asn=65100`. Am L3Out '
             '`bgpExtP`. Ohne Fabric-AS (bgpAsP unter uni/fabric/bgpInstP-default) startet BGP nicht.')

# ----------------------------------------------------------------------------
# Lab 10 - OOB-Management und NTP
# ----------------------------------------------------------------------------
NODES_ALL = [(101, 'leaf101'), (102, 'leaf102'), (103, 'leaf103'), (104, 'leaf104'), (201, 'spine201'), (202, 'spine202')]
lab(id='10-mgmt-ntp', title='10 OOB-Management und NTP', topic='Fabric-Betrieb', level='Mittel', duration='30 min', fabric='discovered',
    goals=['Static Node Management Addresses im Tenant mgmt vergeben', 'Die NTP-Kette Date and Time Policy → Pod Policy Group → Pod Profile bauen',
           'Mit show ntp peer-status prüfen'],
    intro='Die Fabric läuft, aber die Switches haben weder eine Management-Adresse noch eine synchrone Uhrzeit. Ohne NTP stimmen '
          'die Zeitstempel in Faults, Events und im Audit Log nicht – bei der Fehlersuche ein echtes Problem.\n\n'
          'Das OOB-Netz ist **192.168.10.0/24**, Gateway **192.168.10.1**, der NTP-Server **192.168.10.250**.',
    tasks=[
        task('Management-Adressen', '**Tenants > mgmt > Node Management Addresses > Static Node Management Addresses**: Für jeden '
             'Switch eine Adresse **192.168.10.<Node-ID>/24** mit Gateway 192.168.10.1 (z. B. leaf101 → 192.168.10.101/24).',
             'Das sind sechs Einträge: 101, 102, 103, 104, 201, 202.'),
        task('Date and Time Policy', '**Fabric > Fabric Policies > Policies > Pod > Date and Time > default**: NTP-Server '
             '**192.168.10.250** mit Management EPG **default** (Out-of-Band) eintragen.'),
        task('Pod Policy Group', '**Fabric > Fabric Policies > Pods > Policy Groups**: **PodPol** mit Date Time Policy **default**.'),
        task('Pod Profile', '**Pods > Profiles > default**: Im Pod Selector **default** die Fabric Policy Group **PodPol** eintragen.',
             'Ohne diese Zuordnung wirkt die Date and Time Policy nirgends – das ist der häufigste Fehler.'),
        task('Prüfen', 'Auf einem Switch `show ntp peer-status`: Der Server muss mit `*` markiert sein. `show clock` zeigt die Zeitquelle.'),
    ],
    checks=[check('Management-Adresse leaf101', 'exists', dn='uni/tn-mgmt/mgmtp-default/oob-default/rsooBStNode-[topology/pod-1/node-101]'),
            check('Management-Adresse spine201', 'exists', dn='uni/tn-mgmt/mgmtp-default/oob-default/rsooBStNode-[topology/pod-1/node-201]'),
            check('NTP-Server in der Date and Time Policy', 'exists', dn='uni/fabric/time-default/ntpprov-192.168.10.250'),
            check('Pod Profile default nutzt eine Pod Policy Group', 'exists', dn='uni/fabric/funcprof/podpgrp-PodPol'),
            check('Alle Switches NTP-synchron', 'ntp', min=6)],
    solution='Adressen: `mgmtRsOoBStNode` unter `uni/tn-mgmt/mgmtp-default/oob-default` mit `tDn=topology/pod-1/node-101`, '
             '`addr=192.168.10.101/24`, `gw=192.168.10.1`. NTP: `datetimeNtpProv name=192.168.10.250` unter `uni/fabric/time-default` '
             'mit `datetimeRsNtpProvToEpg tDn=uni/tn-mgmt/mgmtp-default/oob-default`. Pod: `fabricPodPGrp PodPol` mit `fabricRsTimePol` '
             '(`tnDatetimePolName=default`) und `fabricRsPodPGrp tDn=uni/fabric/funcprof/podpgrp-PodPol` am Selector `pods-default-typ-ALL`.')

# ----------------------------------------------------------------------------
# Lab 11 - Static Leaf und Taboo
# ----------------------------------------------------------------------------
APP2 = host('app2', '00:50:56:10:20:12', '10.10.20.12/24', '10.10.20.1', 120, [[L102, 'eth1/3']], descr='zweiter App-Server')
lab(id='11-static-leaf-taboo', title='11 Static Leaf und Taboo Contracts', topic='Policy / Deployment', level='Mittel', duration='25 min',
    fabric='discovered',
    goals=['Eine EPG per Static Leaf auf alle passenden Ports eines Leafs bringen', 'Mit einem Taboo Contract Verkehr trotz Contract sperren'],
    intro='Der Webshop läuft: web1 erreicht app1 auf TCP 8080 und per Ping (Contract web-to-app). Neu ist **app2** an **leaf102 '
          'eth1/3** (VLAN 120). Das Team möchte nicht für jeden App-Server einen Static Port pflegen. Außerdem verlangt die '
          'Security-Abteilung, dass die App-Server **nicht pingbar** sind – egal, was die Contracts erlauben.',
    config=[SERVER_ACCESS, shop_tenant(with_contracts=True)], hosts=[WEB1, APP1, APP2],
    tasks=[
        task('Static Leaf', 'In der EPG **App** unter **Static Leafs**: Node **102**, Encap **vlan-120**, Mode Trunk.',
             'Ein Static Leaf deployt die EPG auf allen Ports des Leafs, deren Access Policy die Domain der EPG enthält.'),
        task('Prüfen', 'app2 ist jetzt in der EPG App gelernt. Auf leaf102: `show vlan extended` – auf welchen Ports liegt vlan-120?'),
        task('Taboo Contract', 'Unter **Contracts > Taboos** den Taboo Contract **no-ping** mit einem Subject und dem Filter **icmp** '
             '(aus common) anlegen. An der EPG **App** unter **Contracts** als **Taboo Contract** hinzufügen.'),
        task('Testen', 'Ping web1 → app1 ist blockiert, TCP 8080 funktioniert weiter.'),
    ],
    checks=[check('app2 gelernt in EPG App', 'endpoint', host='app2', epg='uni/tn-Shop/ap-Webshop/epg-App'),
            check('web1 → app2 TCP 8080 erlaubt', 'traffic', src='web1', dst='app2', proto='tcp', port=8080, expect=True),
            check('web1 → app1 Ping blockiert (Taboo)', 'traffic', src='web1', dst='app1', proto='icmp', expect=False),
            check('web1 → app1 TCP 8080 weiter erlaubt', 'traffic', src='web1', dst='app1', proto='tcp', port=8080, expect=True)],
    solution='Static Leaf: `fvRsNodeAtt tDn=topology/pod-1/node-102 encap=vlan-120` an der EPG App. Taboo: `vzTaboo no-ping` mit '
             '`vzTSubj` und `vzRsDenyRule tnVzFilterName=icmp`, an der EPG `fvRsProtBy tnVzTabooName=no-ping`.')


# ----------------------------------------------------------------------------
# Lab 12 - VMM-Integration mit vCenter
# ----------------------------------------------------------------------------
ESXI_ACCESS = mo('polUni', {}, mo('infraInfra', {},
    mo('infraAttEntityP', {'name': 'AAEP-ESXi'}),
    mo('infraFuncP', {}, mo('infraAccPortGrp', {'name': 'IPG-ESXi'}, mo('infraRsAttEntP', {'tDn': 'uni/infra/attentp-AAEP-ESXi'}))),
    mo('infraAccPortP', {'name': 'IntProf-Leaf101-102'},
       mo('infraHPortS', {'name': 'ESXi-Ports', 'type': 'range'},
          mo('infraPortBlk', {'name': 'block2', 'fromPort': '11', 'toPort': '11'}),
          mo('infraRsAccBaseGrp', {'tDn': 'uni/infra/funcprof/accportgrp-IPG-ESXi'})))))
VC12 = {'name': 'vcsa01', 'ip': '192.168.10.50', 'datacenter': 'DC-Frankfurt', 'user': 'administrator@vsphere.local', 'pwd': 'Lab12!vc',
        'hosts': [{'name': 'esx01', 'links': [[L101, 'eth1/11']], 'dvs': ['VDS-Prod'],
                   'vms': [{'name': 'web-vm1', 'mac': '00:50:56:12:10:21', 'ip': '10.10.10.21/24', 'gw': '10.10.10.1', 'network': 'Shop|Webshop|Web', 'silent': False}]},
                  {'name': 'esx02', 'links': [[L102, 'eth1/11']], 'dvs': ['VDS-Prod'],
                   'vms': [{'name': 'app-vm1', 'mac': '00:50:56:12:20:21', 'ip': '10.10.20.21/24', 'gw': '10.10.20.1', 'network': 'Shop|Webshop|App', 'silent': False}]}]}
VMM12 = mo('polUni', {},
    mo('infraInfra', {}, mo('fvnsVlanInstP', {'name': 'VLAN-Pool-VMM', 'allocMode': 'dynamic'}, mo('fvnsEncapBlk', {'from': 'vlan-1000', 'to': 'vlan-1099'})),
       mo('infraAttEntityP', {'name': 'AAEP-ESXi'}, mo('infraRsDomP', {'tDn': 'uni/vmmp-VMware/dom-VDS-Prod'}))),
    mo('vmmProvP', {'vendor': 'VMware'}, mo('vmmDomP', {'name': 'VDS-Prod'},
       mo('infraRsVlanNs', {'tDn': 'uni/infra/vlanns-[VLAN-Pool-VMM]-dynamic'}),
       mo('vmmUsrAccP', {'name': 'vc-admin', 'usr': 'administrator@vsphere.local', 'pwd': 'Lab12!vc'}),
       mo('vmmCtrlrP', {'name': 'vcsa01', 'hostOrIp': '192.168.10.50', 'rootContName': 'DC-Frankfurt'},
          mo('vmmRsAcc', {'tDn': 'uni/vmmp-VMware/dom-VDS-Prod/usracc-vc-admin'})))))
lab(id='12-vmm-vcenter', title='12 VMM-Integration mit VMware vCenter', topic='Virtual Networking', level='Fortgeschritten',
    duration='40 min', fabric='discovered',
    goals=['Eine vCenter VMM Domain mit dynamischem VLAN Pool anlegen', 'Port Groups Tenant|AP|EPG vom APIC erzeugen lassen',
           'Resolution Immediacy und LLDP-Discovery zum ESXi verstehen'],
    intro='Im Webshop kommen virtuelle Server dazu. Im vCenter **vcsa01** (192.168.10.50, Datacenter **DC-Frankfurt**, Benutzer '
          '**administrator@vsphere.local**, Passwort **Lab12!vc**) gibt es den Distributed Switch **VDS-Prod** mit den Hosts **esx01** '
          '(leaf101 eth1/11) und **esx02** (leaf102 eth1/11). Die VMs **web-vm1** und **app-vm1** sind schon auf die Port Groups '
          '`Shop|Webshop|Web` und `Shop|Webshop|App` eingestellt – nur gibt es diese Port Groups noch nicht.\n\n'
          'Policy Group **IPG-ESXi** und Selector für Port 1/11 sind vorhanden, das AAEP **AAEP-ESXi** ist aber noch leer. '
          'Den Zustand im vCenter siehst du unter **Simulation > vCenter**.',
    config=[SERVER_ACCESS, ESXI_ACCESS, shop_tenant(with_contracts=True)], hosts=[WEB1, APP1], vcenters=[VC12],
    tasks=[
        task('Dynamischer VLAN Pool', '**Fabric > Access Policies > Pools > VLAN**: **VLAN-Pool-VMM** mit *Dynamic Allocation* '
             'und dem Encap Block vlan-1000 bis vlan-1099.',
             'Ein statischer Pool reicht nicht: Der APIC vergibt die VLANs für die Port Groups selbst.'),
        task('VMM Domain', '**Virtual Networking > VMM Domains > VMware**, Rechtsklick **Create vCenter Domain**: Name **VDS-Prod**, '
             'VLAN Pool VLAN-Pool-VMM, AAEP **AAEP-ESXi**, Credential **vc-admin** und Controller **vcsa01** mit IP und Datacenter.',
             'Der Datacenter-Name muss exakt stimmen. Unter **Operational** der Domain siehst du, ob der APIC verbunden ist (Fault S0606, wenn nicht).'),
        task('EPGs anbinden', 'An den EPGs **Web** und **App** jeweils **Add VMM Domain Association** mit VDS-Prod, '
             'Resolution Immediacy **Immediate**.'),
        task('Prüfen', 'Unter **Simulation > vCenter** erscheinen die Port Groups mit VLANs aus dem Pool, die VMs werden gelernt. '
             'Auf leaf101: `show vlan extended` und `show endpoint` – Learning Source *learned,vmm*.'),
        task('Experiment', 'Stelle die Resolution Immediacy an der EPG App auf **On Demand** und lösche app-vm1. Was passiert mit dem VLAN auf leaf102?'),
    ],
    checks=[check('VMM Domain VDS-Prod mit vCenter verbunden', 'vmm', dn='uni/vmmp-VMware/dom-VDS-Prod'),
            check('web-vm1 in EPG Web gelernt', 'endpoint', host='web-vm1', epg='uni/tn-Shop/ap-Webshop/epg-Web'),
            check('app-vm1 in EPG App gelernt', 'endpoint', host='app-vm1', epg='uni/tn-Shop/ap-Webshop/epg-App'),
            check('web-vm1 → app-vm1 TCP 8080', 'traffic', src='web-vm1', dst='app-vm1', proto='tcp', port=8080, expect=True),
            check('web1 (Bare Metal) → app-vm1 Ping', 'traffic', src='web1', dst='app-vm1', proto='icmp', expect=True)],
    solution='Domain: `' + json.dumps(VMM12) + '`\n\nAn der EPG: `fvRsDomAtt tDn=uni/vmmp-VMware/dom-VDS-Prod resImedcy=immediate`. '
             'Die Port Group heißt `Tenant|Application Profile|EPG`.')

# ----------------------------------------------------------------------------
# Lab 13 - Shared Services zwischen Tenants
# ----------------------------------------------------------------------------
DNS1 = host('dns1', '00:50:56:13:99:53', '10.99.0.53/24', '10.99.0.1', 199, [[L102, 'eth1/4']], descr='zentraler DNS-Server')
SHARED13 = mo('fvTenant', {'name': 'Shared'}, mo('fvCtx', {'name': 'Services'}), bd('BD-DNS', 'Services', '10.99.0.1/24'),
              mo('fvAp', {'name': 'Infra'}, epg('DNS', 'BD-DNS', ports=[(path(102, 'eth1/4'), 199)])))
lab(id='13-shared-services', title='13 Shared Services: Route Leaking zwischen Tenants', topic='Policy / Inter-VRF', level='Fortgeschritten',
    duration='35 min', fabric='discovered',
    goals=['Einen Contract mit Scope global in einen anderen Tenant exportieren', 'Provider-Subnetz an der EPG und Consumer-Subnetz '
           'mit "Shared between VRFs" setzen', 'Verstehen, warum Route Leaking in der ACI an den Contract gekoppelt ist'],
    intro='Der zentrale DNS-Server **dns1** (10.99.0.53) steht im Tenant **Shared**, VRF **Services**, EPG **DNS**. Die Webserver im '
          'Tenant **Shop** (VRF Prod) sollen ihn per **DNS (UDP 53)** erreichen – sonst nichts. Die App-Server dürfen gar nicht zum DNS.\n\n'
          'Zwischen zwei VRFs gibt es in der ACI erst Routen, wenn ein Contract die EPGs verbindet und die Subnetze als *shared* markiert sind.',
    config=[SERVER_ACCESS, shop_tenant(with_contracts=True), SHARED13], hosts=[WEB1, APP1, DNS1],
    tasks=[
        task('Filter und Contract', 'Im Tenant **Shared**: Filter **dns** (udp, Destination Port dns/53) und Contract **dns** mit '
             '**Scope Global**. Die EPG **DNS** stellt ihn bereit (**Provided**).',
             'Scope VRF (context) wirkt nur innerhalb eines VRFs, Scope Tenant nur innerhalb des Tenants.'),
        task('Provider-Subnetz', 'Unter der EPG **DNS** (nicht der BD!) das Subnetz **10.99.0.1/24** mit Scope *Shared between VRFs* anlegen.',
             'Beim Provider muss das Subnetz für das Route Leaking an der EPG stehen.'),
        task('Contract exportieren', 'Rechtsklick auf den Contract **dns** > **Export Contract**: Name **dns**, Ziel-Tenant **Shop**. '
             'Im Tenant Shop erscheint er unter **Contracts > Imported**.'),
        task('Consumer', 'An der EPG **Web** im Tenant Shop **Add Consumed Contract Interface** mit **dns**. '
             'Am **BD-Web** das Subnetz 10.10.10.1/24 zusätzlich auf *Shared between VRFs* stellen.'),
        task('Prüfen', 'web1 → dns1 UDP 53 klappt, TCP 22 nicht, app1 → dns1 gar nicht. Auf leaf101: `show ip route vrf Shop:Prod` '
             '– die Route 10.99.0.0/24 ist geleakt.'),
    ],
    checks=[check('Imported Contract dns im Tenant Shop', 'exists', dn='uni/tn-Shop/cif-dns'),
            check('web1 → dns1 UDP 53', 'traffic', src='web1', dst='dns1', proto='udp', port=53, expect=True),
            check('web1 → dns1 TCP 22 blockiert', 'traffic', src='web1', dst='dns1', proto='tcp', port=22, expect=False),
            check('app1 → dns1 blockiert', 'traffic', src='app1', dst='dns1', proto='udp', port=53, expect=False)],
    solution='Tenant Shared: `vzBrCP dns scope=global` mit Filter udp/53, an der EPG DNS `fvRsProv` und `fvSubnet ip=10.99.0.1/24 '
             'scope=private,shared`. Export: `vzCPIf name=dns` im Tenant Shop mit `vzRsIf tDn=uni/tn-Shared/brc-dns`. Consumer: '
             '`fvRsConsIf tnVzCPIfName=dns` an der EPG Web und `fvSubnet 10.10.10.1/24 scope=private,shared` am BD-Web.')

# ----------------------------------------------------------------------------
# Lab 14 - L2Out und Migration vom Legacy-Netz
# ----------------------------------------------------------------------------
WEB2 = host('web2', '00:50:56:14:50:11', '10.10.50.11/24', '10.10.50.1', 150, [[L101, 'eth1/6']], descr='neuer Server in der ACI')
OLD14 = dict(host('old-srv', '00:50:56:14:50:20', '10.10.50.20/24', '10.10.50.1', 300, [[L103, 'eth1/20']],
                  descr='Altsystem hinter dem Legacy-Switch, sendet nie von selbst'), silent=True)
MIG14 = mo('fvTenant', {'name': 'Shop'},
           bd('BD-Migration', 'Prod', unicastRoute='no', arpFlood='no', unkMacUcastAct='flood'),
           mo('fvAp', {'name': 'Migration'}, epg('Neu', 'BD-Migration', ports=[(path(101, 'eth1/6'), 150)])))
L2ACC14 = mo('polUni', {},
             mo('infraInfra', {},
                mo('fvnsVlanInstP', {'name': 'VLAN-Pool-Legacy', 'allocMode': 'static'}, mo('fvnsEncapBlk', {'from': 'vlan-300', 'to': 'vlan-300'})),
                mo('infraAttEntityP', {'name': 'AAEP-Legacy'}, mo('infraRsDomP', {'tDn': 'uni/l2dom-L2Dom-Legacy'})),
                mo('infraFuncP', {}, mo('infraAccPortGrp', {'name': 'IPG-Legacy'}, mo('infraRsAttEntP', {'tDn': 'uni/infra/attentp-AAEP-Legacy'}))),
                mo('infraAccPortP', {'name': 'IntProf-Leaf103'}, mo('infraHPortS', {'name': 'legacy', 'type': 'range'},
                   mo('infraPortBlk', {'name': 'block2', 'fromPort': '20', 'toPort': '20'}),
                   mo('infraRsAccBaseGrp', {'tDn': 'uni/infra/funcprof/accportgrp-IPG-Legacy'}))),
                mo('infraNodeP', {'name': 'SwProf-Leaf103'}, mo('infraLeafS', {'name': '103', 'type': 'range'},
                   mo('infraNodeBlk', {'name': 'blk', 'from_': '103', 'to_': '103'})),
                   mo('infraRsAccPortP', {'tDn': 'uni/infra/accportprof-IntProf-Leaf103'}))),
             mo('l2extDomP', {'name': 'L2Dom-Legacy'}, mo('infraRsVlanNs', {'tDn': 'uni/infra/vlanns-[VLAN-Pool-Legacy]-static'})))
L2OUT14 = mo('fvTenant', {'name': 'Shop'},
             mo('vzBrCP', {'name': 'migration', 'scope': 'context'}, mo('vzSubj', {'name': 'any', 'revFltPorts': 'yes'}, mo('vzRsSubjFiltAtt', {'tnVzFilterName': 'default'}))),
             mo('fvAp', {'name': 'Migration'}, mo('fvAEPg', {'name': 'Neu'}, mo('fvRsCons', {'tnVzBrCPName': 'migration'}))),
             mo('l2extOut', {'name': 'Legacy'}, mo('l2extRsEBd', {'tnFvBDName': 'BD-Migration', 'encap': 'vlan-300'}),
                mo('l2extRsL2DomAtt', {'tDn': 'uni/l2dom-L2Dom-Legacy'}),
                mo('l2extLNodeP', {'name': 'default'}, mo('l2extLIfP', {'name': 'default'}, mo('l2extRsPathL2OutAtt', {'tDn': path(103, 'eth1/20')}))),
                mo('l2extInstP', {'name': 'LegacyNet'}, mo('fvRsProv', {'tnVzBrCPName': 'migration'}))))
lab(id='14-l2out-migration', title='14 L2Out und Migration: stille Hosts und ARP Flooding', topic='Netzwerk-Migration', level='Fortgeschritten',
    duration='40 min', fabric='discovered',
    goals=['Ein altes Netz per L2Out (External Bridged Network) an eine Bridge Domain anbinden',
           'Verstehen, warum stille Hosts ohne ARP Flooding unerreichbar bleiben', 'BD-Einstellungen für eine Migrationsphase wählen'],
    intro='Das Subnetz **10.10.50.0/24** zieht vom alten Netz in die ACI. Das Gateway **10.10.50.1** bleibt während der Migration noch '
          'auf dem Legacy-Router – die **BD-Migration** ist deshalb reines Layer 2 (Unicast Routing aus, kein Subnetz). Der neue Server '
          '**web2** (EPG **Neu**) ist schon in der ACI.\n\nDer Legacy-Switch hängt an **leaf103 eth1/20** und spricht **VLAN 300**. Dahinter '
          'steht **old-srv** (10.10.50.20) – ein Altsystem, das nie von selbst sendet. Die ACI kann es also nicht lernen, bis jemand es per ARP anfragt.',
    config=[SERVER_ACCESS, shop_tenant(), MIG14], hosts=[WEB2, OLD14],
    tasks=[
        task('Access Policies', 'VLAN Pool **VLAN-Pool-Legacy** (static, vlan-300), **External Bridged Domain** **L2Dom-Legacy** '
             '(Physical and External Domains > External Bridged Domains), AAEP **AAEP-Legacy**, Policy Group **IPG-Legacy**, '
             'Interface Profile **IntProf-Leaf103** mit Port 1/20 und Switch Profile **SwProf-Leaf103** für Node 103.'),
        task('L2Out', 'Im Tenant Shop **Networking > L2Outs**, **Create L2Out**: Name **Legacy**, Bridge Domain **BD-Migration**, '
             'Encap **vlan-300**, Domain L2Dom-Legacy, Path leaf103 eth1/20, External EPG **LegacyNet**.'),
        task('Contract', 'Contract **migration** (Filter **default** aus common): LegacyNet *Provided*, EPG **Neu** *Consumed*.',
             'Ein L2Out hat ein eigenes External EPG (eigener pcTag) – auch im selben BD braucht es einen Contract.'),
        task('Erster Test', 'Ping von web2 zu old-srv. Warum scheitert er? Lies den Schritt im Ergebnis.'),
        task('ARP Flooding', 'Im **BD-Migration** unter Policy > General **ARP Flooding** aktivieren und erneut testen.',
             'Ohne Unicast Routing kann die ACI kein ARP Glean machen. Den ARP-Request für einen unbekannten Host muss sie dann fluten.'),
    ],
    checks=[check('L2Out Legacy ohne F0467', 'nofaults', under='uni/tn-Shop/l2out-Legacy', code='F0467'),
            check('L2Out Legacy auf leaf103 eth1/20', 'exists', dn='uni/tn-Shop/l2out-Legacy/lnodep-default/lifp-default/rspathL2OutAtt-[topology/pod-1/paths-103/pathep-[eth1/20]]'),
            check('ARP Flooding im BD-Migration', 'exists', dn='uni/tn-Shop/BD-BD-Migration', attrs={'arpFlood': 'yes'}),
            check('web2 → old-srv Ping', 'traffic', src='web2', dst='old-srv', proto='icmp', expect=True)],
    solution='Access: `' + json.dumps(L2ACC14) + '`\n\nTenant: `' + json.dumps(L2OUT14) + '`\n\nUnd am BD: `arpFlood=yes`. '
             'In der Migrationsphase typisch: L2 Unknown Unicast *Flood*, ARP Flooding *an*, Unicast Routing *aus*.')


# ----------------------------------------------------------------------------
# Lab 15 - Transit Routing und Route Control
# ----------------------------------------------------------------------------
WAN15 = router('wan1', L103, 'eth1/48', '172.16.0.2/30', 'ospf', networks=('8.8.8.0/24', '1.1.1.0/24'),
               advertise=('8.8.8.0/24', '1.1.1.0/24'))
PARTNER15 = router('partner1', L104, 'eth1/47', '172.16.1.2/30', 'bgp', vlan=301, rid='100.64.0.1',
                   networks=('192.168.50.0/24', '10.66.0.0/16'), advertise=('192.168.50.0/24', '10.66.0.0/16'))
ACC15 = [access('VLAN-Pool-WAN', 300, 399, 'L3Dom-WAN', 'AAEP-WAN', 'IPG-WAN', 'IntProf-Leaf103', 'wan', 48, 48,
                'SwProf-Leaf103', 103, 103, l3=True),
         access('VLAN-Pool-ISP', 300, 310, 'L3Dom-ISP', 'AAEP-ISP', 'IPG-ISP', 'IntProf-Leaf104', 'isp', 47, 47,
                'SwProf-Leaf104', 104, 104, l3=True),
         mo('polUni', {}, mo('fabricInst', {}, mo('bgpInstPol', {'name': 'default'}, mo('bgpAsP', {'asn': '65001'}),
                                                    mo('bgpRRP', {}, mo('bgpRRNodePEp', {'id': '201'}), mo('bgpRRNodePEp', {'id': '202'})))))]
TEN15 = mo('fvTenant', {'name': 'Shop'},
           filt('https', {'name': 'https', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': 'https', 'dToPort': 'https'}),
           contract('web-to-internet', ['icmp', 'https']),
           bd('BD-Web', 'Prod', '10.10.10.1/24', 'public', 'WAN'),
           mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Web'}, mo('fvRsCons', {'tnVzBrCPName': 'web-to-internet'}))),
           mo('l3extOut', {'name': 'WAN'}, mo('l3extRsEctx', {'tnFvCtxName': 'Prod'}),
              mo('l3extRsL3DomAtt', {'tDn': 'uni/l3dom-L3Dom-WAN'}), mo('ospfExtP', {'areaId': '0.0.0.1'}),
              mo('l3extLNodeP', {'name': 'border'}, mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-103', 'rtrId': '1.1.1.103'}),
                 mo('l3extLIfP', {'name': 'eth48'}, mo('ospfIfP', {}),
                    mo('l3extRsPathL3OutAtt', {'tDn': path(103, 'eth1/48'), 'ifInstT': 'l3-port', 'addr': '172.16.0.1/30', 'mtu': '1500'}))),
              mo('l3extInstP', {'name': 'Internet'}, mo('l3extSubnet', {'ip': '0.0.0.0/0'}), mo('fvRsProv', {'tnVzBrCPName': 'web-to-internet'}))),
           mo('l3extOut', {'name': 'Partner'}, mo('l3extRsEctx', {'tnFvCtxName': 'Prod'}),
              mo('l3extRsL3DomAtt', {'tDn': 'uni/l3dom-L3Dom-ISP'}), mo('bgpExtP', {}),
              mo('l3extLNodeP', {'name': 'border'}, mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-104', 'rtrId': '1.1.1.104'}),
                 mo('l3extLIfP', {'name': 'eth47'},
                    mo('l3extRsPathL3OutAtt', {'tDn': path(104, 'eth1/47'), 'ifInstT': 'sub-interface', 'encap': 'vlan-301', 'addr': '172.16.1.1/30'},
                       mo('bgpPeerP', {'addr': '172.16.1.2'}, mo('bgpAsP', {'asn': '65100'}))))),
              mo('l3extInstP', {'name': 'PartnerNet'}, mo('l3extSubnet', {'ip': '192.168.50.0/24'}))))
SOL15 = mo('fvTenant', {'name': 'Shop'},
           contract('transit', ['default']),
           mo('l3extOut', {'name': 'WAN'}, mo('l3extInstP', {'name': 'Internet'},
              mo('l3extSubnet', {'ip': '192.168.50.0/24', 'scope': 'export-rtctrl'}), mo('fvRsProv', {'tnVzBrCPName': 'transit'}))),
           mo('l3extOut', {'name': 'Partner', 'enforceRtctrl': 'export,import'}, mo('l3extInstP', {'name': 'PartnerNet'},
              mo('l3extSubnet', {'ip': '192.168.50.0/24', 'scope': 'import-security,import-rtctrl'}),
              mo('l3extSubnet', {'ip': '8.8.8.0/24', 'scope': 'export-rtctrl'}), mo('fvRsCons', {'tnVzBrCPName': 'transit'}))))
lab(id='15-transit-route-control', title='15 Transit Routing und Route Control', topic='L3Out / Routing', level='Fortgeschritten',
    duration='40 min', fabric='discovered',
    goals=['Routen von einem L3Out zum anderen weitergeben (Transit Routing)', 'Export und Import Route Control Subnets einsetzen',
           'Den Unterschied zwischen exaktem Match und Aggregate verstehen'],
    intro='Der Webshop hat zwei L3Outs im VRF Prod: **WAN** (OSPF zu **wan1** auf leaf103, Netze 8.8.8.0/24 und 1.1.1.0/24) '
          'und **Partner** (eBGP zu **partner1** auf leaf104, Netze 192.168.50.0/24 und 10.66.0.0/16). Beide Nachbarschaften laufen.\n\n'
          '**Anforderung:** Das Partnernetz **192.168.50.0/24** soll über die ACI nur **8.8.8.0/24** erreichen. Das interne Partnernetz '
          '**10.66.0.0/16** darf nicht in die ACI gelangen, und der Partner darf **1.1.1.0/24** nicht sehen.\n\n'
          'Standardmäßig gibt die ACI gelernte Routen nicht an andere L3Outs weiter – das muss man explizit mit Export Route Control erlauben.',
    config=[SERVER_ACCESS] + ACC15 + [shop_tenant(), TEN15], hosts=[WEB1], routers=[WAN15, PARTNER15],
    tasks=[
        task('Ausgangslage prüfen', 'Auf leaf104: `show ip route vrf Shop:Prod` – 8.8.8.0/24 kommt per MP-BGP von leaf103. '
             'Wird es an partner1 weitergegeben? `show bgp ipv4 unicast vrf Shop:Prod`. Traffic-Test von **192.168.50.10** zu **8.8.8.8**.'),
        task('Export Richtung WAN', 'Am External EPG **Internet** (L3Out WAN) das Subnetz **192.168.50.0/24** nur mit '
             '**Export Route Control Subnet** anlegen.', 'Ohne "External Subnets for the External EPG" – sonst würde das Partnernetz '
             'auf der WAN-Seite klassifiziert.'),
        task('Export Richtung Partner', 'Am External EPG **PartnerNet** (L3Out Partner) **8.8.8.0/24** mit Export Route Control Subnet.',
             'Exakter Match: Nur genau dieses Präfix wird exportiert. Mit 0.0.0.0/0 und *Aggregate Export* ginge alles raus – auch 1.1.1.0/24.'),
        task('Contract', 'Contract **transit** mit dem Filter **default** (common): **Internet** provided, **PartnerNet** consumed.'),
        task('Import Route Control', 'Am L3Out **Partner** unter *Route Control Enforcement* zusätzlich **Import** aktivieren und am '
             'Subnetz 192.168.50.0/24 von PartnerNet **Import Route Control Subnet** setzen.',
             'Mit Import-Enforcement übernimmt die ACI nur noch Präfixe, die ein Import Route Control Subnet erlaubt.'),
        task('Verifizieren', 'leaf104: `show ip route vrf Shop:Prod` (10.66.0.0/16 ist weg), `show bgp ipv4 unicast vrf Shop:Prod`. '
             'Traffic-Test 192.168.50.10 → 8.8.8.8 und 192.168.50.10 → 1.1.1.1.'),
    ],
    checks=[check('Transit: 192.168.50.10 → 8.8.8.8', 'traffic', src='192.168.50.10', dst='8.8.8.8', proto='icmp', expect=True),
            check('wan1 lernt 192.168.50.0/24', 'learned', router='wan1', prefix='192.168.50.0/24'),
            check('partner1 lernt 8.8.8.0/24', 'learned', router='partner1', prefix='8.8.8.0/24'),
            check('partner1 lernt 1.1.1.0/24 nicht', 'learned', router='partner1', prefix='1.1.1.0/24', expect=False),
            check('10.66.0.0/16 nicht in der ACI (leaf104)', 'route', node=104, vrf='Shop:Prod', prefix='10.66.0.0/16', expect=False),
            check('web1 → 8.8.8.8 funktioniert weiter', 'traffic', src='web1', dst='8.8.8.8', proto='icmp', expect=True)],
    solution='`' + json.dumps(SOL15) + '`\\n\\nExport Route Control Subnets steuern, welche Routen ein L3Out an seinen Nachbarn '
             'gibt; Import Route Control Subnets (nur mit Enforcement *Import*) steuern, was die ACI übernimmt. '
             'Klassifiziert wird weiterhin nur über *External Subnets for the External EPG*.')


# ----------------------------------------------------------------------------
# Lab 16 - Service Graph mit Policy-Based Redirect (Firewall)
# ----------------------------------------------------------------------------
FW16 = {'name': 'fw1', 'links': [[L102, 'eth1/20']], 'allow': ['tcp/8080'],
        'ifs': [{'name': 'outside', 'vlan': 401, 'ip': '192.168.100.10/24', 'mac': '00:50:56:FA:01:01'},
                {'name': 'inside', 'vlan': 402, 'ip': '192.168.101.10/24', 'mac': '00:50:56:FA:01:02'}]}
FWPORT16 = mo('polUni', {}, mo('infraInfra', {}, mo('infraAccPortP', {'name': 'IntProf-Leaf101-102'},
    mo('infraHPortS', {'name': 'FW-Ports', 'type': 'range'}, mo('infraPortBlk', {'name': 'block2', 'fromPort': '20', 'toPort': '20'}),
       mo('infraRsAccBaseGrp', {'tDn': 'uni/infra/funcprof/accportgrp-IPG-Server-Access'})))))
LDEV16 = 'uni/tn-Shop/lDevVip-FW1'
SOL16 = [
    ['uni/infra/vlanns-[VLAN-Pool-Server]-static', mo('fvnsVlanInstP', {}, mo('fvnsEncapBlk', {'from': 'vlan-400', 'to': 'vlan-410'}))],
    ['uni', mo('fvTenant', {'name': 'Shop'},
               bd('BD-FW-Ext', 'Prod', '192.168.100.1/24'), bd('BD-FW-Int', 'Prod', '192.168.101.1/24'),
               mo('vnsLDevVip', {'name': 'FW1', 'svcType': 'FW', 'devtype': 'PHYSICAL', 'funcType': 'GoTo'},
                  mo('vnsRsALDevToPhysDomP', {'tDn': 'uni/phys-PhysDom-Server'}),
                  mo('vnsCDev', {'name': 'fw1'},
                     mo('vnsCIf', {'name': 'outside'}, mo('vnsRsCIfPathAtt', {'tDn': path(102, 'eth1/20')})),
                     mo('vnsCIf', {'name': 'inside'}, mo('vnsRsCIfPathAtt', {'tDn': path(102, 'eth1/20')}))),
                  mo('vnsLIf', {'name': 'consumer', 'encap': 'vlan-401'}, mo('vnsRsCIfAttN', {'tDn': LDEV16 + '/cDev-fw1/cIf-[outside]'})),
                  mo('vnsLIf', {'name': 'provider', 'encap': 'vlan-402'}, mo('vnsRsCIfAttN', {'tDn': LDEV16 + '/cDev-fw1/cIf-[inside]'}))),
               mo('vnsSvcCont', {},
                  mo('vnsSvcRedirectPol', {'name': 'PBR-Ext'}, mo('vnsRedirectDest', {'ip': '192.168.100.10', 'mac': '00:50:56:FA:01:01'})),
                  mo('vnsSvcRedirectPol', {'name': 'PBR-Int'}, mo('vnsRedirectDest', {'ip': '192.168.101.10', 'mac': '00:50:56:FA:01:02'}))),
               mo('vnsAbsGraph', {'name': 'FW-Graph'}, mo('vnsAbsNode', {'name': 'N1', 'funcType': 'GoTo', 'routingMode': 'Redirect'},
                                                           mo('vnsRsNodeToLDev', {'tDn': LDEV16}))),
               mo('vnsLDevCtx', {'ctrctNameOrLbl': 'web-to-app', 'graphNameOrLbl': 'FW-Graph', 'nodeNameOrLbl': 'N1'},
                  mo('vnsRsLDevCtxToLDev', {'tDn': LDEV16}),
                  mo('vnsLIfCtx', {'connNameOrLbl': 'consumer'}, mo('vnsRsLIfCtxToBD', {'tDn': 'uni/tn-Shop/BD-BD-FW-Ext'}),
                     mo('vnsRsLIfCtxToLIf', {'tDn': LDEV16 + '/lIf-consumer'}),
                     mo('vnsRsLIfCtxToSvcRedirectPol', {'tDn': 'uni/tn-Shop/svcCont/svcRedirectPol-PBR-Ext'})),
                  mo('vnsLIfCtx', {'connNameOrLbl': 'provider'}, mo('vnsRsLIfCtxToBD', {'tDn': 'uni/tn-Shop/BD-BD-FW-Int'}),
                     mo('vnsRsLIfCtxToLIf', {'tDn': LDEV16 + '/lIf-provider'}),
                     mo('vnsRsLIfCtxToSvcRedirectPol', {'tDn': 'uni/tn-Shop/svcCont/svcRedirectPol-PBR-Int'}))),
               mo('vzBrCP', {'name': 'web-to-app'}, mo('vzSubj', {'name': 'subj'}, mo('vzRsSubjGraphAtt', {'tnVnsAbsGraphName': 'FW-Graph'}))))]]
lab(id='16-service-graph-pbr', title='16 Service Graph mit Policy-Based Redirect', topic='L4-L7 Services', level='Fortgeschritten',
    duration='45 min', fabric='discovered',
    goals=['Ein L4-L7 Device (Firewall, Go-To, physisch) anlegen', 'Einen Service Graph mit PBR auf einen Contract anwenden',
           'Shadow-EPGs, Redirect-Regeln und Faults verstehen'],
    intro='Der Verkehr von **Web** zu **App** (Contract **web-to-app**: tcp/8080 und ICMP) soll künftig durch die Firewall **fw1** '
          '– ohne dass die Server ihr Gateway ändern. Dafür nutzt die ACI **Policy-Based Redirect (PBR)**.\n\n'
          'fw1 hängt an **leaf102 eth1/20** (Port-Policy vorhanden) mit zwei 802.1Q-Interfaces:\n'
          '- **outside** vlan-401, 192.168.100.10/24, MAC 00:50:56:FA:01:01\n- **inside** vlan-402, 192.168.101.10/24, MAC 00:50:56:FA:01:02\n\n'
          'Das Regelwerk der Firewall erlaubt nur **tcp/8080** (siehe Simulation > L4-L7 Geräte).',
    config=[SERVER_ACCESS, FWPORT16, shop_tenant(with_contracts=True)], hosts=[WEB1, APP1], devices=[FW16],
    tasks=[
        task('VLANs für die Firewall', 'Der VLAN Pool **VLAN-Pool-Server** braucht einen Encap Block **vlan-400 bis vlan-410**.',
             'Die Encaps der Cluster Interfaces müssen im VLAN Pool der Domain des L4-L7 Devices liegen.'),
        task('Service-BDs', 'Zwei BDs im VRF Prod: **BD-FW-Ext** (192.168.100.1/24) und **BD-FW-Int** (192.168.101.1/24).'),
        task('L4-L7 Device', '**Services > L4-L7 > Devices > Create L4-L7 Devices**: Name **FW1**, Firewall, Physical, Domain '
             'PhysDom-Server, Function Type **GoTo**. Concrete Device **fw1** mit den Interfaces outside und inside auf leaf102 eth1/20, '
             'Cluster Interfaces **consumer** (vlan-401, outside) und **provider** (vlan-402, inside).'),
        task('PBR Policies', '**Policies > Protocol > L4-L7 Policy-Based Redirect**: **PBR-Ext** mit Ziel 192.168.100.10 / 00:50:56:FA:01:01 '
             'und **PBR-Int** mit Ziel 192.168.101.10 / 00:50:56:FA:01:02.'),
        task('Service Graph Template', '**Service Graph Templates > Create**: **FW-Graph** mit FW1, Node **N1**, Route Redirect aktiv.'),
        task('Graph anwenden', 'Rechtsklick auf FW-Graph > **Apply L4-L7 Service Graph Template**: Consumer Web, Provider App, '
             'bestehender Contract web-to-app. Consumer-Connector BD-FW-Ext + PBR-Ext + Cluster Interface consumer, '
             'Provider-Connector BD-FW-Int + PBR-Int + provider.'),
        task('Verifizieren', '**Deployed Graph Instances** zeigt *applied*. Traffic-Test web1 → app1 tcp/8080 läuft über fw1. '
             'Warum ist Ping jetzt blockiert, obwohl der Contract ICMP erlaubt? Auf leaf101: `show zoning-rule` (Action redir) und '
             '`show service redir info`.'),
    ],
    checks=[check('Graph-Instanz applied', 'graph', contract='uni/tn-Shop/brc-web-to-app'),
            check('fw1 outside im Service-BD gelernt', 'endpoint', host='fw1:outside'),
            check('web1 → app1 tcp/8080 über die Firewall', 'traffic', src='web1', dst='app1', proto='tcp', port=8080, expect=True, via='fw1'),
            check('web1 → app1 Ping von der Firewall blockiert', 'traffic', src='web1', dst='app1', proto='icmp', expect=False)],
    solution='Wichtig sind die drei Teile: **L4-L7 Device** (Concrete Device mit Paths, Cluster Interfaces mit Encap), **Service Graph '
             'Template** (Node N1, Redirect) und die **Device Selection Policy** (Contract/Graph/Node, je Connector BD, Cluster Interface '
             'und PBR Policy). Am Subject des Contracts hängt `vzRsSubjGraphAtt tnVnsAbsGraphName=FW-Graph`. Die PBR-Ziele brauchen die '
             'richtige MAC der Firewall-Interfaces.')


# ----------------------------------------------------------------------------
# Lab 17 - SVI auf vPC mit Secondary IP und BFD
# ----------------------------------------------------------------------------
VPC34 = mo('polUni', {}, mo('fabricInst', {}, mo('fabricProtPol', {}, mo('fabricExplicitGEp', {'name': 'vpc-103-104', 'id': '34'},
           mo('fabricNodePEp', {'id': '103'}), mo('fabricNodePEp', {'id': '104'})))))
ACC17 = access('VLAN-Pool-Core', 350, 359, 'L3Dom-Core', 'AAEP-Core', 'IPG-vPC-core', 'IntProf-Leaf103-104', 'core', 30, 30,
               'SwProf-Leaf103-104', 103, 104, l3=True, pg_cls='infraAccBndlGrp',
               pg_extra=[mo('infraRsLacpPol', {'tnLacpLagPolName': 'LACP-Active'})],
               extra_infra=[mo('lacpLagPol', {'name': 'LACP-Active', 'mode': 'active'})])
CORE17 = dict(router('core1', L103, 'eth1/30', '172.16.50.6/29', 'ospf', vlan=350, rid='10.200.255.1',
                     networks=('10.200.0.0/16',), advertise=('10.200.0.0/16',)),
              links=[[L103, 'eth1/30'], [L104, 'eth1/30']], bond='lacp-active', bfd=True)
VPCPATH = 'topology/pod-1/protpaths-103-104/pathep-[IPG-vPC-core]'
SOL17 = mo('fvTenant', {'name': 'Shop'},
           mo('ospfIfPol', {'name': 'OSPF-BFD', 'nwT': 'bcast', 'ctrl': 'bfd'}),
           contract('web-to-campus', ['icmp']),
           bd('BD-Web', 'Prod', '10.10.10.1/24', 'public', 'Core'),
           mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Web'}, mo('fvRsCons', {'tnVzBrCPName': 'web-to-campus'}))),
           mo('l3extOut', {'name': 'Core'}, mo('l3extRsEctx', {'tnFvCtxName': 'Prod'}), mo('l3extRsL3DomAtt', {'tDn': 'uni/l3dom-L3Dom-Core'}),
              mo('ospfExtP', {'areaId': '0.0.0.1'}),
              mo('l3extLNodeP', {'name': 'border'},
                 mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-103', 'rtrId': '1.1.1.103'}),
                 mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-104', 'rtrId': '1.1.1.104'}),
                 mo('l3extLIfP', {'name': 'vpc-svi'}, mo('ospfIfP', {}, mo('ospfRsIfPol', {'tnOspfIfPolName': 'OSPF-BFD'})), mo('bfdIfP', {}),
                    mo('l3extRsPathL3OutAtt', {'tDn': VPCPATH, 'ifInstT': 'ext-svi', 'encap': 'vlan-350', 'mtu': '1500'},
                       mo('l3extMember', {'side': 'A', 'addr': '172.16.50.1/29'}, mo('l3extIp', {'addr': '172.16.50.3/29'})),
                       mo('l3extMember', {'side': 'B', 'addr': '172.16.50.2/29'}, mo('l3extIp', {'addr': '172.16.50.3/29'}))))),
              mo('l3extInstP', {'name': 'Campus'}, mo('l3extSubnet', {'ip': '10.200.0.0/16'}), mo('fvRsProv', {'tnVzBrCPName': 'web-to-campus'}))))
lab(id='17-l3out-vpc-svi-bfd', title='17 L3Out: SVI auf vPC mit Secondary IP und BFD', topic='L3Out / Routing', level='Fortgeschritten',
    duration='40 min', fabric='discovered',
    goals=['Ein L3Out-SVI auf einem vPC mit Side A, Side B und Secondary IP bauen', 'OSPF zu beiden Border Leafs aufbauen',
           'BFD für schnelle Ausfallerkennung aktivieren und verifizieren'],
    intro='Der Campus-Core **core1** hängt mit einem **LACP-Port-Channel** an **leaf103 eth1/30** und **leaf104 eth1/30** '
          '(vPC-Domäne 34, Policy Group **IPG-vPC-core** und L3 Domain **L3Dom-Core** mit vlan-350 bis 359 sind schon da). '
          'core1 spricht **OSPF Area 0.0.0.1** mit **BFD** in **vlan-350**, hat die Adresse **172.16.50.6/29** und MTU 1500. '
          'Hinter ihm liegt das Campusnetz **10.200.0.0/16**.\n\n'
          'Adressplan: leaf103 = Side A **172.16.50.1**, leaf104 = Side B **172.16.50.2**, gemeinsame Secondary IP **172.16.50.3** '
          '(Next Hop für Static Routes des Cores).',
    config=[SERVER_ACCESS, VPC34, ACC17, BGP_TREE, shop_tenant(with_contracts=True)], hosts=[WEB1, APP1], routers=[CORE17],
    tasks=[
        task('OSPF Interface Policy', 'Im Tenant Shop: OSPF Interface Policy **OSPF-BFD**, Network Type Broadcast, Interface Control **BFD**.'),
        task('L3Out Core', 'L3Out **Core**, VRF Prod, Domain L3Dom-Core, OSPF Area **0.0.0.1**. Node Profile mit **103** (1.1.1.103) und '
             '**104** (1.1.1.104).'),
        task('vPC-SVI', 'Logical Interface Profile mit OSPF Interface Profile (Policy OSPF-BFD) und BFD Interface Profile. Interface: '
             '**SVI**, Pfadtyp **Virtual Port Channel** IPG-vPC-core, **vlan-350**, MTU **1500**, Side A 172.16.50.1/29, Side B 172.16.50.2/29, '
             'Secondary 172.16.50.3/29.', 'MTU inherit wäre 9000 – core1 bliebe dann in EXSTART hängen.'),
        task('External EPG und Contract', 'External EPG **Campus** mit 10.200.0.0/16, Contract **web-to-campus** (icmp): Campus provided, '
             'Web consumed. BD-Web *Advertised Externally* und mit L3Out Core verknüpft.'),
        task('Verifizieren', 'Auf leaf103 und leaf104: `show ip ospf neighbors vrf Shop:Prod`, `show bfd neighbors vrf Shop:Prod`, '
             '`show ip interface brief vrf Shop:Prod` (Primary und Secondary auf vlan…). Ping von web1 zu 10.200.1.10.'),
    ],
    checks=[check('OSPF FULL auf leaf103 und leaf104', 'router', name='core1', adj='FULL', nodes=[103, 104]),
            check('BFD Up zu beiden Border Leafs', 'bfd', router='core1', nodes=[103, 104]),
            check('Secondary IP 172.16.50.3 auf Side A', 'exists', dn='uni/tn-Shop/out-Core/lnodep-border/lifp-vpc-svi/rspathL3OutAtt-[%s]/mem-A/addr-[172.16.50.3/29]' % VPCPATH),
            check('core1 lernt 10.10.10.0/24', 'learned', router='core1', prefix='10.10.10.0/24'),
            check('web1 → 10.200.1.10 Ping', 'traffic', src='web1', dst='10.200.1.10', proto='icmp', expect=True)],
    solution='`' + json.dumps(SOL17) + '`\\n\\nBei einem SVI auf einem vPC bekommt jeder Leaf seine Primary IP (Side A/B), die Secondary IP '
             'ist auf beiden aktiv. BFD läuft nur, wenn es im Protokoll (OSPF Interface Policy *BFD*) und auf dem Router aktiviert ist.')


# ----------------------------------------------------------------------------
# Lab 18 - eBGP ueber Loopbacks: Multihop, MD5, Timer und Summarization
# ----------------------------------------------------------------------------
ACC18 = access('VLAN-Pool-ISP', 300, 310, 'L3Dom-ISP', 'AAEP-ISP', 'IPG-ISP', 'IntProf-Leaf104', 'isp', 47, 47,
               'SwProf-Leaf104', 104, 104, l3=True)
PARTNER18 = dict(router('partner1', L104, 'eth1/47', '172.16.1.2/30', 'bgp', vlan=301, rid='192.168.255.1',
                        networks=('192.168.50.0/24',), advertise=('192.168.50.0/24',), static_back=('1.1.1.104/32',)))
PARTNER18['bgp'] = {'asn': '65100', 'peerAs': '65001', 'password': 'Partner#2026', 'hold': 30, 'keepalive': 10,
                    'updateSource': '192.168.255.1', 'peerAddr': '1.1.1.104'}
TEN18 = mo('fvTenant', {'name': 'Shop'},
           contract('partner-to-shop', ['icmp']),
           bd('BD-Web', 'Prod', '10.10.10.1/24', 'public', 'Partner'), bd('BD-App', 'Prod', '10.10.20.1/24', 'public', 'Partner'),
           mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Web'}, mo('fvRsProv', {'tnVzBrCPName': 'partner-to-shop'})),
              mo('fvAEPg', {'name': 'App'}, mo('fvRsProv', {'tnVzBrCPName': 'partner-to-shop'}))),
           mo('l3extOut', {'name': 'Partner'}, mo('l3extRsEctx', {'tnFvCtxName': 'Prod'}), mo('l3extRsL3DomAtt', {'tDn': 'uni/l3dom-L3Dom-ISP'}),
              mo('bgpExtP', {}),
              mo('l3extLNodeP', {'name': 'border'}, mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-104', 'rtrId': '1.1.1.104'}),
                 mo('l3extLIfP', {'name': 'eth47'}, mo('l3extRsPathL3OutAtt', {'tDn': path(104, 'eth1/47'), 'ifInstT': 'sub-interface',
                                                                              'encap': 'vlan-301', 'addr': '172.16.1.1/30'}))),
              mo('l3extInstP', {'name': 'PartnerNet'}, mo('l3extSubnet', {'ip': '192.168.50.0/24'}), mo('fvRsCons', {'tnVzBrCPName': 'partner-to-shop'}))))
SOL18 = mo('fvTenant', {'name': 'Shop'},
           mo('bgpCtxPol', {'name': 'Partner-Timers', 'kaIntvl': '10', 'holdIntvl': '30'}),
           mo('fvCtx', {'name': 'Prod'}, mo('fvRsBgpCtxPol', {'tnBgpCtxPolName': 'Partner-Timers'})),
           mo('bgpRtSummPol', {'name': 'Summary-Only', 'ctrl': 'summary-only'}),
           mo('l3extOut', {'name': 'Partner'},
              mo('l3extLNodeP', {'name': 'border'},
                 mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-104', 'rtrId': '1.1.1.104'},
                    mo('ipRouteP', {'ip': '192.168.255.1/32'}, mo('ipNexthopP', {'nhAddr': '172.16.1.2'}))),
                 mo('bgpPeerP', {'addr': '192.168.255.1', 'ttl': '2', 'password': 'Partner#2026'}, mo('bgpAsP', {'asn': '65100'}))),
              mo('l3extInstP', {'name': 'PartnerNet'},
                 mo('l3extSubnet', {'ip': '10.10.0.0/16', 'scope': 'export-rtctrl'},
                    mo('l3extRsSubnetToRtSumm', {'tDn': 'uni/tn-Shop/bgprtsum-Summary-Only'})))))
lab(id='18-ebgp-loopback-md5-summary', title='18 eBGP über Loopbacks: Multihop, MD5, Timer und Summarization', topic='L3Out / BGP',
    level='Fortgeschritten', duration='40 min', fabric='discovered',
    goals=['eBGP zwischen Loopbacks mit Multihop und Static Routes aufbauen', 'BGP-Session mit MD5-Passwort und eigenen Timern',
           'Mehrere BD-Subnetze als eine Summary ankündigen'],
    intro='Der Partner-Router **partner1** (AS 65100) hängt an **leaf104 eth1/47** (Sub-Interface vlan-301, 172.16.1.1/30 ↔ 172.16.1.2/30). '
          'Laut Partner-Vertrag läuft BGP **zwischen den Loopbacks**: partner1 nutzt **192.168.255.1** und spricht die ACI an '
          '**1.1.1.104** (Router ID von leaf104) an. Weitere Vorgaben: MD5-Passwort **Partner#2026**, Keepalive **10 s**, Hold **30 s**.\n\n'
          'Der Partner möchte für den Webshop nur **eine Route 10.10.0.0/16** sehen statt der einzelnen BD-Subnetze. '
          'L3Out **Partner**, External EPG und Contract sind vorbereitet.',
    config=[SERVER_ACCESS, ACC18, BGP_TREE, shop_tenant(), TEN18], hosts=[WEB1, APP1], routers=[PARTNER18],
    tasks=[
        task('Erreichbarkeit der Loopback', 'Am Node 104 im Node Profile eine Static Route **192.168.255.1/32** mit Next Hop **172.16.1.2**.',
             'Ohne diese Route kann leaf104 die Loopback des Partners nicht erreichen – BGP bleibt in Active.'),
        task('BGP Peer am Node Profile', 'BGP Peer Connectivity Profile **am Node Profile** (nicht am Interface): Peer **192.168.255.1**, '
             'Remote AS **65100**, **EBGP Multihop TTL 2**, Password **Partner#2026**.', 'Ein Peer am Node Profile nutzt die Loopback (Router ID) als Quelle.'),
        task('BGP Timers', 'BGP Timers Policy **Partner-Timers** (Keepalive 10, Hold 30) anlegen und am VRF **Prod** auswählen.'),
        task('Summarization', 'BGP Route Summarization Policy **Summary-Only** mit *Do not advertise more specifics*. Am External EPG '
             '**PartnerNet** das Subnetz **10.10.0.0/16** mit **Export Route Control Subnet** und dieser Policy anlegen.'),
        task('Verifizieren', 'leaf104: `show bgp ipv4 unicast neighbors vrf Shop:Prod` (Update Source, Multihop, Password, Hold Time), '
             '`show bgp ipv4 unicast summary vrf Shop:Prod`. Unter Simulation > Externe Router: Was lernt partner1?'),
    ],
    checks=[check('BGP partner1 Established', 'router', name='partner1', adj='Established'),
            check('Ausgehandelte Hold Time 30 s', 'bgptimer', router='partner1', hold=30),
            check('partner1 lernt die Summary 10.10.0.0/16', 'learned', router='partner1', prefix='10.10.0.0/16'),
            check('partner1 lernt 10.10.10.0/24 nicht mehr einzeln', 'learned', router='partner1', prefix='10.10.10.0/24', expect=False),
            check('192.168.50.10 → web1 Ping', 'traffic', src='192.168.50.10', dst='web1', proto='icmp', expect=True)],
    solution='`' + json.dumps(SOL18) + '`\\n\\nTypische Fehler: TTL 1 (Session bleibt Idle), fehlende Static Route zur Partner-Loopback '
             '(Active), falsches Passwort (Active, TCP-MD5 schlägt fehl).')


# ----------------------------------------------------------------------------
# Lab 19 - EIGRP und Static Route mit IP SLA Track
# ----------------------------------------------------------------------------
ACC19 = [access('VLAN-Pool-WAN', 300, 399, 'L3Dom-WAN', 'AAEP-WAN', 'IPG-WAN', 'IntProf-Leaf103', 'wan', 48, 48,
                'SwProf-Leaf103', 103, 103, l3=True),
         access('VLAN-Pool-ISP', 300, 310, 'L3Dom-ISP', 'AAEP-ISP', 'IPG-ISP', 'IntProf-Leaf104', 'isp', 47, 47,
                'SwProf-Leaf104', 104, 104, l3=True)]
BRANCH19 = dict(router('branch1', L103, 'eth1/48', '172.16.0.2/30', 'eigrp', rid='10.50.255.1',
                       networks=('10.50.0.0/16',), advertise=('10.50.0.0/16',)), eigrp={'asn': '100', 'hello': 5, 'hold': 15})
INET19 = router('inet1', L104, 'eth1/47', '172.16.1.2/30', 'static', networks=('8.8.8.0/24', '1.1.1.0/24'), advertise=(),
                static_back=('10.10.0.0/16',))
TEN19 = mo('fvTenant', {'name': 'Shop'},
           contract('web-to-internet', ['icmp']), contract('web-to-branch', ['icmp']),
           bd('BD-Web', 'Prod', '10.10.10.1/24', 'public', 'Branch'),
           mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Web'}, mo('fvRsCons', {'tnVzBrCPName': 'web-to-internet'}),
                                               mo('fvRsCons', {'tnVzBrCPName': 'web-to-branch'}))),
           mo('l3extOut', {'name': 'Internet'}, mo('l3extRsEctx', {'tnFvCtxName': 'Prod'}), mo('l3extRsL3DomAtt', {'tDn': 'uni/l3dom-L3Dom-ISP'}),
              mo('l3extLNodeP', {'name': 'border'},
                 mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-104', 'rtrId': '1.1.1.104'},
                    mo('ipRouteP', {'ip': '0.0.0.0/0'}, mo('ipNexthopP', {'nhAddr': '172.16.1.2'}))),
                 mo('l3extLIfP', {'name': 'eth47'}, mo('l3extRsPathL3OutAtt', {'tDn': path(104, 'eth1/47'), 'ifInstT': 'l3-port', 'addr': '172.16.1.1/30'}))),
              mo('l3extInstP', {'name': 'Internet'}, mo('l3extSubnet', {'ip': '0.0.0.0/0'}), mo('fvRsProv', {'tnVzBrCPName': 'web-to-internet'}))))
SOL19 = mo('fvTenant', {'name': 'Shop'},
           mo('eigrpIfPol', {'name': 'EIGRP-Branch', 'helloIntvl': '5', 'holdIntvl': '15'}),
           mo('l3extOut', {'name': 'Branch'}, mo('l3extRsEctx', {'tnFvCtxName': 'Prod'}), mo('l3extRsL3DomAtt', {'tDn': 'uni/l3dom-L3Dom-WAN'}),
              mo('eigrpExtP', {'asn': '100'}),
              mo('l3extLNodeP', {'name': 'border'}, mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-103', 'rtrId': '1.1.1.103'}),
                 mo('l3extLIfP', {'name': 'eth48'}, mo('eigrpIfP', {}, mo('eigrpRsIfPol', {'tnEigrpIfPolName': 'EIGRP-Branch'})),
                    mo('l3extRsPathL3OutAtt', {'tDn': path(103, 'eth1/48'), 'ifInstT': 'l3-port', 'addr': '172.16.0.1/30', 'mtu': '1500'}))),
              mo('l3extInstP', {'name': 'BranchNet'}, mo('l3extSubnet', {'ip': '10.50.0.0/16'}), mo('fvRsProv', {'tnVzBrCPName': 'web-to-branch'}))),
           mo('fvIPSLAMonitoringPol', {'name': 'icmp-5s', 'slaType': 'icmp', 'slaFrequency': '5'}),
           mo('fvTrackMember', {'name': 'inet1-gw', 'dstIpAddr': '172.16.1.2', 'scopeDn': 'uni/tn-Shop/out-Internet'},
              mo('fvRsIpslaMonPol', {'tDn': 'uni/tn-Shop/ipslaMonitoringPol-icmp-5s'})),
           mo('fvTrackList', {'name': 'inet-track', 'percentageUp': '1'}, mo('fvRsOtmListMember', {'tDn': 'uni/tn-Shop/trackmember-inet1-gw'})),
           mo('l3extOut', {'name': 'Internet'}, mo('l3extLNodeP', {'name': 'border'},
              mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-104', 'rtrId': '1.1.1.104'},
                 mo('ipRouteP', {'ip': '0.0.0.0/0'}, mo('ipRsRouteTrack', {'tDn': 'uni/tn-Shop/tracklist-inet-track'}))))))
RT19 = 'uni/tn-Shop/out-Internet/lnodep-border/rsnodeL3OutAtt-[topology/pod-1/node-104]/rt-[0.0.0.0/0]'
lab(id='19-eigrp-static-track', title='19 EIGRP und Static Route mit IP SLA Track', topic='L3Out / Routing', level='Fortgeschritten',
    duration='40 min', fabric='discovered',
    goals=['Ein L3Out mit EIGRP aufbauen', 'Eine Static Route über IP SLA und Track List an die Erreichbarkeit des Next Hops koppeln',
           'Mit show track und show ip route verifizieren'],
    intro='Zwei externe Anbindungen im VRF Prod:\n- Die Filiale **branch1** spricht **EIGRP AS 100** über **leaf103 eth1/48** '
          '(Routed, 172.16.0.1/30 ↔ 172.16.0.2/30, MTU 1500) und hat das Netz **10.50.0.0/16**.\n'
          '- Der Internet-Router **inet1** an **leaf104 eth1/47** ist per **Static Route** angebunden (L3Out **Internet**, Default Route '
          'über 172.16.1.2 ist schon konfiguriert).\n\nFällt inet1 aus, soll die Default Route verschwinden, damit die Fabric nicht in ein '
          'schwarzes Loch routet. Access Policies und Contracts sind vorbereitet.',
    config=[SERVER_ACCESS] + ACC19 + [BGP_TREE, shop_tenant(), TEN19], hosts=[WEB1, APP1], routers=[BRANCH19, INET19],
    tasks=[
        task('EIGRP Interface Policy', 'Im Tenant Shop: EIGRP Interface Policy **EIGRP-Branch** (Hello 5, Hold 15).'),
        task('L3Out Branch', 'L3Out **Branch**, VRF Prod, Domain **L3Dom-WAN**, Protokoll **EIGRP** mit AS **100**. Node 103 (1.1.1.103), '
             'Routed Interface eth1/48 mit 172.16.0.1/30 und MTU 1500, EIGRP Interface Profile mit EIGRP-Branch. External EPG **BranchNet** '
             '10.50.0.0/16, Contract **web-to-branch** provided.', 'BD-Web ist schon mit dem L3Out Branch verknüpft.'),
        task('IP SLA und Track', 'Unter **Policies > Protocol > IP SLA**: Monitoring Policy **icmp-5s** (ICMP, 5 s), Track Member **inet1-gw** '
             '(Ziel 172.16.1.2, Scope L3Out Internet, Policy icmp-5s), Track List **inet-track** mit diesem Member.'),
        task('Track an die Route', 'An der Static Route 0.0.0.0/0 (L3Out Internet, Node 104) die **Track Policy** inet-track eintragen.'),
        task('Verifizieren und Ausfall testen', 'leaf103: `show ip eigrp neighbors vrf Shop:Prod`. leaf104: `show track`, `show ip route vrf Shop:Prod`. '
             'Dann unter Simulation > Externe Router inet1 auf **ausgeschaltet** stellen: Track geht DOWN, die Default Route verschwindet.'),
    ],
    checks=[check('EIGRP-Nachbarschaft zu branch1', 'router', name='branch1', adj='UP'),
            check('web1 → 10.50.1.10 Ping', 'traffic', src='web1', dst='10.50.1.10', proto='icmp', expect=True),
            check('Static Route mit Track Policy', 'exists', dn=RT19 + '/rsRouteTrack'),
            check('Default Route auf leaf104 aktiv', 'route', node=104, vrf='Shop:Prod', prefix='0.0.0.0/0', proto='static'),
            check('web1 → 8.8.8.8 Ping', 'traffic', src='web1', dst='8.8.8.8', proto='icmp', expect=True)],
    solution='`' + json.dumps(SOL19) + '`\\n\\nIP SLA (fvIPSLAMonitoringPol) → Track Member (Ziel-IP, Scope) → Track List (Schwellwert) → '
             '`ipRsRouteTrack` an der Static Route. Ohne Antwort vom Ziel nimmt die ACI die Route aus der Routing-Tabelle.')

# ----------------------------------------------------------------------------
# Lab 20 - Floating SVI fuer einen virtuellen Router
# ----------------------------------------------------------------------------
VR20 = router('vrtr1', L101, 'eth1/9', '172.16.10.30/24', 'ospf', vlan=150, area='0.0.0.2', rid='10.77.255.1',
              networks=('10.77.0.0/16',), advertise=('10.77.0.0/16',))
TEN20 = mo('fvTenant', {'name': 'Shop'},
           contract('web-to-vnf', ['icmp']),
           bd('BD-Web', 'Prod', '10.10.10.1/24', 'public', 'VNF'),
           mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Web'}, mo('fvRsCons', {'tnVzBrCPName': 'web-to-vnf'}))))
SOL20 = mo('fvTenant', {'name': 'Shop'},
           mo('l3extOut', {'name': 'VNF'}, mo('l3extRsEctx', {'tnFvCtxName': 'Prod'}), mo('l3extRsL3DomAtt', {'tDn': 'uni/l3dom-L3Dom-WAN'}),
              mo('ospfExtP', {'areaId': '0.0.0.2'}),
              mo('l3extLNodeP', {'name': 'anchor'}, mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-103', 'rtrId': '1.1.1.103'}),
                 mo('l3extLIfP', {'name': 'floating'}, mo('ospfIfP', {}),
                    mo('l3extVirtualLIfP', {'nodeDn': 'topology/pod-1/node-103', 'encap': 'vlan-150', 'addr': '172.16.10.11/24', 'mtu': '1500'},
                       mo('l3extRsDynPathAtt', {'tDn': 'uni/phys-PhysDom-Server', 'floatingAddr': '172.16.10.100/24'})))),
              mo('l3extInstP', {'name': 'VNF-Net'}, mo('l3extSubnet', {'ip': '10.77.0.0/16'}), mo('fvRsProv', {'tnVzBrCPName': 'web-to-vnf'}))))
lab(id='20-floating-svi', title='20 Floating SVI für einen virtuellen Router', topic='L3Out / Routing', level='Fortgeschritten',
    duration='30 min', fabric='discovered',
    goals=['Verstehen, wofür Floating SVI gedacht ist (virtuelle Router/Firewalls, die zwischen Leafs wandern)',
           'Anchor Node, Primary IP und Floating IP richtig vergeben'],
    intro='Der virtuelle Router **vrtr1** (eine VM) läuft gerade auf einem Host an **leaf101 eth1/9** und kann jederzeit auf einen anderen '
          'Server wandern. Er spricht **OSPF Area 0.0.0.2** in **vlan-150** (172.16.10.30/24, MTU 1500) und hat das Netz **10.77.0.0/16**.\n\n'
          'Statt auf jedem möglichen Leaf ein SVI zu bauen, nutzt du eine **Floating SVI**: Anchor Node ist **leaf103** (172.16.10.11/24, '
          'hier läuft das Routing), auf allen anderen Leafs mit der Domain **PhysDom-Server** nimmt die ACI die Floating IP **172.16.10.100/24**.',
    config=[SERVER_ACCESS, ACC19[0], BGP_TREE, shop_tenant(), TEN20], hosts=[WEB1], routers=[VR20],
    tasks=[
        task('L3Out VNF', 'L3Out **VNF**, VRF Prod, Domain L3Dom-WAN, OSPF Area **0.0.0.2**. Node Profile mit Node 103 (1.1.1.103), Logical '
             'Interface Profile mit OSPF Interface Profile.'),
        task('Floating SVI', 'Im Interface Profile **Create Floating SVI**: Anchor Node 103, vlan-150, 172.16.10.11/24, MTU 1500. Path '
             'Attribute: Domain **PhysDom-Server** mit Floating IP **172.16.10.100/24**.',
             'Ohne Floating IP erreicht ein Router an einem Nicht-Anchor-Leaf die ACI nicht.'),
        task('External EPG', 'External EPG **VNF-Net** 10.77.0.0/16, Contract **web-to-vnf** provided.'),
        task('Verifizieren', 'leaf103: `show ip ospf neighbors vrf Shop:Prod`. Ping von web1 zu 10.77.1.1. Wandert die VM (Router-Anschluss '
             'auf einen anderen Leaf-Port mit derselben Domain), bleibt die Nachbarschaft bestehen.'),
    ],
    checks=[check('OSPF FULL zwischen vrtr1 und dem Anchor leaf103', 'router', name='vrtr1', adj='FULL', nodes=[103]),
            check('vrtr1 lernt 10.10.10.0/24', 'learned', router='vrtr1', prefix='10.10.10.0/24'),
            check('web1 → 10.77.1.1 Ping', 'traffic', src='web1', dst='10.77.1.1', proto='icmp', expect=True)],
    solution='`' + json.dumps(SOL20) + '`')


# ----------------------------------------------------------------------------
# Lab 21 - AAA mit TACACS+, Login-Domain und RBAC
# ----------------------------------------------------------------------------
ISE21 = {'name': 'ise1', 'ip': '192.168.10.40', 'type': 'tacacs', 'key': 'Tac#Key2026', 'down': False,
         'users': [{'name': 'netadmin', 'pwd': 'Net#2026', 'avpair': 'shell:domains=all/admin/'},
                   {'name': 'shopops', 'pwd': 'Shop#2026', 'avpair': 'shell:domains=Shop-Dom/tenant-admin/'},
                   {'name': 'guest', 'pwd': 'Guest#2026', 'avpair': ''}]}
SOL21 = [['uni/userext', mo('aaaUserEp', {},
            mo('aaaTacacsPlusEp', {}, mo('aaaTacacsPlusProvider', {'name': '192.168.10.40', 'key': 'Tac#Key2026'},
                                         mo('aaaRsSecProvToEpg', {'tDn': 'uni/tn-mgmt/mgmtp-default/oob-default'})),
                 mo('aaaTacacsPlusProviderGroup', {'name': 'ISE-TACACS'}, mo('aaaProviderRef', {'name': '192.168.10.40', 'order': '1'}))),
            mo('aaaLoginDomain', {'name': 'ISE'}, mo('aaaDomainAuth', {'realm': 'tacacs', 'providerGroup': 'ISE-TACACS'})),
            mo('aaaDomain', {'name': 'Shop-Dom'}),
            mo('aaaUser', {'name': 'shopro', 'pwd': 'Read#2026'}, mo('aaaUserDomain', {'name': 'Shop-Dom'}, mo('aaaUserRole', {'name': 'tenant-admin', 'privType': 'readPriv'}))))],
         ['uni/tn-Shop', mo('fvTenant', {}, mo('aaaDomainRef', {'name': 'Shop-Dom'}))]]
lab(id='21-aaa-tacacs-rbac', title='21 AAA: TACACS+, Login-Domain und RBAC', topic='Security', level='Fortgeschritten', duration='35 min',
    fabric='discovered',
    goals=['Einen TACACS+-Provider mit Provider Group und Login-Domain einrichten', 'Rechte über das Cisco AV-Pair vergeben',
           'Security Domains für mandantengetrennte Rechte nutzen'],
    intro='Die Admins melden sich künftig über **ISE** (TACACS+) an: Server **192.168.10.40**, Shared Key **Tac#Key2026**, erreichbar über '
          'das Out-of-Band-Netz. Auf dem ISE sind die Benutzer schon angelegt:\n'
          '- **netadmin** / Net#2026 – AV-Pair `shell:domains=all/admin/`\n'
          '- **shopops** / Shop#2026 – AV-Pair `shell:domains=Shop-Dom/tenant-admin/`\n'
          '- **guest** / Guest#2026 – ohne AV-Pair\n\n'
          'Dazu soll es einen lokalen Benutzer **shopro** (Passwort Read#2026) geben, der den Tenant Shop nur **lesen** darf. '
          'Die lokale Anmeldung (admin) bleibt Standard.',
    config=[SERVER_ACCESS, shop_tenant(with_contracts=True)], hosts=[WEB1, APP1], aaa=[ISE21],
    tasks=[
        task('TACACS+ Provider', '**Admin > AAA > TACACS+ Management > TACACS+ Providers**: 192.168.10.40, Key Tac#Key2026, Management EPG '
             '**default (Out-of-Band)**.'),
        task('Provider Group', 'TACACS+ Provider Group **ISE-TACACS** mit dem Provider (Priorität 1).'),
        task('Login Domain', '**Authentication > Login Domains**: **ISE**, Realm TACACS+, Provider Group ISE-TACACS.',
             'Anmelden dann mit Domain ISE auf der Login-Seite oder per REST als `apic#ISE\\\\netadmin`.'),
        task('Security Domain', '**Security > Security Domains**: **Shop-Dom**. Am Tenant Shop (Rechtsklick > Add Security Domain) Shop-Dom zuordnen.',
             'Der Name muss zum AV-Pair passen: shopops bekommt tenant-admin nur in Shop-Dom.'),
        task('Lokaler Benutzer', '**Local Users > Create Local User**: **shopro**, Passwort Read#2026, Security Domain Shop-Dom, Rolle '
             '**tenant-admin** mit **Read**.'),
        task('Ausprobieren', 'Ab- und als shopops (Domain ISE) wieder anmelden: Den Tenant Shop darfst du ändern, Access Policies nicht. '
             'Was passiert bei guest? Unter *Login-Protokoll* siehst du, wie jede Anmeldung lief.'),
    ],
    checks=[check('netadmin meldet sich über ISE als admin an', 'login', user='apic#ISE\\netadmin', pwd='Net#2026', role='admin'),
            check('shopops darf den Tenant Shop ändern', 'rbac', user='apic#ISE\\shopops', pwd='Shop#2026', dn='uni/tn-Shop/BD-BD-Web'),
            check('shopops darf keine Access Policies ändern', 'rbac', user='apic#ISE\\shopops', pwd='Shop#2026', dn='uni/infra/attentp-AAEP-Server', expect=False),
            check('guest ohne AV-Pair wird abgewiesen', 'login', user='apic#ISE\\guest', pwd='Guest#2026', expect=False),
            check('shopro darf Shop nur lesen', 'rbac', user='shopro', pwd='Read#2026', dn='uni/tn-Shop/BD-BD-Web', expect=False),
            check('shopro kann sich anmelden', 'login', user='shopro', pwd='Read#2026')],
    solution='Provider `aaaTacacsPlusProvider name=192.168.10.40` mit `key` und `aaaRsSecProvToEpg` auf oob-default, Provider Group '
             '`aaaTacacsPlusProviderGroup ISE-TACACS` mit `aaaProviderRef`, Login Domain `aaaLoginDomain ISE` mit `aaaDomainAuth realm=tacacs '
             'providerGroup=ISE-TACACS`. Security Domain `aaaDomain Shop-Dom`, am Tenant `aaaDomainRef name=Shop-Dom`. Lokaler Benutzer mit '
             '`aaaUserDomain Shop-Dom` und `aaaUserRole tenant-admin privType=readPriv`.')

# ----------------------------------------------------------------------------
# Lab 22 - In-Band-Management
# ----------------------------------------------------------------------------
INBACC22 = mo('polUni', {},
              mo('infraInfra', {},
                 mo('fvnsVlanInstP', {'name': 'VLAN-Pool-INB', 'allocMode': 'static'}, mo('fvnsEncapBlk', {'from': 'vlan-90', 'to': 'vlan-90'})),
                 mo('infraAttEntityP', {'name': 'AAEP-APIC'}, mo('infraRsDomP', {'tDn': 'uni/phys-PhysDom-INB'})),
                 mo('infraFuncP', {}, mo('infraAccPortGrp', {'name': 'IPG-APIC'}, mo('infraRsAttEntP', {'tDn': 'uni/infra/attentp-AAEP-APIC'}))),
                 mo('infraAccPortP', {'name': 'IntProf-Leaf101-102'}, mo('infraHPortS', {'name': 'APIC-Ports', 'type': 'range'},
                    mo('infraPortBlk', {'name': 'block2', 'fromPort': '48', 'toPort': '48'}),
                    mo('infraRsAccBaseGrp', {'tDn': 'uni/infra/funcprof/accportgrp-IPG-APIC'})))),
              mo('physDomP', {'name': 'PhysDom-INB'}, mo('infraRsVlanNs', {'tDn': 'uni/infra/vlanns-[VLAN-Pool-INB]-static'})))
INB22 = mo('fvTenant', {'name': 'mgmt'},
           mo('fvBD', {'name': 'inb'}, mo('fvSubnet', {'ip': '10.90.0.1/24'})),
           mo('mgmtMgmtP', {'name': 'default'}, mo('mgmtInB', {'name': 'default', 'encap': 'vlan-90'}, mo('mgmtRsMgmtBD', {'tnFvBDName': 'inb'}),
              *[mo('mgmtRsInBStNode', {'tDn': 'topology/pod-1/node-%d' % n, 'addr': '10.90.0.%d/24' % (10 if n == 1 else n), 'gw': '10.90.0.1'})
                for n in (1, 101, 102)])))
lab(id='22-inband-management', title='22 In-Band-Management', topic='Fabric-Betrieb', level='Fortgeschritten', duration='35 min',
    fabric='discovered',
    goals=['In-Band-Management mit eigenem VLAN, BD inb und In-Band EPG einrichten', 'Verstehen, warum die APIC-Ports eine Access Policy brauchen',
           'Einen AAA-Server über In-Band ansprechen'],
    intro='Das Management soll zusätzlich **In-Band** über die Fabric laufen: Netz **10.90.0.0/24**, Gateway **10.90.0.1** (BD **inb** im '
          'Tenant mgmt), **vlan-90**. Adressen: apic1 **10.90.0.10**, leaf101 **10.90.0.101**, leaf102 **10.90.0.102**.\n\n'
          'Anschließend soll der RADIUS-Server **192.168.20.41** (Key **Rad#2026**) über das In-Band EPG erreicht werden. Benutzer dort: '
          '**opsuser** / Ops#2026 mit AV-Pair `shell:domains=all/read-all/`.',
    config=[SERVER_ACCESS], hosts=[WEB1],
    aaa=[{'name': 'radius1', 'ip': '192.168.20.41', 'type': 'radius', 'key': 'Rad#2026', 'down': False,
          'users': [{'name': 'opsuser', 'pwd': 'Ops#2026', 'avpair': 'shell:domains=all/read-all/'}]}],
    tasks=[
        task('Access Policies für die APIC-Ports', 'Der APIC hängt an **leaf101/102 eth1/48**. VLAN Pool **VLAN-Pool-INB** (static, vlan-90), '
             'Physical Domain **PhysDom-INB**, AAEP **AAEP-APIC**, Policy Group **IPG-APIC** und im Interface Profile IntProf-Leaf101-102 '
             'einen Selector **APIC-Ports** für Port 1/48.',
             'Ohne diese Kette darf vlan-90 nicht auf den Port zum APIC – Fault S0211 am In-Band EPG.'),
        task('BD inb', 'Im Tenant **mgmt** am BD **inb** das Subnetz **10.90.0.1/24** anlegen.'),
        task('In-Band EPG', '**Tenants > mgmt > Node Management EPGs**: Rechtsklick **Create In-Band Management EPG**: **default**, '
             'vlan-90, BD inb, Adressen für Node 1 (APIC), 101 und 102.'),
        task('RADIUS über In-Band', 'RADIUS Provider 192.168.20.41 mit Key Rad#2026 und Management EPG **In-Band (default)**, Provider Group '
             '**RAD**, Login Domain **RAD** (Realm RADIUS).'),
        task('Verifizieren', 'Operational-Tab des In-Band EPG, `show controller`, auf leaf101 `show vlan extended`. Login als `opsuser` '
             'mit Domain RAD.'),
    ],
    checks=[check('In-Band aktiv auf apic1, leaf101 und leaf102', 'inb', nodes=[1, 101, 102]),
            check('Kein S0211-Fault mehr', 'nofaults', under='uni/tn-mgmt', code='S0211'),
            check('opsuser meldet sich über RADIUS (In-Band) an', 'login', user='apic#RAD\\opsuser', pwd='Ops#2026', role='read-all')],
    solution='Access: `' + json.dumps(INBACC22) + '`\\n\\nIn-Band: `' + json.dumps(INB22) + '`\\n\\nRADIUS-Provider mit `aaaRsSecProvToEpg '
             'tDn=uni/tn-mgmt/mgmtp-default/inb-default`.')

# ----------------------------------------------------------------------------
# Lab 23 - Endpoint Security Groups und uSeg EPGs
# ----------------------------------------------------------------------------
INF23 = host('web-inf', '00:50:56:10:10:66', '10.10.10.66/24', '10.10.10.1', 110, [[L101, 'eth1/3']], descr='kompromittierter Webserver')
SOL23 = mo('fvTenant', {'name': 'Shop'},
           filt('tcp-8080', {'name': 'tcp-8080', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '8080', 'dToPort': '8080'}),
           contract('frontend-to-backend', ['tcp-8080']),
           mo('fvAp', {'name': 'Webshop'},
              mo('fvAEPg', {'name': 'Web'}, mo('fvRsPathAtt', {'tDn': path(101, 'eth1/3'), 'encap': 'vlan-110'})),
              mo('fvAEPg', {'name': 'Quarantine', 'isAttrBasedEPg': 'yes'}, mo('fvRsBd', {'tnFvBDName': 'BD-Web'}),
                 mo('fvRsDomAtt', {'tDn': 'uni/phys-PhysDom-Server'}), mo('fvCrtrn', {}, mo('fvIpAttr', {'name': 'infected', 'ip': '10.10.10.66'}))),
              mo('fvESg', {'name': 'Frontend'}, mo('fvRsScope', {'tnFvCtxName': 'Prod'}),
                 mo('fvEPgSelector', {'matchEpgDn': 'uni/tn-Shop/ap-Webshop/epg-Web'}), mo('fvRsCons', {'tnVzBrCPName': 'frontend-to-backend'})),
              mo('fvESg', {'name': 'Backend'}, mo('fvRsScope', {'tnFvCtxName': 'Prod'}),
                 mo('fvEPgSelector', {'matchEpgDn': 'uni/tn-Shop/ap-Webshop/epg-App'}), mo('fvRsProv', {'tnVzBrCPName': 'frontend-to-backend'}))))
lab(id='23-esg-useg', title='23 Endpoint Security Groups und uSeg EPGs', topic='Policy / Segmentierung', level='Fortgeschritten',
    duration='35 min', fabric='discovered',
    goals=['Policy mit Endpoint Security Groups statt EPG-Contracts aufbauen', 'Einen einzelnen Host per uSeg EPG nach IP isolieren',
           'Verstehen, welche Contracts nach der ESG-Zuordnung noch gelten'],
    intro='Das Security-Team stellt auf **Endpoint Security Groups** um: Die Policy hängt nicht mehr an den EPGs, sondern an ESGs im VRF Prod. '
          'Gleichzeitig ist der Webserver **web-inf** (10.10.10.66 an leaf101 eth1/3, vlan-110) kompromittiert und muss sofort isoliert werden, '
          'ohne ihn umzukonfigurieren.\n\nZwischen Web und App gibt es noch **keinen** Contract.',
    config=[SERVER_ACCESS, shop_tenant()], hosts=[WEB1, APP1, INF23],
    tasks=[
        task('Static Port für web-inf', 'An der EPG **Web** einen Static Port leaf101 eth1/3, vlan-110 ergänzen. web-inf ist dann in Web gelernt.'),
        task('uSeg EPG', 'Im AP Webshop unter **uSeg EPGs** die EPG **Quarantine** (BD-Web, Domain PhysDom-Server) mit dem IP-Attribut '
             '**10.10.10.66** anlegen.', 'Die ACI klassifiziert den Host jetzt nach seiner IP in Quarantine – Port und VLAN bleiben gleich.'),
        task('Filter und Contract', 'Filter **tcp-8080** und Contract **frontend-to-backend**.'),
        task('ESGs', '**Endpoint Security Groups**: **Frontend** (VRF Prod, EPG Selector Web) konsumiert, **Backend** (VRF Prod, EPG Selector App) '
             'stellt den Contract bereit.', 'Ein Contract zwischen einer ESG und einer EPG ist nicht möglich.'),
        task('Prüfen', 'web1 → app1 tcp/8080 klappt, web-inf → app1 nicht. Im Traffic-Test siehst du die Klassifizierung (EPG → ESG). '
             'Auf leaf101: `show zoning-rule` – welche pcTags stehen in den Regeln?'),
    ],
    checks=[check('web-inf liegt in der uSeg EPG Quarantine', 'endpoint', host='web-inf', epg='uni/tn-Shop/ap-Webshop/epg-Quarantine'),
            check('web1 → app1 tcp/8080 über die ESGs', 'traffic', src='web1', dst='app1', proto='tcp', port=8080, expect=True, via='ESG'),
            check('web-inf → app1 blockiert', 'traffic', src='web-inf', dst='app1', proto='tcp', port=8080, expect=False),
            check('web1 → app1 tcp/22 blockiert', 'traffic', src='web1', dst='app1', proto='tcp', port=22, expect=False)],
    solution='`' + json.dumps(SOL23) + '`')


# ----------------------------------------------------------------------------
# Lab 24 - Firmware-Upgrade mit Upgrade Groups
# ----------------------------------------------------------------------------
VPC24 = mo('fabricProtPol', {'pairT': 'explicit'}, mo('fabricExplicitGEp', {'name': 'vpc-101-102', 'id': '12'},
                                                      mo('fabricNodePEp', {'id': '101'}), mo('fabricNodePEp', {'id': '102'})),
           mo('fabricExplicitGEp', {'name': 'vpc-103-104', 'id': '34'}, mo('fabricNodePEp', {'id': '103'}), mo('fabricNodePEp', {'id': '104'})))
FW24_DL = mo('firmwareRepoP', {}, mo('firmwareOSource', {'name': 'apic-6.0.6c', 'proto': 'scp', 'url': '192.168.10.50:/images/aci-apic-dk9.6.0.6c.iso',
                                                          'user': 'backup', 'password': 'Backup123!'}),
              mo('firmwareOSource', {'name': 'n9000-16.0.6c', 'proto': 'http', 'url': 'http://192.168.10.50/images/aci-n9000-dk9.16.0.6c.bin'}))


def upg_group(name, nodes, now):
    return mo('fabricInst', {}, mo('maintMaintP', {'name': name, 'version': 'n9000-16.0(6c)', 'adminSt': 'triggered' if now else 'untriggered'}),
              mo('maintMaintGrp', {'name': name}, mo('maintRsMgrpp', {'tnMaintMaintPName': name}),
                 *[mo('fabricNodeBlk', {'name': 'blk%d' % n, 'from_': str(n), 'to_': str(n)}) for n in nodes]))


lab(id='24-firmware-upgrade', title='24 Firmware-Upgrade mit Upgrade Groups', topic='Fabric-Betrieb', level='Fortgeschritten', duration='35 min',
    fabric='discovered', settings={'upgradeSeconds': 30},
    goals=['Firmware-Images ins Repository des APIC laden', 'Das Upgrade in der richtigen Reihenfolge fahren: erst der APIC, dann die Switches',
           'Upgrade Groups so bilden, dass nie beide vPC-Peers oder beide Spines gleichzeitig neu laden'],
    intro='Die Fabric läuft mit **6.0(5h)** (APIC) bzw. **16.0(5h)** (Switches). Ziel ist **6.0(6c) / 16.0(6c)**. Die Images liegen auf dem '
          'Fileserver **192.168.10.50** (SCP, Benutzer backup / Backup123!, oder HTTP) unter `/images`.\n\n'
          'leaf101/102 und leaf103/104 sind **vPC-Paare**. Ein Reload dauert im Simulator 30 Sekunden '
          '(einstellbar unter Simulation > Einstellungen).',
    config=[SERVER_ACCESS, mo('polUni', {}, mo('fabricInst', {}, VPC24)), shop_tenant(with_contracts=True)], hosts=[WEB1, APP1],
    tasks=[
        task('Images laden', '**Admin > Firmware > Download Tasks** (bzw. *Images > Add Firmware to APIC*): beide Images vom Fileserver laden, '
             'z. B. SCP `192.168.10.50:/images/aci-apic-dk9.6.0.6c.iso` und HTTP `http://192.168.10.50/images/aci-n9000-dk9.16.0.6c.bin`.'),
        task('Erst der APIC', '**Infrastructure > Controllers**: Zielversion apic-6.0(6c) wählen, dann *Actions > Upgrade Controller Now*. '
             'Während des Upgrades nimmt der APIC keine Konfiguration an.',
             'Versuchst du zuerst die Switches, bricht die Kompatibilitätsprüfung ab: Switches dürfen nicht neuer sein als der APIC.'),
        task('Upgrade Groups', '**Infrastructure > Nodes**: Zwei Gruppen **Odd** (101, 103, 201) und **Even** (102, 104, 202), Zielversion '
             'n9000-16.0(6c).', 'Eine Gruppe mit 101 und 102 erzeugt Fault S1801, eine mit beiden Spines S1802.'),
        task('Gruppe für Gruppe', 'Zuerst **Odd** starten (*Actions > Upgrade Now*) und während des Reloads den Traffic-Test web1 → app1 '
             'ausführen: web1 hängt **single-homed** an leaf101 und ist kurz offline – dual-homed Server (vPC) hätten keinen Ausfall, der '
             'vPC-Peer leaf102 lädt ja nicht gleichzeitig. Wenn Odd fertig ist, **Even** starten.'),
        task('Verifizieren', '`show firmware upgrade status` und `show version` auf dem APIC, Upgrade-Übersicht unter Admin > Firmware.'),
    ],
    checks=[check('APIC auf 6.0(6c), alle Switches auf 16.0(6c)', 'firmware', apic='6.0(6c)', switch='16.0(6c)'),
            check('Jeder Switch in genau einer Upgrade Group, kein vPC-Paar und nicht alle Spines zusammen', 'fwgroups', min=2),
            check('web1 → app1 tcp/8080 funktioniert', 'traffic', src='web1', dst='app1', proto='tcp', port=8080, expect=True)],
    solution='1. Download Tasks: `' + json.dumps(FW24_DL) + '`\n2. `uni/controller/ctrlrfwpol` version=apic-6.0(6c), dann '
             '`uni/controller/ctrlrmaintpol` adminSt=triggered\n3. Upgrade Groups: `' + json.dumps(upg_group('Odd', [101, 103, 201], True)) +
             '` und danach die Gruppe Even mit 102, 104, 202.')

# ----------------------------------------------------------------------------
# Lab 25 - Config Export und Import
# ----------------------------------------------------------------------------
def _backup25():
    import sys
    sys.path.insert(0, os.path.dirname(OUT))
    from dcprep.model import Store, post as mpost
    from dcprep.topology import base_config
    st = Store()
    base_config(st, 'admin')
    mpost(st, 'uni', shop_tenant(with_contracts=True))
    rows = [r for r in st.dump_config() if r[0] == 'uni/tn-Shop' or r[0].startswith('uni/tn-Shop/')]
    for r in rows:  # fester Zeitstempel, damit der Generator deterministisch bleibt
        for x in r[1:]:
            if isinstance(x, dict) and 'modTs' in x:
                x['modTs'] = '2026-10-26T22:59:58.000+00:00'
    return {'size': '18 KB', 'export': {'kind': 'aci-config-export', 'created': '2026-10-26T23:00:04.000+00:00', 'target': 'uni/tn-Shop',
                                        'secure': False, 'key': '', 'policy': 'Shop-Nightly', 'rows': rows, 'version': '6.0(5h)',
                                        'counters': dict(st.counters)}}


RL25 = mo('fileRemotePath', {'name': 'SCP-Backup', 'host': '192.168.10.50', 'protocol': 'scp', 'remotePath': '/backup', 'remotePort': '22',
                             'userName': 'backup', 'userPasswd': 'Backup123!'},
          mo('fileRsARemoteHostToEpg', {'tDn': 'uni/tn-mgmt/mgmtp-default/oob-default'}))
IMP25 = mo('configImportP', {'name': 'Restore-Shop', 'fileName': 'ce2_Shop-Nightly-2026-10-26T23-00-00.tar.gz', 'importType': 'merge',
                             'importMode': 'atomic', 'adminSt': 'triggered'}, mo('configRsRemotePath', {'tnFileRemotePathName': 'SCP-Backup'}))
EXP25 = mo('configExportP', {'name': 'Fabric-Nightly', 'adminSt': 'triggered', 'includeSecureFields': 'yes'},
           mo('configRsRemotePath', {'tnFileRemotePathName': 'SCP-Backup'}))
lab(id='25-config-export-import', title='25 Config Export und Import', topic='Fabric-Betrieb', level='Fortgeschritten', duration='30 min',
    fabric='discovered',
    goals=['Eine Remote Location für SCP anlegen', 'Einen gelöschten Tenant per Import (Merge) aus dem Backup wiederherstellen',
           'Exporte mit AES-Verschlüsselung erstellen, damit Passwörter und Keys enthalten sind'],
    intro='Gestern Abend hat ein Kollege versehentlich den Tenant **Shop** gelöscht. Auf dem SCP-Server **192.168.10.50** (backup / Backup123!) '
          'liegt das nächtliche Backup **ce2_Shop-Nightly-2026-10-26T23-00-00.tar.gz** in `/backup`. Die Server web1 und app1 sind seitdem offline.\n\n'
          'Danach soll ein nächtlicher **Export der ganzen Fabric** eingerichtet werden – diesmal mit Passwörtern, also mit **Global AES Encryption** '
          '(Passphrase mindestens 16 Zeichen).',
    config=[SERVER_ACCESS], hosts=[WEB1, APP1],
    fileserver={'files': {'/backup/ce2_Shop-Nightly-2026-10-26T23-00-00.tar.gz': _backup25()}},
    tasks=[
        task('Remote Location', '**Admin > Import/Export > Remote Locations**: **SCP-Backup**, Host 192.168.10.50, SCP, Port 22, Pfad /backup, '
             'Benutzer backup, Management EPG **default (Out-of-Band)**.'),
        task('Import', '**Import Policies > Configuration**: **Restore-Shop**, Datei aus dem Backup, Import Type **Merge**, Mode **Atomic**, '
             'Remote Location SCP-Backup, *Start Now: Triggered*. Ergebnis unter **Jobs**.',
             'Replace würde alles, was nicht im Backup steht, im Zielbereich ersetzen – für einen einzelnen Tenant ist Merge der sichere Weg.'),
        task('Prüfen', 'web1 und app1 sind wieder gelernt, web1 → app1 tcp/8080 klappt.'),
        task('AES-Verschlüsselung', '**System Settings > Global AES Passphrase Encryption Settings** (oder Import/Export > Global AES Encryption): '
             'Encryption einschalten, Passphrase z. B. `Nightly-Backup#2026`.'),
        task('Export', '**Export Policies > Configuration**: **Fabric-Nightly**, Remote Location SCP-Backup, Include Secure Fields yes, sofort '
             'starten. Unter Simulation > Fileserver & Monitoring siehst du die Datei – jetzt *mit* Secure Properties.'),
    ],
    checks=[check('Import erfolgreich', 'job', kind='import'),
            check('Tenant Shop mit EPG Web ist zurück', 'exists', dn='uni/tn-Shop/ap-Webshop/epg-Web'),
            check('web1 → app1 tcp/8080', 'traffic', src='web1', dst='app1', proto='tcp', port=8080, expect=True),
            check('Global AES Encryption aktiv', 'exists', dn='uni/exportcryptkey', attrs={'strongEncryptionEnabled': 'yes'}),
            check('Export mit Secure Properties erfolgreich', 'job', kind='export', secure=True)],
    solution='`' + json.dumps(RL25) + '` unter uni/fabric, dann `' + json.dumps(IMP25) + '`; danach `uni/exportcryptkey` mit '
             'strongEncryptionEnabled=yes und Passphrase, zuletzt `' + json.dumps(EXP25) + '`.')

# ----------------------------------------------------------------------------
# Lab 26 - Monitoring: SNMP, Syslog, Callhome
# ----------------------------------------------------------------------------
OOB26 = mo('mgmtOoB', {'name': 'default'}, *[mo('mgmtRsOoBStNode', {'tDn': 'topology/pod-1/node-%d' % i, 'addr': '192.168.10.%d/24' % i,
                                                                    'gw': '192.168.10.254'}) for i in (101, 102, 103, 104, 201, 202)])
SNMP26 = mo('fabricInst', {},
            mo('snmpPol', {'name': 'default', 'adminSt': 'enabled', 'contact': 'noc@firma.de', 'loc': 'RZ Frankfurt'},
               mo('snmpCommunityP', {'name': 'NMS-Read'}),
               mo('snmpClientGrpP', {'name': 'NMS'}, mo('snmpRsEpg', {'tDn': 'uni/tn-mgmt/mgmtp-default/oob-default'}),
                  mo('snmpClientP', {'addr': '192.168.10.61'}))),
            mo('fabricFuncP', {}, mo('fabricPodPGrp', {'name': 'PodPol'}, mo('fabricRsSnmpPol', {'tnSnmpPolName': 'default'}))),
            mo('snmpGroup', {'name': 'NMS-Traps'}, mo('snmpTrapDest', {'host': '192.168.10.61', 'port': '162', 'ver': 'v2c', 'secName': 'NMS-Read'},
                                                     mo('snmpRsARemoteHostToEpg', {'tDn': 'uni/tn-mgmt/mgmtp-default/oob-default'}))),
            mo('syslogGroup', {'name': 'Syslog'}, mo('syslogRemoteDest', {'host': '192.168.10.60', 'severity': 'information'},
                                                     mo('fileRsARemoteHostToEpg', {'tDn': 'uni/tn-mgmt/mgmtp-default/oob-default'}))),
            mo('callhomeGroup', {'name': 'NOC-Mail'}, mo('callhomeProf', {'from': 'apic1@firma.de', 'contact': 'NOC'},
                                                         mo('callhomeSmtpServer', {'host': '192.168.10.62'},
                                                            mo('fileRsARemoteHostToEpg', {'tDn': 'uni/tn-mgmt/mgmtp-default/oob-default'}))),
               mo('callhomeDest', {'name': 'noc', 'email': 'noc@firma.de'})),
            mo('monCommonPol', {}, mo('syslogSrc', {'name': 'all', 'minSev': 'warning', 'incl': 'faults,audit'},
                                      mo('syslogRsDestGroup', {'tDn': 'uni/fabric/slgroup-Syslog'})),
               mo('snmpSrc', {'name': 'traps', 'minSev': 'minor', 'incl': 'faults'}, mo('snmpRsDestGroup', {'tDn': 'uni/fabric/snmpgroup-NMS-Traps'})),
               mo('callhomeSrc', {'minSev': 'major', 'incl': 'faults'}, mo('callhomeRsDestGroup', {'tDn': 'uni/fabric/chgroup-NOC-Mail'}))))
lab(id='26-monitoring-snmp-syslog', title='26 Monitoring: SNMP, Syslog und Callhome', topic='Fabric-Betrieb', level='Fortgeschritten',
    duration='40 min', fabric='discovered',
    goals=['SNMP-Polling mit Community und Client Group über die Pod Policy Group freigeben', 'Faults und Audit Logs per Syslog und SNMP-Trap senden',
           'Callhome-Mails für schwere Faults einrichten', 'Verstehen, warum Switches eine Management-Adresse brauchen'],
    intro='Das NOC will die Fabric überwachen. Im OOB-Netz 192.168.10.0/24 stehen: **Syslog** 192.168.10.60 (UDP 514), **SNMP-Manager** '
          '192.168.10.61 (Community **NMS-Read**, Traps auf 162) und der **Mailserver** 192.168.10.62. Die Switches haben noch keine '
          'Management-Adressen: leaf101 = 192.168.10.101 usw., Gateway 192.168.10.254.',
    config=[SERVER_ACCESS, shop_tenant(with_contracts=True)], hosts=[WEB1, APP1],
    tasks=[
        task('Management-Adressen', '**Tenant mgmt > Node Management Addresses**: Static Node Management Addresses für 101–104, 201, 202 '
             '(192.168.10.<Node-ID>/24, Gateway 192.168.10.254).'),
        task('SNMP-Polling', '**Fabric > Fabric Policies > Policies > Pod > SNMP**: Policy **default** aktivieren, Contact und Location, Community '
             '**NMS-Read**, Client Group mit Management EPG default (Out-of-Band) und Client **192.168.10.61**. Dann eine Pod Policy Group '
             '**PodPol** mit dieser SNMP Policy und im Pod Profile default zuweisen.',
             'Ohne Client Group beantwortet die ACI keine SNMP-Anfrage – auch mit richtiger Community nicht.'),
        task('Destination Groups', '**Admin > External Data Collectors > Monitoring Destinations**: Syslog-Gruppe **Syslog** (Ziel 192.168.10.60, '
             'Severity information), SNMP-Gruppe **NMS-Traps** (192.168.10.61:162, v2c, NMS-Read), Callhome-Gruppe **NOC-Mail** (From apic1@firma.de, '
             'SMTP 192.168.10.62, Ziel noc@firma.de). Jeweils Management EPG default (Out-of-Band).'),
        task('Sources', '**Fabric Policies > Policies > Monitoring > Common Policy**: Syslog Source (Faults und Audit, ab warning), '
             'SNMP Source (Faults ab minor), Callhome Source (Faults ab major) – jeweils mit ihrer Destination Group.',
             'Ohne Source sendet der APIC nichts, auch wenn die Destination Group fertig ist.'),
        task('Testen', 'Simulation > Fileserver & Monitoring: *snmpwalk* gegen apic1 und leaf101, dann einen Test-Fault **major** auslösen. '
             'Er muss beim Syslog-Server, beim SNMP-Manager und als Mail ankommen.'),
    ],
    checks=[check('SNMP-Walk auf apic1 mit NMS-Read', 'snmp', manager='snmp-nms', node='apic1', community='NMS-Read'),
            check('SNMP-Walk auf leaf101', 'snmp', manager='snmp-nms', node='leaf101', community='NMS-Read'),
            check('Syslog-Ziel erreichbar', 'mon', kind='syslog'),
            check('SNMP-Trap-Ziel erreichbar', 'mon', kind='snmp'),
            check('Callhome-Ziel erreichbar', 'mon', kind='smtp'),
            check('Syslog-Server hat einen Fault empfangen', 'received', collector='syslog-srv', contains='][raised]['),
            check('NOC-Mail angekommen', 'received', collector='mail-srv', contains='Mail an noc@firma.de')],
    solution='Management-Adressen: `' + json.dumps(OOB26) + '`\n\nFabric (uni): `' + json.dumps(SNMP26) + '`\n\nPod Profile: '
             '`uni/fabric/podprof-default/pods-default-typ-ALL/rspodPGrp` tDn=uni/fabric/funcprof/podpgrp-PodPol. Danach Test-Fault auslösen.')

# ----------------------------------------------------------------------------
# Lab 27 - DHCP Relay
# ----------------------------------------------------------------------------
DHCP27_ACC = access('VLAN-Pool-Office', 150, 169, 'PhysDom-Office', 'AAEP-Office', 'IPG-Office', 'IntProf-Office', 'Office-Ports', 11, 20,
                    'SwProf-Office', 101, 102)
OFFICE27 = mo('fvTenant', {'name': 'Office'}, mo('fvCtx', {'name': 'Corp'}),
              bd('BD-Clients', 'Corp', '10.50.0.1/24'), bd('BD-Services', 'Corp', '10.60.0.1/24'),
              contract('clients-to-services', ['icmp', 'default']),
              mo('fvAp', {'name': 'Office'},
                 epg('Clients', 'BD-Clients', dom='uni/phys-PhysDom-Office', ports=[(path(101, 'eth1/11'), 150), (path(102, 'eth1/11'), 150)],
                     cons=['clients-to-services']),
                 epg('Services', 'BD-Services', dom='uni/phys-PhysDom-Office', ports=[(path(102, 'eth1/12'), 160)], prov=['clients-to-services'])))
DHCP1 = dict(host('dhcp1', '00:50:56:60:00:10', '10.60.0.10/24', '10.60.0.1', 160, [[L102, 'eth1/12']], descr='DHCP-Server (Windows)'),
             dhcpd=[{'net': '10.50.0.0/24', 'from': '10.50.0.100', 'to': '10.50.0.199', 'gw': '10.50.0.1'}])
PC1 = dict(host('pc1', '00:50:56:50:00:21', '0.0.0.0/32', '', 150, [[L101, 'eth1/11']], descr='Büro-PC (DHCP)'), dhcp=True)
PC2 = dict(host('pc2', '00:50:56:50:00:22', '0.0.0.0/32', '', 150, [[L102, 'eth1/11']], descr='Büro-PC (DHCP)'), dhcp=True)
RELAY27 = mo('fvTenant', {'name': 'Office'},
             mo('dhcpRelayP', {'name': 'DHCP-Corp', 'owner': 'tenant'}, mo('dhcpRsProv', {'tDn': 'uni/tn-Office/ap-Office/epg-Services', 'addr': '10.60.0.10'})),
             mo('fvBD', {'name': 'BD-Clients'}, mo('dhcpLbl', {'name': 'DHCP-Corp', 'owner': 'tenant'})))
lab(id='27-dhcp-relay', title='27 DHCP Relay', topic='Tenant / Services', level='Mittel', duration='25 min', fabric='discovered',
    goals=['Eine DHCP Relay Policy mit Provider-EPG und Server-Adresse anlegen', 'Die Policy per DHCP Relay Label an die Client-BD hängen',
           'Mit show ip dhcp relay und dem Host-Status verifizieren'],
    intro='Im Tenant **Office** holen sich die Büro-PCs **pc1** und **pc2** (EPG Clients, BD-Clients 10.50.0.0/24) ihre Adresse per DHCP. '
          'Der DHCP-Server **dhcp1** (10.60.0.10) steht in der EPG **Services** (BD-Services) und hat einen Scope für 10.50.0.0/24. '
          'Noch bekommen die PCs keine Adresse – der DHCP Discover ist ein Broadcast und bleibt im BD.',
    config=[DHCP27_ACC, OFFICE27], hosts=[DHCP1, PC1, PC2],
    tasks=[
        task('Relay Policy', '**Tenant Office > Policies > Protocol > DHCP > Relay Policies**: **DHCP-Corp** mit Provider EPG **Services** und '
             'Server-Adresse **10.60.0.10**.'),
        task('Relay Label', 'Am **BD-Clients** unter *DHCP Relay Labels* das Label **DHCP-Corp** (Scope tenant) anlegen.',
             'Der Name des Labels muss genau dem Namen der Relay Policy entsprechen. Der Relay Agent nutzt das BD-Gateway 10.50.0.1 als giaddr.'),
        task('Verifizieren', 'Simulation > Topologie & Hosts: pc1 und pc2 haben eine Adresse aus 10.50.0.100–199. Auf leaf101 '
             '`show ip dhcp relay`. Traffic-Test pc1 → dhcp1.'),
    ],
    checks=[check('pc1 hat ein DHCP-Lease', 'dhcp', host='pc1'), check('pc2 hat ein DHCP-Lease', 'dhcp', host='pc2'),
            check('pc1 erreicht dhcp1', 'traffic', src='pc1', dst='dhcp1', expect=True)],
    solution='`' + json.dumps(RELAY27) + '`')

# ----------------------------------------------------------------------------
# Lab 28 - Loop Protection mit MCP und QoS
# ----------------------------------------------------------------------------
SHOP28 = shop_tenant(with_contracts=True)
SHOP28['fvTenant']['children'][-3]['fvAp']['children'][0]['fvAEPg']['children'] += [
    mo('fvRsPathAtt', {'tDn': path(101, 'eth1/9'), 'encap': 'vlan-110'}), mo('fvRsPathAtt', {'tDn': path(102, 'eth1/9'), 'encap': 'vlan-110'})]
CAT28 = {'name': 'cat-lager', 'links': [[L101, 'eth1/9'], [L102, 'eth1/9']], 'bond': 'none', 'vlans': '', 'descr': 'alter Catalyst im Lager'}
MCP28 = mo('mcpInstPol', {'adminSt': 'enabled', 'key': 'Mcp#Fabric2026', 'ctrl': 'pdu-per-vlan', 'loopProtectAct': 'port-disable'})
lab(id='28-mcp-loop-qos', title='28 Loop Protection mit MCP und QoS-Klassen', topic='Fabric-Betrieb', level='Fortgeschritten', duration='30 min',
    fabric='discovered',
    goals=['Eine Layer-2-Schleife über einen Legacy-Switch erkennen', 'MCP global mit Key und PDU per VLAN aktivieren', 'Endpoint Loop Protection '
           'als zweite Verteidigungslinie kennen', 'EPGs einer QoS-Klasse zuordnen'],
    intro='Die Lager-IT hat einen alten Catalyst **cat-lager** mit zwei Kabeln an **leaf101 eth1/9** und **leaf102 eth1/9** gesteckt – ohne '
          'Port-Channel. Beide Ports liegen in der EPG **Web** (vlan-110). Seitdem ist der Webshop gestört: Broadcast-Storm im BD-Web, '
          'die MACs springen zwischen den Ports.\n\nMCP ist global noch aus. Danach soll die EPG **App** die QoS-Klasse **Level2** bekommen.',
    config=[SERVER_ACCESS, SHOP28], hosts=[WEB1, APP1], switches=[CAT28],
    tasks=[
        task('Analyse', 'Faults ansehen (S2534 am BD), Traffic-Test web1 → app1, auf leaf101 `show mcp internal info interface all`. '
             'Simulation > Legacy-Switches zeigt die Schleife.'),
        task('MCP aktivieren', '**Fabric > Access Policies > Policies > Global > MCP Instance Policy default**: Admin State enabled, Key '
             '`Mcp#Fabric2026`, Loop Protection Action Port Disable.',
             'Ohne *Enable MCP PDU per VLAN* sendet MCP nur untagged – die Schleife in vlan-110 bleibt unentdeckt.'),
        task('PDU per VLAN', 'In derselben Policy **Enable MCP PDU per VLAN** aktivieren. Jetzt error-disabled MCP einen der Ports '
             '(`show interface status err-disabled`).'),
        task('Endpoint Loop Protection', '**System Settings > Endpoint Controls**: Ep Loop Protection aktivieren (Action Port Disable) – '
             'als Absicherung, falls MCP auf einem Port fehlt.'),
        task('QoS', 'EPG **App**: QoS Class **Level2**. Auf einem Leaf `show qos classes`.'),
    ],
    checks=[check('Schleife durch MCP gebrochen', 'loop', switch='cat-lager', action='mcp'),
            check('MCP mit PDU per VLAN aktiv', 'exists', dn='uni/infra/mcpInstP-default', attrs={'adminSt': 'enabled', 'ctrl': 'pdu-per-vlan'}),
            check('Endpoint Loop Protection aktiv', 'exists', dn='uni/infra/epLoopProtectP-default', attrs={'adminSt': 'enabled'}),
            check('web1 → app1 tcp/8080 wieder erreichbar', 'traffic', src='web1', dst='app1', proto='tcp', port=8080, expect=True),
            check('EPG App in QoS-Klasse Level2', 'exists', dn='uni/tn-Shop/ap-Webshop/epg-App', attrs={'prio': 'level2'})],
    solution='`uni/infra/mcpInstP-default`: `' + json.dumps(MCP28) + '`, `uni/infra/epLoopProtectP-default` adminSt=enabled, '
             'EPG App prio=level2.')


# ----------------------------------------------------------------------------
# Lab 29 - Multi-Pod
# ----------------------------------------------------------------------------
POD2_ACC = access('VLAN-Pool-Server', 100, 199, 'PhysDom-Server', 'AAEP-Server', 'IPG-Server-Access',
                  'IntProf-Leaf105-106', 'Server-Ports-Pod2', 1, 10, 'SwProf-Leaf105-106', 105, 106)
APP2 = host('app1', '00:50:56:10:20:11', '10.10.20.11/24', '10.10.20.1', 120, [['SAL1931LA05', 'eth1/2']], descr='Applikationsserver in Pod 2')
SHOP29 = shop_tenant(with_contracts=True)
SHOP29['fvTenant']['children'][-3]['fvAp']['children'][1]['fvAEPg']['children'][2] = mo('fvRsPathAtt', {'tDn': 'topology/pod-2/paths-105/pathep-[eth1/2]', 'encap': 'vlan-120'})


def ipn_router(name, pod, kind, ifs, mtu=9150, relay=(), pim=True):
    return {'name': name, 'pod': pod, 'kind': kind, 'mtu': mtu, 'area': '0.0.0.0', 'pim': pim, 'rp': '192.168.100.1' if pim else '', 'relay': list(relay),
            'down': False, 'ifs': [{'serial': s_, 'port': p_, 'vlan': 4, 'ip': ip} for s_, p_, ip in ifs]}


IPN_IFS1 = [('FDO2219SP01', 'eth1/32', '192.168.1.2/30'), ('FDO2219SP02', 'eth1/32', '192.168.1.6/30')]
IPN_IFS2 = [('FDO2219SP03', 'eth1/32', '192.168.2.2/30'), ('FDO2219SP04', 'eth1/32', '192.168.2.6/30')]
WAN_IFS = [('SAL1931RL01', 'eth1/54', '192.168.3.2/30')]


def mp_lif(nid, pod, port, ip):
    return mo('l3extLIfP', {'name': 'ipn-%d' % nid}, mo('ospfIfP', {}),
              mo('l3extRsPathL3OutAtt', {'tDn': 'topology/pod-%d/paths-%d/pathep-[%s]' % (pod, nid, port), 'ifInstT': 'sub-interface',
                                         'encap': 'vlan-4', 'addr': ip}))


def mp_l3out(spines):
    return mo('fvTenant', {'name': 'infra'}, mo('l3extOut', {'name': 'multipod'}, mo('l3extRsEctx', {'tnFvCtxName': 'overlay-1'}),
                                                mo('ospfExtP', {'areaId': '0.0.0.0'}), mo('bgpExtP', {}),
                                                mo('l3extLNodeP', {'name': 'spines'},
                                                   *[mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-%d/node-%d' % (pod, n), 'rtrId': '%d.%d.%d.%d' % (n, n, n, n)})
                                                     for n, pod, _ in spines],
                                                   *[mp_lif(n, pod, 'eth1/32', ip) for n, pod, ip in spines])))


EXT29 = mo('fvTenant', {'name': 'infra'}, mo('fabricExtConnP', {'id': '1', 'name': 'Multipod'}, mo('fabricPeeringP', {'type': 'automatic_with_full_mesh'}),
                                             mo('fabricPodConnP', {'id': '1'}, mo('fabricIp', {'addr': '172.16.1.1/32'})),
                                             mo('fabricPodConnP', {'id': '2'}, mo('fabricIp', {'addr': '172.16.2.1/32'}))))
SPINES29 = [(201, 1, '192.168.1.1/30'), (202, 1, '192.168.1.5/30'), (203, 2, '192.168.2.1/30'), (204, 2, '192.168.2.5/30')]
lab(id='29-multipod', title='29 Multi-Pod mit Inter-Pod Network', topic='Fabric-Architektur', level='Experte', duration='50 min',
    fabric='discovered', topology='multipod',
    ipn={'routers': [ipn_router('ipn1', 1, 'ipn', IPN_IFS1), ipn_router('ipn2', 2, 'ipn', IPN_IFS2, mtu=1500),
                     ipn_router('wan-rl', 1, 'wan', WAN_IFS, pim=False)]},
    goals=['Einen zweiten Pod über ein IPN an die Fabric anbinden', 'Die Anforderungen an das IPN kennen: vlan-4, OSPF, MTU, PIM Bidir, DHCP Relay',
           'Infra-L3Out, Pod TEP Pool und Fabric External Connection Policy einrichten', 'Pod-2-Switches registrieren und Verkehr zwischen den Pods prüfen'],
    intro='Das zweite Rechenzentrum wird als **Pod 2** angebunden: spine203/204 und leaf105/106 hängen am IPN-Router **ipn2**, Pod 1 (spine201/202) an '
          '**ipn1**. Die Spines nutzen jeweils **eth1/32** zum IPN.\n\n**Design:** TEP Pool Pod 2 **10.1.0.0/16**, OSPF Area 0, Sub-Interfaces vlan-4: '
          'spine201 192.168.1.1/30, spine202 192.168.1.5/30, spine203 192.168.2.1/30, spine204 192.168.2.5/30 (die IPN-Seite hat jeweils .2/.6). '
          'Data Plane TEP Pod 1 **172.16.1.1/32**, Pod 2 **172.16.2.1/32**.\n\napp1 steht jetzt in Pod 2 an leaf105 eth1/2 (EPG App, vlan-120).',
    config=[SERVER_ACCESS, POD2_ACC, SHOP29], hosts=[WEB1, APP2],
    tasks=[
        task('Infra-L3Out', 'Im Tenant **infra** ein L3Out **multipod** (VRF overlay-1, OSPF Area 0, BGP) mit allen vier Spines und ihren Sub-Interfaces '
             'anlegen – am schnellsten über **Fabric > Inventory > Quick Start > Add Pod**. Unter Simulation > IPN & WAN wird ipn1 FULL.'),
        task('Pod TEP Pool', '**Pod Fabric Setup Policy**: Pod 2 mit 10.1.0.0/16 (macht der Add-Pod-Wizard mit).'),
        task('DHCP Relay im IPN', 'Simulation > IPN & WAN: auf **ipn1 und ipn2** das DHCP Relay auf die TEP-Adresse des APIC setzen. Danach erscheinen '
             'spine203/204 unter *Nodes Pending Registration*.', 'Ohne Relay kommt der DHCP Discover der Pod-2-Spines nie beim APIC an.'),
        task('Registrieren', 'spine203 (203), spine204 (204), leaf105 (105), leaf106 (106) – jeweils **Pod ID 2**.'),
        task('IPN-Fehler finden', 'Die Pod-2-Spines kommen nicht auf FULL. `show ip ospf neighbors vrf overlay-1` auf spine203 und die Simulation zeigen '
             'warum. Auf ipn2 die richtige MTU (9150) setzen.', 'Erst danach sind leaf105/106 vom APIC aus erreichbar.'),
        task('Data Plane TEP', 'Fabric External Connection Policy (Tenant infra) mit Pod Connection Profiles für Pod 1 und 2 prüfen.'),
        task('Verkehr', 'Traffic-Test web1 (Pod 1) → app1 (Pod 2) tcp/8080.'),
    ],
    checks=[check('spine203 aktiv', 'node', serial='FDO2219SP03', id=203), check('spine204 aktiv', 'node', serial='FDO2219SP04', id=204),
            check('leaf105 aktiv', 'node', serial='SAL1931LA05', id=105), check('leaf106 aktiv', 'node', serial='SAL1931LA06', id=106),
            check('Alle Spines mit OSPF FULL zum IPN', 'ipnadj', serials=['FDO2219SP01', 'FDO2219SP02', 'FDO2219SP03', 'FDO2219SP04']),
            check('web1 → app1 tcp/8080 über das IPN', 'traffic', src='web1', dst='app1', proto='tcp', port=8080, expect=True, via='Multi-Pod')],
    solution='Infra (uni): `' + json.dumps(mp_l3out(SPINES29)) + '` und `' + json.dumps(EXT29) + '`, `uni/controller/setuppol` mit '
             '`fabricSetupP podId=2 tepPool=10.1.0.0/16`. Im IPN: Relay 10.0.0.1 auf ipn1/ipn2, MTU von ipn2 auf 9150. Registrierung mit podId=2.')

# ----------------------------------------------------------------------------
# Lab 30 - Remote Leaf
# ----------------------------------------------------------------------------
RL_ACC = access('VLAN-Pool-Store', 110, 110, 'PhysDom-Store', 'AAEP-Store', 'IPG-Store', 'IntProf-Leaf301', 'Store-Ports', 1, 10,
                'SwProf-Leaf301', 301, 301)
STORE1 = host('store1', '00:50:56:30:01:11', '10.10.10.31/24', '10.10.10.1', 110, [['SAL1931RL01', 'eth1/1']], descr='Kassensystem in der Filiale')
SPINES30 = [(201, 1, '192.168.1.1/30'), (202, 1, '192.168.1.5/30')]
EXT30 = mo('fvTenant', {'name': 'infra'}, mo('fabricExtConnP', {'id': '1', 'name': 'Multipod'},
                                             mo('fabricPodConnP', {'id': '1'}, mo('fabricIp', {'addr': '172.16.1.1/32'}))))
RLSOL30 = [['uni/controller/setuppol/setupp-1', mo('fabricSetupP', {}, mo('fabricExtSetupP', {'remoteId': '11', 'tepPool': '10.11.0.0/20'}))],
           ['uni/tn-infra/fabricExtConnP-1/podConnP-1', mo('fabricPodConnP', {}, mo('fabricExtRoutablePodSubnet', {'pool': '172.16.10.0/24'}))],
           ['#ipn', {'name': 'wan-rl', 'mtu': 9150, 'relay': '10.0.0.1'}],
           ['uni/controller/nodeidentpol', mo('fabricNodeIdentP', {'serial': 'SAL1931RL01', 'nodeId': '301', 'name': 'leaf301', 'podId': '1',
                                                                    'nodeType': 'remote-leaf-wan', 'extPoolId': '11'})],
           ['uni/tn-infra/out-multipod', mo('l3extOut', {}, mo('l3extLNodeP', {'name': 'remote-leaf-301'},
                                                                mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-301', 'rtrId': '30.30.30.30'}),
                                                                mp_lif(301, 1, 'eth1/54', '192.168.3.1/30')))],
           ['uni', RL_ACC],
           ['uni/tn-Shop/ap-Webshop/epg-Web', mo('fvAEPg', {}, mo('fvRsDomAtt', {'tDn': 'uni/phys-PhysDom-Store'}),
                                                   mo('fvRsPathAtt', {'tDn': 'topology/pod-1/paths-301/pathep-[eth1/1]', 'encap': 'vlan-110'}))]]
lab(id='30-remote-leaf', title='30 Remote Leaf in der Filiale', topic='Fabric-Architektur', level='Experte', duration='40 min',
    fabric='discovered', topology='multipod',
    ipn={'routers': [ipn_router('ipn1', 1, 'ipn', IPN_IFS1, relay=['10.0.0.1']), ipn_router('ipn2', 2, 'ipn', IPN_IFS2, relay=['10.0.0.1']),
                     ipn_router('wan-rl', 1, 'wan', WAN_IFS, mtu=1500, pim=False)]},
    goals=['Ein Remote Leaf über ein WAN an Pod 1 anbinden', 'Remote Pool, External TEP Pool und Registrierung als remote-leaf-wan',
           'Uplink des Remote Leafs im Infra-L3Out und die Anforderungen an den WAN-Router'],
    intro='In der Filiale steht **leaf301** (Serial SAL1931RL01), sein Uplink eth1/54 hängt am WAN-Router **wan-rl** (192.168.3.2/30, vlan-4). '
          'Pod 1 ist bereits über das Infra-L3Out **multipod** mit dem IPN verbunden.\n\n**Design:** Remote ID **11**, Remote Pool **10.11.0.0/20**, '
          'External TEP Pool **172.16.10.0/24**, Uplink leaf301 **192.168.3.1/30**, Router ID 30.30.30.30. Das Kassensystem **store1** '
          '(10.10.10.31, vlan-110 an leaf301 eth1/1) soll in der EPG **Web** landen.',
    config=[SERVER_ACCESS, shop_tenant(with_contracts=True), mp_l3out(SPINES30), EXT30], hosts=[WEB1, APP1, STORE1],
    tasks=[
        task('Remote Pool und External TEP', '**Fabric > Inventory > Quick Start > Add Remote Leaf** oder von Hand: Remote Pool 11 / 10.11.0.0/20 in der Pod '
             'Fabric Setup Policy, External TEP Pool 172.16.10.0/24 im Pod Connection Profile 1 der Fabric External Connection Policy.'),
        task('WAN-Router', 'Simulation > IPN & WAN: auf **wan-rl** das DHCP Relay zum APIC (10.0.0.1) eintragen.'),
        task('Registrieren', 'leaf301 als **Remote Leaf** (Node Type remote-leaf-wan, Remote Pool ID 11, Node ID 301) registrieren.'),
        task('Uplink', 'Im Infra-L3Out **multipod** ein Node Profile für Node 301 mit Sub-Interface eth1/54, vlan-4, 192.168.3.1/30 und OSPF.',
             'Ohne OSPF zum WAN-Router bleibt der Remote Leaf in Discovery.'),
        task('Access Policies und EPG', 'Access Policies für leaf301 Port 1/1 (vlan-110, eigene Domain PhysDom-Store) und einen Static Port in der EPG Web.'),
        task('Verkehr', 'store1 → app1 tcp/8080. Klappt es nicht, die Meldung im Traffic-Test lesen und den WAN-Router prüfen.',
             'VXLAN braucht mehr als 1500 Byte MTU im WAN.'),
    ],
    checks=[check('leaf301 als Remote Leaf aktiv', 'node', serial='SAL1931RL01', id=301),
            check('OSPF FULL zum WAN-Router', 'ipnadj', serials=['SAL1931RL01']),
            check('store1 in EPG Web gelernt', 'endpoint', host='store1', epg='uni/tn-Shop/ap-Webshop/epg-Web'),
            check('store1 → app1 tcp/8080', 'traffic', src='store1', dst='app1', proto='tcp', port=8080, expect=True)],
    solution='Siehe Add-Remote-Leaf-Wizard; Objekte: fabricExtSetupP remoteId=11 tepPool=10.11.0.0/20, fabricExtRoutablePodSubnet 172.16.10.0/24, '
             'fabricNodeIdentP nodeType=remote-leaf-wan extPoolId=11, Node Profile mit `' + json.dumps(mp_lif(301, 1, 'eth1/54', '192.168.3.1/30')) +
             '`. Auf wan-rl: Relay 10.0.0.1 und MTU 9150.')


# ----------------------------------------------------------------------------
# Lab 31 - Multi-Site mit dem Nexus Dashboard Orchestrator
# ----------------------------------------------------------------------------
TPL31A = {'name': 'Shop-Stretched', 'tenant': 'Shop', 'sites': ['local', 'DC-HAM'], 'vrfs': ['Prod'],
          'bds': [{'name': 'BD-Web', 'vrf': 'Prod', 'subnet': '10.10.10.1/24', 'l2stretch': True, 'bum': False}],
          'aps': [{'name': 'Webshop', 'epgs': [{'name': 'Web', 'bd': 'BD-Web', 'cons': ['web-to-ham'], 'prov': []}]}],
          'contracts': [{'name': 'web-to-ham', 'filter': 'tcp/8080,icmp'}]}
TPL31B = {'name': 'HAM-Local', 'tenant': 'Shop', 'sites': ['DC-HAM'], 'vrfs': [],
          'bds': [{'name': 'BD-HAM-App', 'vrf': 'Prod', 'subnet': '10.20.20.1/24', 'l2stretch': False, 'bum': False}],
          'aps': [{'name': 'Webshop', 'epgs': [{'name': 'App-HAM', 'bd': 'BD-HAM-App', 'cons': [], 'prov': ['web-to-ham']}]}],
          'contracts': []}
INFRA31 = {'area': '0.0.0.0', 'ucastTep': '172.16.100.1/32', 'peering': 'full-mesh',
           'spines': [{'node': 201, 'port': 'eth1/31', 'ip': '10.255.1.1/30', 'evpnRid': '10.255.255.201'},
                      {'node': 202, 'port': 'eth1/31', 'ip': '10.255.1.5/30', 'evpnRid': '10.255.255.202'}]}
ISN31 = {'routers': [{'name': 'isn1', 'pod': 1, 'kind': 'isn', 'mtu': 1500, 'area': '0.0.0.0', 'pim': False, 'rp': '', 'relay': [], 'down': False,
                      'ifs': [{'serial': 'FDO2219SP01', 'port': 'eth1/31', 'vlan': 4, 'ip': '10.255.1.2/30'},
                              {'serial': 'FDO2219SP02', 'port': 'eth1/31', 'vlan': 4, 'ip': '10.255.1.6/30'}]}]}
lab(id='31-multisite-ndo', title='31 Multi-Site mit dem Nexus Dashboard Orchestrator', topic='Fabric-Architektur', level='Experte', duration='45 min',
    fabric='discovered', topology='multisite', ipn=ISN31,
    goals=['Den lokalen APIC im NDO onboarden und eine Site ID vergeben', 'Die Infra zwischen den Sites einrichten: ISN, OSPF, BGP EVPN, Overlay Unicast TEP',
           'Objekte über Templates zwischen den Sites strecken und site-lokal deployen', 'Verstehen, was der NDO im APIC anlegt (annotation orchestrator:msc)'],
    intro='Die Fabric in Frankfurt (dieser APIC) wird mit der Fabric **DC-HAM** (Site ID 2, schon im NDO) zu einer Multi-Site-Umgebung. Die Spines hängen mit '
          '**eth1/31** am Intersite Network **isn1** (10.255.1.2 und .6, vlan-4). Der NDO steht unter **Simulation > Multi-Site (NDO)**.\n\n'
          '**Design:** Site ID **1**, OSPF Area 0, spine201 **10.255.1.1/30** (BGP-EVPN Router-ID 10.255.255.201), spine202 **10.255.1.5/30** '
          '(10.255.255.202), Overlay Unicast TEP **172.16.100.1/32**.\n\nIn DC-HAM laufen **ham-web1** (10.10.10.51, EPG Web) und **ham-app1** '
          '(10.20.20.51, EPG App-HAM).',
    config=[SERVER_ACCESS, shop_tenant(with_contracts=True)], hosts=[WEB1, APP1],
    tasks=[
        task('Site onboarden', 'Im NDO den lokalen APIC mit admin und dem APIC-Passwort hinzufügen, Site ID **1**.'),
        task('Infra', 'Infra Configuration: OSPF Area, Spine-Interfaces zum ISN mit IP und BGP-EVPN Router-ID, Overlay Unicast TEP. **Deploy**. '
             'Danach im APIC: Tenant infra > L3Out **intersite** und die Site ID in der Fabric External Connection Policy.'),
        task('ISN', 'Die Spines kommen nicht auf OSPF FULL zum ISN. Ursache unter Simulation > IPN & WAN bzw. `show ip ospf neighbors vrf overlay-1` '
             'auf spine201 finden und am ISN beheben.', 'VXLAN zwischen den Sites braucht Jumbo Frames.'),
        task('Template Shop-Stretched', 'Schema mit Template **Shop-Stretched** (Tenant Shop, Sites lokal und DC-HAM): VRF Prod, BD-Web 10.10.10.1/24 mit '
             '**L2 Stretch**, AP Webshop mit EPG Web (konsumiert web-to-ham), Contract **web-to-ham** (tcp/8080, icmp). Deployen.'),
        task('Template HAM-Local', 'Template **HAM-Local** nur für DC-HAM: BD-HAM-App 10.20.20.1/24 (VRF Prod), EPG App-HAM stellt web-to-ham bereit. Deployen.'),
        task('Prüfen', 'Traffic-Test web1 → ham-web1 (gleiches Subnetz, L2 über das ISN) und web1 → ham-app1 tcp/8080. Im APIC sind Tenant, BD und EPG jetzt '
             'mit annotation orchestrator:msc markiert.'),
    ],
    checks=[check('Infra zwischen den Sites ok', 'msite'),
            check('web1 → ham-web1 (L2 gestreckt)', 'traffic', src='web1', dst='ham-web1', expect=True, via='ISN'),
            check('web1 → ham-app1 tcp/8080', 'traffic', src='web1', dst='ham-app1', proto='tcp', port=8080, expect=True, via='ISN'),
            check('web1 → ham-app1 tcp/22 blockiert', 'traffic', src='web1', dst='ham-app1', proto='tcp', port=22, expect=False)],
    solution='NDO: onboard (Site ID 1), Infra `' + json.dumps(INFRA31) + '`, Deploy Infra; ISN-MTU auf 9150; Templates `' + json.dumps(TPL31A) +
             '` und `' + json.dumps(TPL31B) + '` deployen.')


# ----------------------------------------------------------------------------
# Lab 32 - Abnahmefall: HTTPS mit Least Privilege (neues Lab-Format)
#   Anforderungen statt Klick-Anleitung, gestufte Hinweise, Pruefungsmodus,
#   Bewertung getrennt nach Funktion und Sicherheit, Verstaendnisfragen.
# ----------------------------------------------------------------------------
WEB32 = dict(WEB1, services=['tcp/22'])
APP32 = dict(APP1, services=['tcp/22', 'tcp/443'])
SOL32 = mo('fvTenant', {'name': 'Shop'},
           filt('https', {'name': 'https', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '443', 'dToPort': '443'}),
           contract('web-to-app-https', ['https']),
           mo('fvAp', {'name': 'Webshop'},
              mo('fvAEPg', {'name': 'Web'}, mo('fvRsCons', {'tnVzBrCPName': 'web-to-app-https'})),
              mo('fvAEPg', {'name': 'App'}, mo('fvRsProv', {'tnVzBrCPName': 'web-to-app-https'}))))

lab(id='32-https-least-privilege', title='32 Least Privilege: HTTPS von WEB zu APP', topic='Policy / Contracts', level='Einstieg',
    duration='25 min', fabric='discovered', kind='requirements', modes=['guided', 'exam'],
    prerequisites=['Lab 03: Tenant, VRF, Bridge Domain und EPG anlegen können'],
    tools=['Traffic-Test (Operations > Visibility & Troubleshooting oder Simulation > Testmatrix)',
           'Tenant-Konfiguration per GUI, REST-API oder Ansible',
           'CLI auf dem Leaf: show zoning-rule, show endpoint'],
    goals=['Implicit Deny zwischen EPGs vom Routing unterscheiden', 'Filter, Contract und Subject passend zur Anforderung bauen',
           'Consumer und Provider aus der Verbindungsrichtung ableiten', 'Least Privilege prüfen: auch was blockiert sein muss'],
    intro='Der Tenant **Shop** läuft: VRF **Prod**, die Bridge Domains **BD-Web** (10.10.10.1/24) und **BD-App** (10.10.20.1/24) '
          'mit Unicast Routing, das Application Profile **Webshop** mit den EPGs **Web** und **App**. Die Access Policies sind fertig, '
          '**web1** (10.10.10.11, leaf101 eth1/1, VLAN 110) und **app1** (10.10.20.11, leaf102 eth1/2, VLAN 120) sind gelernt. '
          'Auf app1 laufen HTTPS (tcp/443) und SSH (tcp/22), auf web1 SSH.\n\n'
          'Teste zuerst den Ausgangszustand mit dem Traffic-Test: **web1 → app1, TCP 443**. Woran scheitert er – und woran nicht?',
    requirements=['web1 kann HTTPS-Verbindungen (TCP 443) zu app1 aufbauen.',
                  'Sonst ist von Web nach App nichts erlaubt: kein SSH, kein Ping, keine anderen Ports (Least Privilege).',
                  'App kann von sich aus keine Verbindungen zu Web aufbauen.',
                  'Access Policies, Bridge Domains und Routing bleiben unverändert.'],
    limits=['Contracts sind wie in ACI zustandslos: Auch die Antwort braucht eine passende Regel. '
            'Die Filter-Option Stateful erlaubt vom Provider zum Consumer nur TCP mit ACK (keine Prüfung von Sequenznummern).',
            'Subjects ohne "Apply Both Directions" (vzInTerm/vzOutTerm) werden noch nicht unterstützt.',
            'Ob auf einem Host ein Dienst läuft, ist ein simulator-spezifisches Modell (Feld Dienste am Host).',
            'ICMP wird nicht nach Type/Code unterschieden.'],
    hints=['**Konzept:** Zwischen Endpoints in verschiedenen EPGs gilt in ACI ohne Freigabe *Implicit Deny* (Whitelist-Modell). '
           'Das Routing zwischen BD-Web und BD-App ist bereits da – es fehlt etwas anderes.',
           '**Beteiligte Objekte:** Ein *Filter* beschreibt den Verkehr, ein *Contract* mit *Subject* fasst Filter zusammen, und die '
           'EPGs hängen als *Consumer* bzw. *Provider* am Contract. Alles liegt im Tenant Shop.',
           '**Prüfschritt:** Im Traffic-Test web1 → app1 tcp/443 den Schritt *Policy Anfrage* lesen und auf leaf102 '
           '`show zoning-rule` ansehen. Wer baut die Verbindung auf? Diese EPG ist Consumer. Wer bietet den Dienst an? '
           'Diese EPG ist Provider. Danach SSH und Ping testen – die müssen weiter blockiert sein.',
           '**Lösung:** Filter **https** (EtherType IP, Protokoll tcp, Destination Port 443) → Contract **web-to-app-https** '
           '(Scope VRF) mit einem Subject, das den Filter enthält (Reverse Filter Ports an) → EPG **Web** konsumiert, EPG **App** '
           'stellt bereit. Die Antwort von app1 (Quell-Port 443) kommt über die umgekehrte Regel des Subjects zurück. Ein Filter '
           'mit Protokoll *unspecified* oder ein Contract mit dem Filter *default* aus common würde zwar funktionieren, öffnet aber '
           'alles und fällt durch die Least-Privilege-Prüfung.'],
    cause='Im Ausgangszustand gibt es zwischen den EPGs Web und App keinen Contract. Endpoint Learning, Gateway und Routing sind in '
          'Ordnung – der Traffic-Test endet mit POLICY_IMPLICIT_DENY im Schritt *Policy Anfrage*.',
    config=[SERVER_ACCESS, shop_tenant()], hosts=[WEB32, APP32], tasks=[],
    checks=[check('web1 → app1 HTTPS (TCP 443) funktioniert', 'traffic', src='web1', dst='app1', proto='tcp', port=443, expect=True),
            check('web1 erreicht weiterhin sein Gateway (Routing unverändert)', 'traffic', src='web1', dst='10.10.10.1', proto='icmp', expect=True),
            check('web1 → app1 SSH (TCP 22) ist durch die Policy blockiert', 'traffic', src='web1', dst='app1', proto='tcp', port=22,
                  expect=False, reason='POLICY_', category='security'),
            check('web1 → app1 Ping ist durch die Policy blockiert', 'traffic', src='web1', dst='app1', proto='icmp',
                  expect=False, reason='POLICY_', category='security'),
            check('app1 → web1 TCP 443: App baut keine Verbindung auf', 'traffic', src='app1', dst='web1', proto='tcp', port=443,
                  expect=False, reason='POLICY_', category='security'),
            check('Least Privilege Web → App: nur tcp/443 offen', 'exposure', src='web1', dst='app1', allow=['tcp/443'], category='security'),
            check('Least Privilege App → Web: keine neuen Verbindungen', 'exposure', src='app1', dst='web1', allow=[], category='security')],
    questions=[{'id': 'q1', 'q': 'Warum schlug HTTPS im Ausgangszustand fehl, obwohl das Routing zwischen BD-Web und BD-App funktioniert?',
                'options': ['Es fehlte eine Route zwischen den Subnetzen', 'Zwischen zwei EPGs gilt ohne Contract Implicit Deny',
                            'Der Dienst auf app1 lief nicht', 'Das VLAN von web1 war nicht im VLAN-Pool'],
                'answer': 1, 'explain': 'Routing und Policy sind in ACI getrennte Entscheidungen. Der Traffic-Test zeigt Gateway und Routing grün '
                                        'und scheitert erst an der Policy (Implicit Deny).'},
               {'id': 'q2', 'q': 'Welche EPG ist für diesen Contract der Provider?',
                'options': ['Web, weil sie die Verbindung aufbaut', 'App, weil sie den Dienst anbietet',
                            'Beide, sonst gibt es keinen Rückverkehr', 'Keine – die Rolle spielt keine Rolle'],
                'answer': 1, 'explain': 'Der Provider bietet den Dienst an (Ziel-Port 443), der Consumer baut die Verbindung auf. Vertauschte Rollen '
                                        'erlauben die Anfrage nicht.'},
               {'id': 'q3', 'q': 'Wie kommt die Antwort von app1 (Quell-Port 443) zurück zu web1, obwohl Contracts zustandslos sind?',
                'options': ['Über die Regel für die Gegenrichtung, die Quell- und Ziel-Port des Filters vertauscht',
                            'App darf damit selbst Verbindungen zu Web auf Ziel-Port 443 aufbauen',
                            'Der Contract arbeitet wie eine Stateful Firewall',
                            'Gar nicht – Antworten sind in ACI immer erlaubt'],
                'answer': 0, 'explain': 'Das Subject erzeugt bei "Apply Both Directions" mit "Reverse Filter Ports" eine Regel Provider → Consumer '
                                        'mit vertauschten Ports. Dadurch passt die Antwort (Quell-Port 443). Ohne die Option kommt die Anfrage '
                                        'durch, die Antwort nicht.'}],
    solution='Filter, Contract und Rollen (POST auf `uni/tn-Shop`):\n\n`' + json.dumps(SOL32) + '`\n\n'
             'Gleichwertig sind z. B.: Contract-Scope *tenant* statt *VRF*, der Filter im Tenant *common*, die Filter-Option *Stateful*, '
             'ein Port-Bereich 443-443. Nicht gleichwertig: Filter ohne Protokoll, Filter *default*, Port-Bereiche über 443 hinaus, vertauschte '
             'Rollen, Reverse Filter Ports aus.')


# ----------------------------------------------------------------------------
# Maschinenlesbare Musterloesungen (fuer die Tests: [URL-DN, Body])
# ----------------------------------------------------------------------------
BGP_RR = ['uni/fabric/bgpInstP-default', mo('bgpInstPol', {}, mo('bgpAsP', {'asn': '65001'}),
                                            mo('bgpRRP', {}, mo('bgpRRNodePEp', {'id': '201'}), mo('bgpRRNodePEp', {'id': '202'})))]
SOLUTIONS = {
    '00-day0-apic-setup': [['#setup', SETUP00]] + [['uni/controller/nodeidentpol', mo('fabricNodeIdentP', {'serial': s_, 'nodeId': str(i), 'name': n})]
                                                   for s_, i, n in [(L101, 101, 'leaf101'), (L102, 102, 'leaf102')]],
    '01-fabric-discovery': [['uni/controller/nodeidentpol', mo('fabricNodeIdentP', {'serial': s_, 'nodeId': str(i), 'name': n})]
                            for s_, i, n in [(L101, 101, 'leaf101'), (L102, 102, 'leaf102'), ('FDO2219SP01', 201, 'spine201'),
                                             ('FDO2219SP02', 202, 'spine202'), (L103, 103, 'leaf103'), (L104, 104, 'leaf104')]] + [BGP_RR],
    '02-access-policies': [['uni', SERVER_ACCESS]],
    '03-tenant-epg': [['uni', shop_tenant()]],
    '04-contracts': [['uni', shop_tenant(with_contracts=True, with_mgmt=True)],
                     ['uni/tn-Shop', mo('fvTenant', {'name': 'Shop'}, *vzany_solution)],
                     ['uni/tn-Shop/ctx-Prod/any', mo('vzAny', {}, mo('vzRsAnyToProv', {'tnVzBrCPName': 'mgmt-ssh'}))],
                     ['uni/tn-Shop/ap-Webshop/epg-Mgmt', mo('fvAEPg', {}, mo('fvRsCons', {'tnVzBrCPName': 'mgmt-ssh'}))]],
    '05-vpc-lacp': [['uni', access('VLAN-Pool-Server', 100, 199, 'PhysDom-Server', 'AAEP-Server', 'IPG-vPC-db1',
                                   'IntProf-Leaf103-104', 'db1', 10, 10, 'SwProf-Leaf103-104', 103, 104,
                                   pg_cls='infraAccBndlGrp', pg_extra=[mo('infraRsLacpPol', {'tnLacpLagPolName': 'LACP-Active'})],
                                   extra_infra=[mo('lacpLagPol', {'name': 'LACP-Active', 'mode': 'active'})])],
                    ['uni/fabric/protpol', mo('fabricExplicitGEp', {'name': 'vpc-103-104', 'id': '34'},
                                              mo('fabricNodePEp', {'id': '103'}), mo('fabricNodePEp', {'id': '104'}))],
                    ['uni', mo('fvTenant', {'name': 'Shop'}, bd('BD-DB', 'Prod', '10.10.30.1/24'),
                               filt('mysql', {'name': 'mysql', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': '3306', 'dToPort': '3306'}),
                               contract('app-to-db', ['mysql']),
                               mo('fvAp', {'name': 'Webshop'},
                                  epg('DB', 'BD-DB', ports=[('topology/pod-1/protpaths-103-104/pathep-[IPG-vPC-db1]', 130)], prov=['app-to-db']),
                                  mo('fvAEPg', {'name': 'App'}, mo('fvRsCons', {'tnVzBrCPName': 'app-to-db'}))))]],
    '06-l3out-ospf': [['uni', access('VLAN-Pool-WAN', 300, 399, 'L3Dom-WAN', 'AAEP-WAN', 'IPG-WAN', 'IntProf-Leaf103', 'wan',
                                     48, 48, 'SwProf-Leaf103', 103, 103, l3=True)],
                      ['uni', mo('fvTenant', {'name': 'Shop'},
                                 filt('https', {'name': 'https', 'etherT': 'ip', 'prot': 'tcp', 'dFromPort': 'https', 'dToPort': 'https'}),
                                 contract('web-to-internet', ['icmp', 'https']),
                                 bd('BD-Web', 'Prod', '10.10.10.1/24', 'public', 'WAN'),
                                 mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Web'}, mo('fvRsCons', {'tnVzBrCPName': 'web-to-internet'}))),
                                 mo('l3extOut', {'name': 'WAN'}, mo('l3extRsEctx', {'tnFvCtxName': 'Prod'}),
                                    mo('l3extRsL3DomAtt', {'tDn': 'uni/l3dom-L3Dom-WAN'}), mo('ospfExtP', {'areaId': '0.0.0.1'}),
                                    mo('l3extLNodeP', {'name': 'border'},
                                       mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-103', 'rtrId': '1.1.1.103'}),
                                       mo('l3extLIfP', {'name': 'eth48'}, mo('ospfIfP', {}),
                                          mo('l3extRsPathL3OutAtt', {'tDn': path(103, 'eth1/48'), 'ifInstT': 'l3-port',
                                                                     'addr': '172.16.0.1/30', 'mtu': '1500'}))),
                                    mo('l3extInstP', {'name': 'Internet'}, mo('l3extSubnet', {'ip': '0.0.0.0/0'}),
                                       mo('fvRsProv', {'tnVzBrCPName': 'web-to-internet'}))))], BGP_RR],
    '07-troubleshooting': [['uni/infra/vlanns-[VLAN-Pool-Ops]-static', mo('fvnsVlanInstP', {}, mo('fvnsEncapBlk', {'from': 'vlan-150', 'to': 'vlan-199'}))],
                           ['uni/infra/accportprof-IntProf-Ops/hports-Ops-Ports-typ-range', mo('infraHPortS', {}, mo('infraPortBlk', {'name': 'block3', 'fromPort': '12', 'toPort': '12'}))],
                           ['uni/tn-Ops/flt-http/e-http', mo('vzEntry', {'dFromPort': 'http', 'dToPort': 'http'})],
                           ['uni/tn-Ops/BD-BD-App', mo('fvBD', {'unicastRoute': 'yes'})],
                           ['uni/tn-Ops/ap-Ops/epg-Backup', mo('fvAEPg', {}, mo('fvRsBd', {'tnFvBDName': 'BD-Backup'}))],
                           ['uni/tn-Ops/brc-web-to-app/subj-subj', mo('vzSubj', {'revFltPorts': 'yes'})]],
    '08-rest-api': [['uni', mo('fvTenant', {'name': 'Automation'}, mo('fvCtx', {'name': 'v1'}), bd('bd1', 'v1', '192.168.1.1/24'),
                               mo('fvAp', {'name': 'app'}, epg('epg1', 'bd1', dom=None)))]],
    '09-l3out-bgp': [BGP_RR,
                     ['uni', access('VLAN-Pool-ISP', 300, 310, 'L3Dom-ISP', 'AAEP-ISP', 'IPG-ISP', 'IntProf-Leaf104', 'isp',
                                    47, 47, 'SwProf-Leaf104', 104, 104, l3=True)],
                     ['uni', mo('fvTenant', {'name': 'Shop'},
                                contract('web-to-isp', ['icmp']),
                                bd('BD-Web', 'Prod', '10.10.10.1/24', 'public', 'ISP'),
                                mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Web'}, mo('fvRsCons', {'tnVzBrCPName': 'web-to-isp'}))),
                                mo('l3extOut', {'name': 'ISP'}, mo('l3extRsEctx', {'tnFvCtxName': 'Prod'}),
                                   mo('l3extRsL3DomAtt', {'tDn': 'uni/l3dom-L3Dom-ISP'}), mo('bgpExtP', {}),
                                   mo('l3extLNodeP', {'name': 'border'},
                                      mo('l3extRsNodeL3OutAtt', {'tDn': 'topology/pod-1/node-104', 'rtrId': '1.1.1.104'}),
                                      mo('l3extLIfP', {'name': 'eth47'},
                                         mo('l3extRsPathL3OutAtt', {'tDn': path(104, 'eth1/47'), 'ifInstT': 'sub-interface',
                                                                    'encap': 'vlan-301', 'addr': '172.16.1.1/30'},
                                            mo('bgpPeerP', {'addr': '172.16.1.2'}, mo('bgpAsP', {'asn': '65100'}))))),
                                   mo('l3extInstP', {'name': 'Internet'}, mo('l3extSubnet', {'ip': '0.0.0.0/0'}),
                                      mo('fvRsProv', {'tnVzBrCPName': 'web-to-isp'}))))]],
    '10-mgmt-ntp': [['uni/tn-mgmt/mgmtp-default/oob-default', mo('mgmtOoB', {}, *[mo('mgmtRsOoBStNode', {'tDn': 'topology/pod-1/node-%d' % i, 'addr': '192.168.10.%d/24' % i, 'gw': '192.168.10.1'}) for i, _ in NODES_ALL])],
                    ['uni/fabric/time-default', mo('datetimePol', {}, mo('datetimeNtpProv', {'name': '192.168.10.250'}, mo('datetimeRsNtpProvToEpg', {'tDn': 'uni/tn-mgmt/mgmtp-default/oob-default'})))],
                    ['uni/fabric/funcprof', mo('fabricFuncP', {}, mo('fabricPodPGrp', {'name': 'PodPol'}, mo('fabricRsTimePol', {'tnDatetimePolName': 'default'})))],
                    ['uni/fabric/podprof-default/pods-default-typ-ALL', mo('fabricPodS', {}, mo('fabricRsPodPGrp', {'tDn': 'uni/fabric/funcprof/podpgrp-PodPol'}))]],
    '11-static-leaf-taboo': [['uni/tn-Shop', mo('fvTenant', {}, mo('vzTaboo', {'name': 'no-ping'}, mo('vzTSubj', {'name': 'deny'}, mo('vzRsDenyRule', {'tnVzFilterName': 'icmp'}))),
                                                mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'App'}, mo('fvRsNodeAtt', {'tDn': 'topology/pod-1/node-102', 'encap': 'vlan-120'}),
                                                                                    mo('fvRsProtBy', {'tnVzTabooName': 'no-ping'}))))]],
    '12-vmm-vcenter': [['uni', VMM12],
                       ['uni/tn-Shop/ap-Webshop', mo('fvAp', {}, *[mo('fvAEPg', {'name': n}, mo('fvRsDomAtt', {'tDn': 'uni/vmmp-VMware/dom-VDS-Prod', 'resImedcy': 'immediate'})) for n in ('Web', 'App')])]],
    '13-shared-services': [['uni/tn-Shared', mo('fvTenant', {},
                               filt('dns', {'name': 'dns', 'etherT': 'ip', 'prot': 'udp', 'dFromPort': 'dns', 'dToPort': 'dns'}),
                               contract('dns', ['dns'], scope='global'),
                               mo('fvAp', {'name': 'Infra'}, mo('fvAEPg', {'name': 'DNS'}, mo('fvRsProv', {'tnVzBrCPName': 'dns'}),
                                                                 mo('fvSubnet', {'ip': '10.99.0.1/24', 'scope': 'private,shared'}))))],
                           ['uni/tn-Shop', mo('fvTenant', {}, mo('vzCPIf', {'name': 'dns'}, mo('vzRsIf', {'tDn': 'uni/tn-Shared/brc-dns'})),
                                              mo('fvBD', {'name': 'BD-Web'}, mo('fvSubnet', {'ip': '10.10.10.1/24', 'scope': 'private,shared'})),
                                              mo('fvAp', {'name': 'Webshop'}, mo('fvAEPg', {'name': 'Web'}, mo('fvRsConsIf', {'tnVzCPIfName': 'dns'}))))]],
    '15-transit-route-control': [['uni', SOL15]],
    '16-service-graph-pbr': SOL16,
    '17-l3out-vpc-svi-bfd': [['uni', SOL17]],
    '18-ebgp-loopback-md5-summary': [['uni', SOL18]],
    '19-eigrp-static-track': [['uni', SOL19]],
    '20-floating-svi': [['uni', SOL20]],
    '21-aaa-tacacs-rbac': SOL21,
    '22-inband-management': [['uni', INBACC22], ['uni', INB22],
                             ['uni/userext', mo('aaaUserEp', {}, mo('aaaRadiusEp', {},
                                 mo('aaaRadiusProvider', {'name': '192.168.20.41', 'key': 'Rad#2026'},
                                    mo('aaaRsSecProvToEpg', {'tDn': 'uni/tn-mgmt/mgmtp-default/inb-default'})),
                                 mo('aaaRadiusProviderGroup', {'name': 'RAD'}, mo('aaaProviderRef', {'name': '192.168.20.41'}))),
                                 mo('aaaLoginDomain', {'name': 'RAD'}, mo('aaaDomainAuth', {'realm': 'radius', 'providerGroup': 'RAD'})))]],
    '23-esg-useg': [['uni', SOL23]],
    '24-firmware-upgrade': [['uni/fabric', FW24_DL], ['uni/controller/ctrlrfwpol', mo('firmwareCtrlrFwP', {'version': 'apic-6.0(6c)'})],
                            ['uni/controller/ctrlrmaintpol', mo('maintCtrlrMaintP', {'adminSt': 'triggered'})],
                            ['uni', mo('polUni', {}, upg_group('Odd', [101, 103, 201], True))],
                            ['uni', mo('polUni', {}, upg_group('Even', [102, 104, 202], True))]],
    '25-config-export-import': [['uni/fabric', RL25], ['uni/fabric', IMP25],
                                ['uni/exportcryptkey', mo('pkiExportEncryptionKey', {'strongEncryptionEnabled': 'yes', 'passphrase': 'Nightly-Backup#2026'})],
                                ['uni/fabric', EXP25]],
    '26-monitoring-snmp-syslog': [['uni/tn-mgmt/mgmtp-default', mo('mgmtMgmtP', {}, OOB26)], ['uni', mo('polUni', {}, SNMP26)],
                                  ['uni/fabric/podprof-default/pods-default-typ-ALL/rspodPGrp', mo('fabricRsPodPGrp', {'tDn': 'uni/fabric/funcprof/podpgrp-PodPol'})],
                                  ['#monitor-test', {'severity': 'major'}]],
    '27-dhcp-relay': [['uni', RELAY27]],
    '28-mcp-loop-qos': [['uni/infra/mcpInstP-default', MCP28], ['uni/infra/epLoopProtectP-default', mo('epLoopProtectP', {'adminSt': 'enabled'})],
                        ['uni/tn-Shop/ap-Webshop/epg-App', mo('fvAEPg', {'prio': 'level2'})]],
    '29-multipod': [['uni', mp_l3out(SPINES29)], ['uni', EXT29],
                    ['uni/controller/setuppol', mo('fabricSetupPol', {}, mo('fabricSetupP', {'podId': '2', 'tepPool': '10.1.0.0/16'}))],
                    ['#ipn', {'name': 'ipn1', 'relay': '10.0.0.1'}], ['#ipn', {'name': 'ipn2', 'relay': '10.0.0.1', 'mtu': 9150}]] +
                   [['uni/controller/nodeidentpol', mo('fabricNodeIdentP', {'serial': s_, 'nodeId': str(i), 'name': n, 'podId': '2'})]
                    for s_, i, n in [('FDO2219SP03', 203, 'spine203'), ('FDO2219SP04', 204, 'spine204'), ('SAL1931LA05', 105, 'leaf105'),
                                     ('SAL1931LA06', 106, 'leaf106')]],
    '30-remote-leaf': RLSOL30,
    '31-multisite-ndo': [['#ndo', {'op': 'onboard', 'user': 'admin', 'pwd': 'admin', 'siteId': '1'}], ['#ndo', {'op': 'infra', 'infra': INFRA31}],
                         ['#ndo', {'op': 'deployInfra'}], ['#ipn', {'name': 'isn1', 'mtu': 9150}],
                         ['#ndo', {'op': 'template', 'template': TPL31A}], ['#ndo', {'op': 'deploy', 'name': 'Shop-Stretched'}],
                         ['#ndo', {'op': 'template', 'template': TPL31B}], ['#ndo', {'op': 'deploy', 'name': 'HAM-Local'}]],
    '14-l2out-migration': [['uni', L2ACC14], ['uni', L2OUT14], ['uni/tn-Shop/BD-BD-Migration', mo('fvBD', {'arpFlood': 'yes'})]],
    '32-https-least-privilege': [['uni', SOL32]],
}


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith('.json'):
            os.remove(os.path.join(OUT, f))
    for l in LABS:
        l.setdefault('config', [])
        l.setdefault('hosts', [])
        l.setdefault('routers', [])
        l.setdefault('vcenters', [])
        l.setdefault('devices', [])
        l.setdefault('aaa', [])
        l.setdefault('switches', [])
        l['solutionConfig'] = SOLUTIONS[l['id']]
        with open(os.path.join(OUT, l['id'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(l, f, ensure_ascii=False, indent=1)
    print('%d Labs geschrieben nach %s' % (len(LABS), OUT))


if __name__ == '__main__':
    main()
