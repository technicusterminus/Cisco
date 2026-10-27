"""AAA: Login-Domains, Remote-Authentifizierung (TACACS+, RADIUS, LDAP) und RBAC."""
import re

from .model import AciError, tenant_of

REALM_CLS = {'tacacs': ('tacacsext', 'aaaTacacsPlusProviderGroup', 'tacacsplusprovidergroup', 'tacacsplusprovider', 'aaaTacacsPlusProvider'),
             'radius': ('radiusext', 'aaaRadiusProviderGroup', 'radiusprovidergroup', 'radiusprovider', 'aaaRadiusProvider'),
             'ldap': ('ldapext', 'aaaLdapProviderGroup', 'ldapprovidergroup', 'ldapprovider', 'aaaLdapProvider')}

# Welche Rollen duerfen welche Bereiche schreiben (Bereich -> Rollen)
WRITE_ROLES = {
    'tenant': {'admin', 'tenant-admin', 'tenant-ext-admin'},
    'l4l7': {'admin', 'tenant-admin', 'nw-svc-admin'},
    'access': {'admin', 'access-admin'},
    'fabric': {'admin', 'fabric-admin'},
    'aaa': {'admin', 'aaa'},
    'vmm': {'admin', 'vmm-admin'},
    'other': {'admin'},
}


def parse_login(name):
    """'apic#Domain\\\\user', 'apic:Domain\\\\user' oder 'user' -> (domain|None, user)."""
    m = re.match(r'^apic[#:]([^\\/]+)[\\/](.+)$', name or '')
    if m:
        return m.group(1), m.group(2)
    return None, name or ''


def parse_avpair(av):
    """'shell:domains=all/admin/,Shop/tenant-admin/read-all' -> Rollenliste."""
    roles = []
    m = re.match(r'^\s*shell:domains\s*=\s*(.+?)\s*$', av or '')
    if not m:
        return roles
    for part in m.group(1).split(','):
        bits = part.strip().split('/')
        if len(bits) < 2 or not bits[0]:
            continue
        dom = bits[0]
        for r in [x for x in bits[1].split('|') if x]:
            roles.append({'domain': dom, 'role': r, 'priv': 'writePriv'})
        if len(bits) > 2:
            for r in [x for x in bits[2].split('|') if x]:
                roles.append({'domain': dom, 'role': r, 'priv': 'readPriv'})
    return roles


def local_roles(store, user):
    roles = []
    base = 'uni/userext/user-%s' % user
    for d in store.children(base, 'aaaUserDomain'):
        dom = store.attrs(d)['name']
        for r in store.children(d, 'aaaUserRole'):
            a = store.attrs(r)
            roles.append({'domain': dom, 'role': a['name'], 'priv': a['privType']})
    return roles


def is_admin(roles):
    return any(r['domain'] == 'all' and r['role'] == 'admin' and r['priv'] == 'writePriv' for r in roles)


def _provider_reachable(S, prov_dn, ip):
    """Ist der Provider ueber sein Management-EPG erreichbar?"""
    st, e = S.store, S.engine
    rs = st.attrs(prov_dn + '/rsSecProvToEpg') or {}
    epg = rs.get('tDn') or 'uni/tn-mgmt/mgmtp-default/oob-default'
    if '/inb-' in epg:
        if not getattr(e, 'inb', {}).get(1):
            return False, 'Management EPG ist In-Band, aber der APIC hat keine aktive In-Band-Adresse'
    elif not e.oob.get(1):
        return False, 'Der APIC hat keine Out-of-Band-Adresse'
    srv = next((x for x in S.sim.get('aaa', []) if x['ip'] == ip), None)
    if not srv:
        return False, 'Unter %s antwortet kein Server' % ip
    if srv.get('down'):
        return False, 'Server %s ist ausgefallen' % ip
    return True, srv


def remote_auth(S, realm, group, user, pwd):
    """Fragt die Provider der Gruppe der Reihe nach. Rueckgabe (roles, info) oder (None, Grund); 'unreachable' wenn keiner antwortet."""
    st = S.store
    ext, gcls, grn, prn, pcls = REALM_CLS[realm]
    gdn = 'uni/userext/%s/%s-%s' % (ext, grn, group)
    if gdn not in st.objs:
        return None, 'Provider Group %s existiert nicht' % group
    refs = sorted((st.attrs(d) for d in st.children(gdn, 'aaaProviderRef')),
                  key=lambda a: int(a.get('order') or 1))
    tried = []
    for ref in refs:
        pdn = 'uni/userext/%s/%s-%s' % (ext, prn, ref['name'])
        if pdn not in st.objs:
            tried.append('%s: Provider nicht konfiguriert' % ref['name'])
            continue
        ok, srv = _provider_reachable(S, pdn, ref['name'])
        if not ok:
            tried.append('%s: %s' % (ref['name'], srv))
            continue
        if srv.get('type') != realm:
            tried.append('%s: Server spricht %s, nicht %s' % (ref['name'], srv.get('type'), realm))
            continue
        if (srv.get('key') or '') != (st.attrs(pdn).get('key') or ''):
            if realm == 'radius':
                tried.append('%s: keine gueltige Antwort (Shared Secret falsch, der Server verwirft die Anfrage)' % ref['name'])
                continue
            return None, '%s: Authentifizierung fehlgeschlagen (Shared Key falsch)' % ref['name']
        u = next((x for x in srv.get('users', []) if x['name'] == user), None)
        if not u or u.get('pwd') != pwd:
            return None, 'Server %s: Benutzer oder Passwort falsch' % ref['name']
        roles = parse_avpair(u.get('avpair', ''))
        return roles, {'server': ref['name'], 'avpair': u.get('avpair', '')}
    return None, 'unreachable: ' + '; '.join(tried or ['keine Provider in der Gruppe'])


