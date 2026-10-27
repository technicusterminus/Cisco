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


def lab(**kw):
    LABS.append(kw)


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
# Maschinenlesbare Musterloesungen (fuer die Tests: [URL-DN, Body])
# ----------------------------------------------------------------------------
BGP_RR = ['uni/fabric/bgpInstP-default', mo('bgpInstPol', {}, mo('bgpAsP', {'asn': '65001'}),
                                            mo('bgpRRP', {}, mo('bgpRRNodePEp', {'id': '201'}), mo('bgpRRNodePEp', {'id': '202'})))]
SOLUTIONS = {
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
        l['solutionConfig'] = SOLUTIONS[l['id']]
        with open(os.path.join(OUT, l['id'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(l, f, ensure_ascii=False, indent=1)
    print('%d Labs geschrieben nach %s' % (len(LABS), OUT))


if __name__ == '__main__':
    main()