def authenticate(S, name, pwd):
    """Rueckgabe (user, roles, info). Wirft AciError bei Fehlschlag."""
    st = S.store
    dom, user = parse_login(name)
    if dom:
        ddn = 'uni/userext/logindomain-%s' % dom
        if ddn not in st.objs:
            raise AciError(401, 'Login-Domain %s existiert nicht' % dom, 401)
        da = st.attrs(ddn + '/domainauth') or {'realm': 'local'}
        realm, group, fallback_ok = da['realm'], da.get('providerGroup', ''), False
    else:
        da = st.attrs('uni/userext/authrealm/defaultauth') or {'realm': 'local'}
        realm, group = da['realm'], da.get('providerGroup', '')
        fallback_ok = da.get('fallbackCheck', 'false') == 'false'
    if realm == 'local':
        return _local(st, user, pwd, 'lokal' + (' (Domain %s)' % dom if dom else ''))
    roles, info = remote_auth(S, realm, group, user, pwd)
    if roles is None:
        if info.startswith('unreachable') and fallback_ok:
            return _local(st, user, pwd, 'lokal (Fallback: kein %s-Server erreichbar)' % realm.upper())
        raise AciError(401, 'Login fehlgeschlagen: %s' % info.replace('unreachable: ', 'kein Server erreichbar - '), 401)
    if not roles:
        pol = (st.attrs('uni/userext/authrealm') or {}).get('defRolePolicy', 'no-login')
        if pol == 'assign-default-role':
            roles = [{'domain': 'all', 'role': 'read-all', 'priv': 'readPriv'}]
        else:
            raise AciError(401, 'Login fehlgeschlagen: Der %s-Server liefert kein gueltiges Cisco AV-Pair '
                           '(shell:domains=...) und die Remote User Login Policy steht auf no-login' % realm.upper(), 401)
    return user, roles, '%s ueber %s (%s)' % (realm.upper(), info['server'], info['avpair'])


def _local(st, user, pwd, how):
    u = st.attrs('uni/userext/user-%s' % user)
    if not u or u.get('pwd') != pwd:
        raise AciError(401, 'Username or password is incorrect - FAILED local authentication', 401)
    if u.get('accountStatus') == 'inactive':
        raise AciError(401, 'Benutzerkonto %s ist deaktiviert' % user, 401)
    roles = local_roles(st, user)
    if not roles:
        raise AciError(401, 'Benutzer %s hat keine Security Domain mit Rolle - Login nicht moeglich' % user, 401)
    return user, roles, how


# ---------------------------------------------------------------------------- RBAC
def area(dn):
    if dn.startswith('uni/tn-'):
        if re.search(r'/(lDevVip|AbsGraph|ldevCtx|svcCont)', dn):
            return 'l4l7'
        return 'tenant'
    if dn.startswith('uni/userext'):
        return 'aaa'
    if dn.startswith('uni/vmmp'):
        return 'vmm'
    if re.match(r'^uni/(infra|phys-|l3dom-|l2dom-)', dn):
        return 'access'
    if re.match(r'^(uni/fabric|uni/controller|topology)', dn):
        return 'fabric'
    return 'other'


def obj_domains(store, dn):
    """Security Domains eines Objekts: die des Tenants (bzw. Domain-Objekts) plus 'all'."""
    doms = {'all'}
    tn = tenant_of(dn)
    owner = tn
    if not owner:
        m = re.match(r'^(uni/(?:phys|l3dom|l2dom)-[^/]+|uni/vmmp-[^/]+/dom-[^/]+|uni/infra/attentp-[^/]+)', dn)
        owner = m.group(1) if m else None
    if owner:
        for k in store.children(owner, 'aaaDomainRef'):
            doms.add(store.attrs(k)['name'])
        if tn == 'uni/tn-common':
            doms.add('common')
        if tn == 'uni/tn-mgmt':
            doms.add('mgmt')
    return doms


def can_read(store, roles, dn):
    if is_admin(roles):
        return True
    doms = obj_domains(store, dn)
    if any(r['domain'] in doms for r in roles):
        return True
    # common darf jeder sehen, der irgendeine Rolle hat (Default-Filter, VRF, Contracts aus common)
    return tenant_of(dn) == 'uni/tn-common' and bool(roles)


def can_write(store, roles, dn):
    if is_admin(roles):
        return True
    doms = obj_domains(store, dn)
    allowed = WRITE_ROLES[area(dn)]
    return any(r['domain'] in doms and r['role'] in allowed and r['priv'] == 'writePriv' for r in roles)


def describe(roles):
    return ', '.join('%s/%s (%s)' % (r['domain'], r['role'], 'write' if r['priv'] == 'writePriv' else 'read') for r in roles)
