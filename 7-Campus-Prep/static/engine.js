/* Campus Prep: Simulator-Engine im Browser (Portierung von campusprep/wlc.py, labs.py, store.py und der Sim-Klasse in server.py).

   Zweck: WLC-Simulator.html laeuft per Doppelklick ohne Python und ohne Webserver. Die Engine bietet dieselben Endpunkte wie der
   Python-Server (handle(method, path, body) -> {status, body}); die Oberflaeche (app.js) merkt den Unterschied nicht.

   Es gibt zwei Implementierungen derselben Regeln. Damit sie nicht auseinanderlaufen, erzeugt tests/parity/make_fixtures.py aus
   der Python-Engine erwartete Ergebnisse (HTTP-Schritte, Zustand), und tests/parity/parity.js spielt sie gegen diese Datei ab.
   Aenderungen an den Regeln gehoeren in beide Dateien; ohne gruenen Paritaetstest werden sie nicht uebernommen.

   Hinweise zur Portierung:
   - Woerterbuecher mit Namen aus Benutzereingaben sind Objekte ohne Prototyp (dict/clone), damit Namen wie "constructor" oder
     "__proto__" wie in Python gewoehnliche Schluessel sind. WLAN-Profile liegen in einer Map (Einfuegereihenfolge auch bei
     rein numerischen Namen, wie in Python).
   - Python-Ausgaben (str() von None/True, repr() von dict) werden nachgebildet, weil sie in Detailtexten der Labs stehen.
*/
(function (root) {
  'use strict';

  const DEF_POLICY_TAG = 'default-policy-tag', DEF_SITE_TAG = 'default-site-tag', DEF_RF_TAG = 'default-rf-tag';
  const DEF_FLEX_PROFILE = 'default-flex-profile', DEF_WEBAUTH_MAP = 'global', DEF_MOBILITY_GROUP = 'default';
  const RF_BANDS = { '24ghz': '2,4 GHz', '5ghz': '5 GHz' };
  const NAME_RE = /^[\p{L}\p{N}_.-]{1,32}$/u;          // wie Python \w (Unicode)
  const STORE_NAME_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$/;
  const KIND = 'campusprep-state', VERSION = 6, ACCEPTED = [1, 2, 3, 4, 5, 6];
  const MODES = ['guided', 'exam'];
  const HIDDEN = ['cause', 'solution', 'solutionCommands', 'startCommands', 'worldClients', 'worldRadius', 'worldMobility', 'checks', 'hints', 'questions'];

  // ------------------------------------------------------------------ Hilfen
  class CliError extends Error {}
  class LabError extends Error { constructor(msg, status) { super(msg); this.status = status || 400; } }
  class StoreError extends Error { constructor(msg, status) { super(msg); this.status = status || 400; } }

  const isDict = x => x !== null && typeof x === 'object' && !Array.isArray(x);
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const dict = () => Object.create(null);
  function clone(x) {
    if (Array.isArray(x)) return x.map(clone);
    if (isDict(x)) { const o = dict(); for (const k of Object.keys(x)) o[k] = clone(x[k]); return o; }
    return x;
  }
  const plain = x => JSON.parse(JSON.stringify(x));          // fuer Antworten: gewoehnliche Objekte
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  const sortedKeys = o => Object.keys(o).sort(cmp);
  const isDigits = s => /^[0-9]+$/.test(String(s));
  const pad = (v, n) => String(v).padEnd(n);
  const get = (o, k) => (has(o, k) ? o[k] : undefined);
  const setdefault = (o, k, v) => { if (!has(o, k)) o[k] = v; return o[k]; };

  function pyStr(v) { return v === null || v === undefined ? 'None' : v === true ? 'True' : v === false ? 'False' : String(v); }
  function pyRepr(v) {
    if (v === null || v === undefined) return 'None';
    if (v === true) return 'True';
    if (v === false) return 'False';
    if (typeof v === 'number') return String(v);
    if (typeof v === 'string') {
      const q = v.includes("'") && !v.includes('"') ? '"' : "'";
      let out = '';
      for (const ch of v) {
        if (ch === '\\') out += '\\\\';
        else if (ch === q) out += '\\' + q;
        else if (ch === '\n') out += '\\n';
        else if (ch === '\r') out += '\\r';
        else if (ch === '\t') out += '\\t';
        else out += ch;
      }
      return q + out + q;
    }
    if (Array.isArray(v)) return '[' + v.map(pyRepr).join(', ') + ']';
    return '{' + Object.keys(v).map(k => pyRepr(k) + ': ' + pyRepr(v[k])).join(', ') + '}';
  }
  const deepEqual = (a, b) => JSON.stringify(canon(a)) === JSON.stringify(canon(b));
  function canon(x) {
    if (Array.isArray(x)) return x.map(canon);
    if (isDict(x)) { const o = {}; for (const k of sortedKeys(x)) o[k] = canon(x[k]); return o; }
    return x;
  }
  const stableStringify = x => JSON.stringify(canon(x), null, 1) + '\n';

  function normMac(m) {
    const h = Array.from(String(m).toLowerCase()).filter(c => '0123456789abcdef'.includes(c)).join('');
    if (h.length !== 12) throw new Error('MAC-Adresse ungueltig: ' + m);
    return h.slice(0, 4) + '.' + h.slice(4, 8) + '.' + h.slice(8, 12);
  }

  /* Der simulierte RADIUS-Server hinter dem Controller (Gegenseite, nicht konfigurierbar). */
  const defaultMobility = () => clone({ controllers: [{ name: 'wlc2', ip: '10.10.0.20', mac: 'aabb.cc00.0200', group: 'Campus', up: true,
    knows: { ip: '10.10.0.10', mac: 'aabb.cc00.0100', group: 'default' }, wlans: { Corp: 'psk' } }] });
  const defaultRadius = () => clone({ servers: [{ ip: '10.10.0.50', auth_port: 1812, secret: 'RadiusKey1', up: true, nas: ['10.10.0.10'],
    users: [{ name: 'anna', password: 'Passw0rt!', vlan: '30' }, { name: 'bernd', password: 'Geheim#2', vlan: '40' },
            { name: 'carla', password: 'Sommer#3', vlan: null }] }] });

  function newWorld() {
    return clone({
      wlc: { hostname: 'wlc1', platformId: 'C9800-CL-K9', ip: '10.10.0.10', mac: 'aabb.cc00.0100', serial: 'SIM9800CL001',
             version: '17.9.4a', location: 'Rechenzentrum', uptimeSeconds: 864000 },
      aps: [
        { name: 'ap-lobby', model: '9130AXI', ethMac: 'a4b2.32aa.0001', radioMac: '2c57.41aa.0001', ip: '10.10.20.11',
          location: 'default location', country: 'DE', serial: 'SIMAP0000001', joined: true },
        { name: 'ap-lager', model: '9130AXI', ethMac: 'a4b2.32aa.0002', radioMac: '2c57.41aa.0002', ip: '10.10.20.12',
          location: 'default location', country: 'DE', serial: 'SIMAP0000002', joined: true },
      ],
      clients: [
        { mac: '58bf.eaaa.0001', ssid: 'Corp', psk: 'Sommer2026', ap: 'ap-lobby', protocol: '11ac' },
        { mac: '58bf.eaaa.0002', ssid: 'Corp', psk: 'falsch', ap: 'ap-lobby', protocol: '11ax' },
      ],
      radius: defaultRadius(),
      mobility: defaultMobility(),
    });
  }

  // ------------------------------------------------------------------ WLC
  const newFlex = () => ({ native: null, vlans: dict(), descr: '' });
  const newSite = () => ({ local: true, flex: null, descr: '' });

  class Wlc {
    constructor(world) {
      this.world = world;
      this.wlans = new Map();                   // profil -> {id, ssid, shutdown, akm, psk}
      this.policies = dict();                   // name -> {vlan, shutdown, descr, central}
      this.policyTags = dict(); this.policyTags[DEF_POLICY_TAG] = dict();
      this.apCfg = dict();                      // ethMac -> {policy_tag, site_tag}
      this.flexProfiles = dict(); this.flexProfiles[DEF_FLEX_PROFILE] = newFlex();
      this.siteTags = dict(); this.siteTags[DEF_SITE_TAG] = newSite();
      this.radiusServers = dict();              // name -> {ip, auth_port, acct_port, key, timeout, retransmit}
      this.aaaGroups = dict();                  // name -> {servers: [radius-server-name]} (Reihenfolge = Reihenfolge der Versuche)
      this.aaaLists = dict();                   // dot1x-Methodenliste name -> {group}
      this.localUsers = dict();                 // Benutzername -> Passwort (lokale Datenbank fuer Web-Auth)
      this.loginLists = dict();                 // Login-Methodenliste name -> {method: 'local'}
      this.authzDefaultLocal = false;           // aaa authorization network default local
      this.webauthMaps = dict(); this.webauthMaps[DEF_WEBAUTH_MAP] = { type: 'webauth', virtual_ip: '192.0.2.1' };
      this.mobilityGroup = DEF_MOBILITY_GROUP;  // wireless mobility group name
      this.mobilityPeers = dict();              // Peer-IP -> {mac, group}
      this.rfProfiles = dict();                 // 'band:name' -> {band, name, shutdown, tx_min, tx_max, descr}
      this.rfTags = dict(); this.rfTags[DEF_RF_TAG] = { '24ghz': '', '5ghz': '' };   // name -> {24ghz, 5ghz}
    }

    snapshot() {
      return clone({ wlans: this.dumpWlans(), policies: this.policies, policyTags: this.policyTags, apCfg: this.apCfg,
                     flexProfiles: this.flexProfiles, siteTags: this.siteTags, radiusServers: this.radiusServers,
                     aaaGroups: this.aaaGroups, aaaLists: this.aaaLists, localUsers: this.localUsers, loginLists: this.loginLists,
                     authzDefaultLocal: this.authzDefaultLocal, webauthMaps: this.webauthMaps, mobilityGroup: this.mobilityGroup,
                     mobilityPeers: this.mobilityPeers, rfProfiles: this.rfProfiles, rfTags: this.rfTags });
    }
    restore(s) {
      this.loadWlans(s.wlans);
      this.policies = clone(s.policies); this.policyTags = clone(s.policyTags); this.apCfg = clone(s.apCfg);
      this.flexProfiles = clone(s.flexProfiles); this.siteTags = clone(s.siteTags);
      this.radiusServers = clone(s.radiusServers); this.aaaGroups = clone(s.aaaGroups); this.aaaLists = clone(s.aaaLists);
      this.localUsers = clone(s.localUsers); this.loginLists = clone(s.loginLists); this.authzDefaultLocal = s.authzDefaultLocal;
      this.webauthMaps = clone(s.webauthMaps); this.mobilityGroup = s.mobilityGroup; this.mobilityPeers = clone(s.mobilityPeers);
      this.rfProfiles = clone(s.rfProfiles); this.rfTags = clone(s.rfTags);
    }
    dumpWlans() { const o = dict(); for (const [k, v] of this.wlans) o[k] = clone(v); return o; }
    loadWlans(o) { this.wlans = new Map(); for (const k of Object.keys(o)) this.wlans.set(k, clone(o[k])); }
    dump() { return this.snapshot(); }
    load(d) {
      // Pflichtfelder wie in Python: Ein Stand mit fehlenden Feldern ist beschaedigt
      const need = (o, keys) => { for (const k of keys) if (!has(o, k)) throw new Error('Feld fehlt: ' + k); };
      for (const k of Object.keys(d.wlans)) need(d.wlans[k], ['id', 'ssid', 'shutdown', 'akm', 'psk']);
      for (const k of Object.keys(d.policies)) need(d.policies[k], ['vlan', 'descr', 'shutdown']);
      const fps = d.flexProfiles || {}, sts = d.siteTags || {};
      for (const k of Object.keys(fps)) need(fps[k], ['descr', 'native', 'vlans']);
      for (const k of Object.keys(sts)) { need(sts[k], ['descr', 'local']); if (!sts[k].local) need(sts[k], ['flex']); }
      this.loadWlans(d.wlans);
      this.policies = clone(d.policies); this.policyTags = clone(d.policyTags); this.apCfg = clone(d.apCfg);
      setdefault(this.policyTags, DEF_POLICY_TAG, dict());
      // Staende der Version 1 kennen weder Flex Profiles noch Site Tags: Standardobjekte verwenden
      this.flexProfiles = clone(Object.keys(fps).length ? fps : {});
      setdefault(this.flexProfiles, DEF_FLEX_PROFILE, newFlex());
      this.siteTags = clone(Object.keys(sts).length ? sts : {});
      setdefault(this.siteTags, DEF_SITE_TAG, newSite());
      // Staende vor Version 3 kennen keine AAA-Objekte
      this.radiusServers = clone(d.radiusServers && Object.keys(d.radiusServers).length ? d.radiusServers : {});
      this.aaaGroups = clone(d.aaaGroups && Object.keys(d.aaaGroups).length ? d.aaaGroups : {});
      this.aaaLists = clone(d.aaaLists && Object.keys(d.aaaLists).length ? d.aaaLists : {});
      // Staende vor Version 4 kennen keine Web-Auth-Objekte
      this.localUsers = clone(d.localUsers && Object.keys(d.localUsers).length ? d.localUsers : {});
      this.loginLists = clone(d.loginLists && Object.keys(d.loginLists).length ? d.loginLists : {});
      this.authzDefaultLocal = !!d.authzDefaultLocal;
      this.webauthMaps = clone(d.webauthMaps && Object.keys(d.webauthMaps).length ? d.webauthMaps : {});
      setdefault(this.webauthMaps, DEF_WEBAUTH_MAP, { type: 'webauth', virtual_ip: '192.0.2.1' });
      // Staende vor Version 5 kennen kein Mobility
      this.mobilityGroup = d.mobilityGroup || DEF_MOBILITY_GROUP;
      this.mobilityPeers = clone(d.mobilityPeers && Object.keys(d.mobilityPeers).length ? d.mobilityPeers : {});
      // Staende vor Version 6 kennen keine RF-Profile
      this.rfProfiles = clone(d.rfProfiles && Object.keys(d.rfProfiles).length ? d.rfProfiles : {});
      this.rfTags = clone(d.rfTags && Object.keys(d.rfTags).length ? d.rfTags : {});
      setdefault(this.rfTags, DEF_RF_TAG, { '24ghz': '', '5ghz': '' });
    }

    // ---- Zustand fuer die Oberflaeche
    state() {
      const aps = this.world.aps.map(a => {
        const cfg = get(this.apCfg, a.ethMac) || {};
        const explicit = cfg.policy_tag || cfg.site_tag || cfg.rf_tag;
        return { name: a.name, model: a.model, ethMac: a.ethMac, radioMac: a.radioMac, ip: a.ip, location: a.location,
                 country: a.country, state: a.joined ? 'Registered' : 'Not joined', policyTag: this.policyTagOf(a),
                 siteTag: this.siteTagOf(a), rfTag: this.rfTagOf(a),
                 rf: { '24ghz': this.rfEffective(a, '24ghz'), '5ghz': this.rfEffective(a, '5ghz') }, mode: this.apMode(a), tagSource: explicit ? 'Static' : 'Default' };
      });
      const wl = [...this.wlans.entries()].sort((x, y) => x[1].id - y[1].id);
      return {
        wlc: Object.assign({}, this.world.wlc),
        wlans: wl.map(([n, w]) => ({ profile: n, id: w.id, ssid: w.ssid, status: w.shutdown ? 'DOWN' : 'UP', akm: w.akm,
                                     pskSet: !!w.psk, authList: w.authlist || '', webAuth: !!w.webauth, webAuthList: w.webauth_list || '',
                                     webAuthMap: w.webauth_map || '', security: Wlc.securityOf(w) })),
        policies: sortedKeys(this.policies).map(n => { const p = this.policies[n];
          return { name: n, vlan: p.vlan, description: p.descr, central: has(p, 'central') ? p.central : true,
                   aaaOverride: has(p, 'aaa_override') ? p.aaa_override : false, status: p.shutdown ? 'DISABLED' : 'ENABLED' }; }),
        radiusServers: sortedKeys(this.radiusServers).map(n => { const r = this.radiusServers[n];
          return { name: n, ip: r.ip, authPort: r.auth_port, acctPort: r.acct_port, keySet: !!r.key, timeout: r.timeout, retransmit: r.retransmit,
                   state: this.radiusReply(n)[0] ? 'UP' : 'DEAD' }; }),
        aaaGroups: sortedKeys(this.aaaGroups).map(n => ({ name: n, servers: this.aaaGroups[n].servers.slice() })),
        aaaLists: sortedKeys(this.aaaLists).map(n => ({ name: n, group: this.aaaLists[n].group })),
        localUsers: sortedKeys(this.localUsers).map(n => ({ name: n, passwordSet: !!this.localUsers[n] })),
        loginLists: sortedKeys(this.loginLists).map(n => ({ name: n, method: this.loginLists[n].method })),
        authzDefaultLocal: this.authzDefaultLocal,
        rfProfiles: sortedKeys(this.rfProfiles).map(k => { const p = this.rfProfiles[k];
          return { name: p.name, band: p.band, status: p.shutdown ? 'DISABLED' : 'ENABLED', txMin: p.tx_min, txMax: p.tx_max, description: p.descr }; }),
        rfTags: sortedKeys(this.rfTags).map(n => ({ name: n, builtin: n === DEF_RF_TAG, rf24: this.rfTags[n]['24ghz'], rf5: this.rfTags[n]['5ghz'] })),
        mobilityGroup: this.mobilityGroup, mobilityMac: this.world.wlc.mac,
        mobilityPeers: sortedKeys(this.mobilityPeers).map(ip => Object.assign({ ip, mac: this.mobilityPeers[ip].mac, group: this.mobilityPeers[ip].group }, this.mobilityTunnel(ip))),
        webauthMaps: sortedKeys(this.webauthMaps).map(n => ({ name: n, builtin: n === DEF_WEBAUTH_MAP, type: this.webauthMaps[n].type, virtualIp: this.webauthMaps[n].virtual_ip })),
        flexProfiles: sortedKeys(this.flexProfiles).map(n => { const f = this.flexProfiles[n];
          return { name: n, builtin: n === DEF_FLEX_PROFILE, description: f.descr, native: f.native,
                   vlans: sortedKeys(f.vlans).map(k => ({ name: k, id: f.vlans[k] })) }; }),
        siteTags: sortedKeys(this.siteTags).map(n => { const t = this.siteTags[n];
          return { name: n, builtin: n === DEF_SITE_TAG, description: t.descr, local: t.local,
                   flexProfile: t.local ? null : (t.flex || DEF_FLEX_PROFILE) }; }),
        policyTags: sortedKeys(this.policyTags).map(n => ({ name: n, builtin: n === DEF_POLICY_TAG,
          maps: sortedKeys(this.policyTags[n]).map(k => ({ wlan: k, policy: this.policyTags[n][k] })) })),
        aps,
        clients: this.clients().map(c => ({ mac: c.mac, ssid: c.ssid, ap: c.ap, protocol: c.protocol, state: c.state, wlan: c.wlan,
                                            vlan: c.vlan, method: c.method, switching: c.switching, mode: c.mode,
                                            roam: c.roam === undefined ? null : c.roam,
                                            user: (() => { const e = c.eap && Object.keys(c.eap).length ? c.eap : (c.web && Object.keys(c.web).length ? c.web : null); return e && e.user !== undefined ? e.user : null; })(),
                                            reasons: c.reasons })),
      };
    }

    apByName(name) { return this.world.aps.find(a => a.name === name) || null; }
    rfTagOf(ap) { return (get(this.apCfg, ap.ethMac) || {}).rf_tag || DEF_RF_TAG; }
    rfEffective(ap, band) {
      /* Wirkung der RF-Konfiguration: Das RF Tag verweist je Band auf ein RF-Profil. Ohne Verweis gelten die globalen Einstellungen;
         ein deaktiviertes RF-Profil schaltet das Band ab (Simulator-Modell). */
      const tag = get(this.rfTags, this.rfTagOf(ap)) || {};
      const name = tag[band] || '';
      const prof = name ? get(this.rfProfiles, band + ':' + name) : null;
      if (!prof) return { profile: null, txMax: null, radio: 'on' };
      if (prof.shutdown) return { profile: name, txMax: null, radio: 'off' };
      return { profile: name, txMax: prof.tx_max, radio: 'on' };
    }
    policyTagOf(ap) { return (get(this.apCfg, ap.ethMac) || {}).policy_tag || DEF_POLICY_TAG; }
    siteTagOf(ap) { return (get(this.apCfg, ap.ethMac) || {}).site_tag || DEF_SITE_TAG; }
    apMode(ap) { const st = get(this.siteTags, this.siteTagOf(ap)); return !st || st.local ? 'Local' : 'FlexConnect'; }
    flexOf(ap) { const st = get(this.siteTags, this.siteTagOf(ap)); return !st || st.local ? null : (st.flex || DEF_FLEX_PROFILE); }

    static flexVlan(fp, v) {
      /* VLAN-ID, die der AP fuer den Wert aus dem Policy Profile kennt, sonst null. Namen muessen exakt passen (belegt);
         eine numerische ID passt auf eine VLAN-ID des Flex Profile oder seine Native VLAN (Annahme). */
      if (!fp) return null;
      if (isDigits(v)) {
        const i = parseInt(v, 10);
        const ids = Object.keys(fp.vlans).map(k => fp.vlans[k]).filter(x => x !== null);
        return ids.includes(i) || fp.native === i ? i : null;
      }
      const r = get(fp.vlans, v);
      return r === undefined ? null : r;
    }

    static securityOf(w) {
      /* Spalte Security von show wlan summary: [WPA2][802.1x][AES] und [open] sind belegt, [PSK] ist abgeleitet. */
      return w.akm === 'psk' ? '[WPA2][PSK][AES]' : w.akm === 'dot1x' ? '[WPA2][802.1x][AES]' : '[open]';
    }

    radiusReply(name) {
      /* Antwortet der RADIUS-Server hinter dem konfigurierten Eintrag? [ok, Grund]. Ohne Antwort verwirft der Controller den Versuch und
         nimmt den naechsten Server der Group; der Server gilt dann als DEAD (Simulator-Modell). */
      const srv = get(this.radiusServers, name);
      if (!srv) return [false, 'RADIUS-Server ' + name + ' ist nicht definiert'];
      if (!srv.ip) return [false, 'RADIUS-Server ' + name + ' hat keine Adresse (address ipv4 fehlt)'];
      const ws = (((this.world.radius || {}).servers) || []).find(x => x.ip === srv.ip);
      if (!ws || !ws.up) return [false, 'RADIUS-Server ' + name + ' (' + srv.ip + ') antwortet nicht'];
      if (srv.auth_port !== (has(ws, 'auth_port') ? ws.auth_port : 1812)) return [false, 'RADIUS-Server ' + name + ' (' + srv.ip + ') antwortet nicht: Auth-Port ' + srv.auth_port + ' stimmt nicht'];
      if (!ws.nas.includes(this.world.wlc.ip)) return [false, 'RADIUS-Server ' + name + ' verwirft die Anfrage: Der Controller ist dort nicht als Client eingetragen'];
      if (srv.key !== ws.secret) return [false, 'RADIUS-Server ' + name + ' verwirft die Anfrage: Das Shared Secret stimmt nicht'];
      return [true, ''];
    }

    wlanServers(w) {
      const mm = get(this.aaaLists, w.authlist || '');
      const grp = mm ? get(this.aaaGroups, mm.group) : undefined;
      return (grp ? grp.servers : []).filter(n => has(this.radiusServers, n)).map(n => this.radiusServers[n].ip);
    }

    _dot1x(client, w, res) {
      /* 802.1X: Kette WLAN -> Authentication List -> Server Group -> RADIUS-Server pruefen. [ok, Benutzer-Eintrag] */
      const eap = client.eap;
      if (!eap) { res.reasons.push('Das Endgeraet sendet keine 802.1X-Zugangsdaten, das WLAN verlangt 802.1X'); return [false, null]; }
      const lst = w.authlist || '';
      if (!lst) { res.reasons.push('Am WLAN-Profil ist keine 802.1X-Authentication-List konfiguriert (security dot1x authentication-list)'); return [false, null]; }
      const mm = get(this.aaaLists, lst);
      if (!mm) { res.reasons.push('Die Authentication List ' + lst + ' ist nicht definiert (aaa authentication dot1x)'); return [false, null]; }
      const grp = get(this.aaaGroups, mm.group);
      if (!grp) { res.reasons.push('Die Server Group ' + mm.group + ' der Authentication List ' + lst + ' ist nicht definiert'); return [false, null]; }
      if (!grp.servers.length) { res.reasons.push('Die Server Group ' + mm.group + ' enthaelt keinen RADIUS-Server'); return [false, null]; }
      const tried = [];
      for (const name of grp.servers) {
        const [ok, why] = this.radiusReply(name);
        if (!ok) { tried.push(why); continue; }
        const ws = this.world.radius.servers.find(x => x.ip === this.radiusServers[name].ip);
        const user = ws.users.find(u => u.name === eap.user);
        if (!user || user.password !== eap.password) { res.reasons.push('Access-Reject von ' + name + ': Benutzername oder Passwort falsch'); return [false, null]; }
        return [true, user];
      }
      res.reasons.push('Kein RADIUS-Server der Group ' + mm.group + ' antwortet: ' + tried.join('; '));
      return [false, null];
    }

    decide(client) {
      const ap = this.apByName(client.ap);
      const res = { state: 'Not Associated', ap: client.ap, wlan: null, policy: null, vlan: null, method: null,
                    switching: null, mode: null, roam: null, reasons: [] };
      if (!ap || !ap.joined) { res.reasons.push('AP ' + client.ap + ' ist nicht am Controller registriert'); return res; }
      let wl = null;
      for (const [n, w] of this.wlans) if (w.ssid === client.ssid) { wl = n; break; }
      if (wl === null) { res.reasons.push('Kein WLAN-Profil mit SSID ' + client.ssid + ' konfiguriert'); return res; }
      const w = this.wlans.get(wl);
      const tag = this.policyTagOf(ap);
      const pol = get(get(this.policyTags, tag) || dict(), wl);
      if (pol === undefined) {
        res.reasons.push('Das Policy Tag ' + tag + ' von ' + ap.name + ' enthaelt das WLAN ' + wl + ' nicht - die SSID wird an diesem AP nicht ausgestrahlt');
        return res;
      }
      if (w.shutdown) { res.reasons.push('WLAN-Profil ' + wl + ' ist administrativ down (shutdown)'); return res; }
      const p = get(this.policies, pol);
      if (p === undefined) { res.reasons.push('Policy Profile ' + pol + ' im Policy Tag ' + tag + ' existiert nicht'); return res; }
      if (p.shutdown) { res.reasons.push('Policy Profile ' + pol + ' ist administrativ down (shutdown)'); return res; }
      const central = has(p, 'central') ? p.central : true;
      res.wlan = w.id; res.policy = pol; res.switching = central ? 'central' : 'local'; res.mode = this.apMode(ap);
      if (central) {
        if (!isDigits(p.vlan)) {
          res.reasons.push('VLAN ' + p.vlan + ' ist am Controller nicht definiert (der Simulator kennt fuer zentrales Switching nur numerische VLAN-IDs)');
          return res;
        }
        res.vlan = String(p.vlan);
      } else {
        if (res.mode !== 'FlexConnect') {
          res.reasons.push('Policy Profile ' + pol + ' schaltet lokal (no central switching), der AP ' + ap.name + ' arbeitet aber im Local Mode - ' +
                           'lokales Switching setzt den FlexConnect-Modus voraus (Site Tag ohne Local Site)');
          return res;
        }
        const fname = this.flexOf(ap);
        const vid = Wlc.flexVlan(get(this.flexProfiles, fname), p.vlan);
        if (vid === null) {
          res.reasons.push('Das VLAN ' + p.vlan + ' des Policy Profile ' + pol + ' ist im Flex Profile ' + fname +
                           ' nicht definiert (der Name muss exakt passen) - die Clients koennen sich nicht verbinden');
          return res;
        }
        res.vlan = String(vid);
      }
      if (w.akm === 'psk') {
        res.method = 'PSK';
        if (client.psk !== w.psk) { res.reasons.push('Pre-Shared Key stimmt nicht - die Authentifizierung scheitert'); return res; }
      } else if (w.akm === 'dot1x') {
        res.method = 'Dot1x';
        const [ok, user] = this._dot1x(client, w, res);
        if (!ok) return res;
        // VLAN per RADIUS (Attribute 64/65/81): nur mit aaa-override im Policy Profile, sonst gilt das VLAN des Policy Profile
        if ((has(p, 'aaa_override') ? p.aaa_override : false) && user.vlan) {
          const v = String(user.vlan);
          if (central) {
            if (!isDigits(v)) {
              res.reasons.push('Das von RADIUS gelieferte VLAN ' + v + ' ist am Controller nicht definiert (der Simulator kennt fuer zentrales Switching nur numerische VLAN-IDs)');
              return res;
            }
            res.vlan = v;
          } else {
            const vid = Wlc.flexVlan(get(this.flexProfiles, this.flexOf(ap)), v);
            if (vid === null) {
              res.reasons.push('Das von RADIUS gelieferte VLAN ' + v + ' ist im Flex Profile ' + this.flexOf(ap) + ' nicht definiert - der Client kann sich nicht verbinden');
              return res;
            }
            res.vlan = String(vid);
          }
        }
      } else res.method = 'None';
      if (w.webauth) {
        if (res.method === 'None') res.method = 'Web Auth';
        if (!this._webauth(client, w, res)) { res.state = 'Webauth Pending'; return res; }
      }
      if (client.roam) this._roam(client, w, res);
      res.state = 'Run';
      return res;
    }

    mobilityTunnel(ip) {
      /* Zustand des Mobility-Tunnels zu einem konfigurierten Peer (Simulator-Modell): Control und Data Path kommen nur hoch, wenn beide Seiten passen. */
      const pr = get(this.mobilityPeers, ip);
      const down = why => ({ control: 'Down', data: 'Down', reason: why });
      if (!pr) return down('Peer ' + ip + ' ist nicht konfiguriert');
      const ctl = (((this.world.mobility || {}).controllers) || []).find(x => x.ip === ip);
      if (!ctl || !ctl.up) return down('Der Controller ' + ip + ' antwortet nicht');
      if (pr.mac !== ctl.mac) return down('Die MAC-Adresse ' + pr.mac + ' stimmt nicht mit der des Controllers ' + ctl.name + ' (' + ctl.mac + ') ueberein');
      if (pr.group !== ctl.group) return down('Der Gruppenname ' + pr.group + ' im Peer-Eintrag stimmt nicht: Der Controller ' + ctl.name + ' gehoert zur Gruppe ' + ctl.group);
      const kn = ctl.knows || {};
      if (kn.ip !== this.world.wlc.ip || kn.mac !== this.world.wlc.mac) return down('Der Controller ' + ctl.name + ' hat diesen Controller nicht oder mit falscher IP/MAC eingetragen');
      if (kn.group !== this.mobilityGroup) return down('Der Controller ' + ctl.name + ' erwartet diesen Controller in der Gruppe ' + pyStr(kn.group) + ', hier ist ' + this.mobilityGroup + ' konfiguriert');
      return { control: 'Up', data: 'Up', reason: '' };
    }

    _roam(client, w, res) {
      const ip = isDict(client.roam) ? client.roam.from : null;
      const ctl = (((this.world.mobility || {}).controllers) || []).find(x => x.ip === ip);
      const tun = this.mobilityTunnel(ip);
      if (tun.control !== 'Up') { res.reasons.push('Kein Roaming vom Controller ' + ip + ': ' + tun.reason + '. Der Client verbindet sich als neue Sitzung'); return; }
      if (ctl.wlans[client.ssid] !== w.akm) {
        res.reasons.push('Kein Roaming vom Controller ' + ctl.name + ': Die Sicherheit der SSID ' + client.ssid + ' dort (' + (has(ctl.wlans, client.ssid) ? ctl.wlans[client.ssid] : 'nicht vorhanden') +
                         ') weicht von hier (' + w.akm + ') ab. Der Client verbindet sich als neue Sitzung');
        return;
      }
      res.roam = 'Inter-Controller';
    }

    _webauth(client, w, res) {
      const lst = w.webauth_list || '';
      if (!lst) { res.reasons.push('Am WLAN-Profil ist keine Web-Auth-Authentication-List gesetzt (security web-auth authentication-list)'); return false; }
      if (!has(this.loginLists, lst)) { res.reasons.push('Die Authentication List ' + lst + ' ist nicht definiert (aaa authentication login ' + lst + ' local)'); return false; }
      const pm = w.webauth_map || '';
      if (!pm) { res.reasons.push('Am WLAN-Profil ist keine Parameter Map gesetzt (security web-auth parameter-map)'); return false; }
      if (!has(this.webauthMaps, pm)) { res.reasons.push('Die Parameter Map ' + pm + ' ist nicht definiert (parameter-map type webauth)'); return false; }
      if (!this.authzDefaultLocal) {
        res.reasons.push('Die Autorisierung fehlt: aaa authorization network default local ist nicht konfiguriert, die lokale Anmeldung am Portal funktioniert ohne sie nicht');
        return false;
      }
      const cred = client.web;
      if (!cred || !Object.keys(cred).length) { res.reasons.push('Der Client hat sich noch nicht am Web-Portal angemeldet (Zustand Webauth Pending)'); return false; }
      if (!has(this.localUsers, cred.user) || this.localUsers[cred.user] !== cred.password) {
        res.reasons.push('Anmeldung am Portal abgelehnt: Benutzername oder Passwort falsch');
        return false;
      }
      return true;
    }

    clients() { return this.world.clients.map(c => Object.assign({}, c, this.decide(c))); }

    // ---- Show-Ausgaben (Format belegt, siehe docs/QUELLEN.md)
    showWlanSummary() {
      const rows = [...this.wlans.entries()].sort((x, y) => x[1].id - y[1].id);
      const out = ['Number of WLANs: ' + rows.length, '',
        'ID   Profile Name                     SSID                             Status Security', '-'.repeat(154)];
      for (const [n, w] of rows) {
        out.push(pad(w.id, 4) + ' ' + pad(n, 32) + ' ' + pad(w.ssid, 32) + ' ' + pad(w.shutdown ? 'DOWN' : 'UP', 6) + ' ' +
                 Wlc.securityOf(w));
      }
      return out.join('\n');
    }
    showApSummary() {
      const aps = this.world.aps.filter(a => a.joined);
      const out = ['Number of APs: ' + aps.length, '',
        'AP Name                            Slots    AP Model  Ethernet MAC    Radio MAC       Location' +
        '                          Country     IP Address                                 State', '-'.repeat(163)];
      for (const a of aps) {
        out.push([pad(a.name, 34), pad(2, 8), pad(a.model, 9), pad(a.ethMac, 15), pad(a.radioMac, 15), pad(a.location, 33),
                  pad(a.country, 11), pad(a.ip, 42), 'Registered'].join(' '));
      }
      return out.join('\n');
    }
    showApTagSummary() {
      const aps = this.world.aps.filter(a => a.joined);
      const out = ['Number of APs: ' + aps.length, '',
        'AP Name                 AP Mac           Site Tag Name                     Policy Tag Name' +
        '                   RF Tag Name                       Misconfigured    Tag Source', '-'.repeat(172)];
      for (const a of aps) {
        const cfg = get(this.apCfg, a.ethMac) || {};
        out.push([pad(a.name, 23), pad(a.ethMac, 16), pad(this.siteTagOf(a), 33), pad(this.policyTagOf(a), 33), pad(this.rfTagOf(a), 33),
                  pad('No', 16), (cfg.policy_tag || cfg.site_tag || cfg.rf_tag) ? 'Static' : 'Default'].join(' '));
      }
      return out.join('\n');
    }
    showWirelessClientSummary() {
      const cl = this.clients().filter(c => c.state !== 'Not Associated');
      const out = ['Number of Clients: ' + cl.length, '',
        'MAC Address    AP Name                                        Type ID   State             Protocol Method     Role', '-'.repeat(121)];
      for (const c of cl) {
        out.push([pad(c.mac, 14), pad(c.ap, 46), pad('WLAN', 4), pad(c.wlan, 4), pad(c.state, 17), pad(c.protocol, 8), pad(c.method, 10), 'Local'].join(' '));
      }
      return out.join('\n');
    }
    nameDescTable(title, header, rows) {
      const out = ['Number of ' + title + ': ' + rows.length, '', pad(header, 33) + ' Description', '-'.repeat(72)];
      for (const [n, d] of rows) out.push((pad(n, 33) + ' ' + d).replace(/\s+$/, ''));
      return out.join('\n');
    }
    showFlexSummary() { return this.nameDescTable('Flex Profiles', 'Flex Profile Name', sortedKeys(this.flexProfiles).map(n => [n, this.flexProfiles[n].descr])); }
    showSiteTagSummary() { return this.nameDescTable('Site Tags', 'Site Tag Name', sortedKeys(this.siteTags).map(n => [n, this.siteTags[n].descr])); }
    showMobilitySummary() {
      const w = this.world.wlc;
      const out = ['Mobility Summary', '', 'Wireless Management IP Address: ' + w.ip, 'Mobility Control Message DSCP Value: 48', 'Mobility Keepalive Interval/Count: 10/3',
                   'Mobility Group Name: ' + this.mobilityGroup, 'Mobility MAC Address: ' + w.mac, '',
                   'Number of Mobility Peers (Simulator-Format): ' + Object.keys(this.mobilityPeers).length];
      if (Object.keys(this.mobilityPeers).length) {
        out.push('', 'IP Address        MAC Address     Group Name                        Control Path  Data Path', '-'.repeat(90));
        for (const ip of sortedKeys(this.mobilityPeers)) {
          const p = this.mobilityPeers[ip], t = this.mobilityTunnel(ip);
          out.push(pad(ip, 17) + ' ' + pad(p.mac, 15) + ' ' + pad(p.group, 33) + ' ' + pad(t.control, 13) + ' ' + t.data);
        }
      }
      return out.join('\n');
    }
    showAaaServers() {
      /* Nur Zeilen, deren Format der genieparser-Parser kennt; das Geraet gibt weitere aus. Die Dauern sind simuliert. */
      const out = [];
      sortedKeys(this.radiusServers).forEach((n, i) => {
        const r = this.radiusServers[n];
        const up = this.radiusReply(n)[0];
        out.push('RADIUS: id ' + (i + 1) + ', priority 1, host ' + (r.ip || '0.0.0.0') + ', auth-port ' + r.auth_port + ', acct-port ' + r.acct_port + ', hostname ' + n,
                 '  State: current ' + (up ? 'UP' : 'DEAD') + ', duration 600s, previous duration 0s',
                 '  Dead: total time ' + (up ? '0s' : '600s') + ', count ' + (up ? 0 : 1),
                 '  Quarantined: No');
      });
      return out.join('\n');
    }
    showPolicySummary() {
      const names = sortedKeys(this.policies);
      const out = ['Number of Policy Profiles: ' + names.length, '',
        'Policy Profile Name               Description                             Status', '-'.repeat(89)];
      for (const n of names) {
        const p = this.policies[n];
        out.push(pad(n, 33) + ' ' + pad(p.descr || 'Not required', 39) + ' ' + (p.shutdown ? 'DISABLED' : 'ENABLED'));
      }
      return out.join('\n');
    }
  }

  // ------------------------------------------------------------------ CLI
  const PROMPTS = { exec: '#', config: '(config)#', wlan: '(config-wlan)#', policy: '(config-wireless-policy)#', ptag: '(config-policy-tag)#',
                    ap: '(config-ap)#', flex: '(config-wireless-flex-profile)#', flexvlan: '(config-wireless-flex-profile-vlan)#', stag: '(config-site-tag)#',
                    radius: '(config-radius-server)#', aaagrp: '(config-sg-radius)#', pmap: '(config-params-parameter-map)#',
                    rfprof: '(config-rf-profile)#', rftag: '(config-rf-tag)#' };
  const isIpv4 = v => { const p = v.split('.'); return p.length === 4 && p.every(x => isDigits(x) && x.length <= 3 && parseInt(x, 10) <= 255); };
  const eq = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
  const startsWith = (w, p) => w.length >= p.length && p.every((x, i) => w[i] === x);

  class Cli {
    constructor(wlc) { this.wlc = wlc; this.mode = 'exec'; this.ctx = null; this.ctx2 = null; }
    get prompt() { return this.wlc.world.wlc.hostname + PROMPTS[this.mode]; }

    run(line) {
      try { return this._run(line.trim()); } catch (e) { if (e instanceof CliError) return '% ' + e.message; throw e; }
    }

    _run(line) {
      if (!line) return '';
      const w = line.split(/\s+/);
      if (w[0] === 'end') { this.mode = 'exec'; this.ctx = null; this.ctx2 = null; return ''; }
      if (w[0] === 'exit') {
        if (this.mode === 'flexvlan') { this.mode = 'flex'; this.ctx2 = null; return ''; }
        this.mode = this.mode !== 'exec' && this.mode !== 'config' ? 'config' : 'exec';
        this.ctx = null; this.ctx2 = null;
        return '';
      }
      if (w[0] === 'show' || (w[0] === 'do' && w.length > 1 && w[1] === 'show')) return this._show((w[0] === 'show' ? w.slice(1) : w.slice(2)).join(' '));
      if (this.mode === 'exec') {
        if (['configure terminal', 'conf t', 'configure t'].includes(line)) { this.mode = 'config'; return 'Enter configuration commands, one per line.  End with CNTL/Z.'; }
        throw new CliError('Invalid input detected: "' + line + '"');
      }
      return this._config(w);
    }

    _show(cmd) {
      const c = this.wlc;
      const m = { 'wlan summary': () => c.showWlanSummary(), 'ap summary': () => c.showApSummary(), 'ap tag summary': () => c.showApTagSummary(),
                  'wireless client summary': () => c.showWirelessClientSummary(), 'wireless profile policy summary': () => c.showPolicySummary(),
                  'wireless profile flex summary': () => c.showFlexSummary(), 'wireless tag site summary': () => c.showSiteTagSummary(),
                  'aaa servers': () => c.showAaaServers(), 'wireless mobility summary': () => c.showMobilitySummary() };
      if (!has(m, cmd)) throw new CliError('Der Befehl "show ' + cmd + '" ist in diesem Simulator (noch) nicht belegt/umgesetzt');
      return m[cmd]();
    }

    _flex(w, no) {
      const fp = this.wlc.flexProfiles[this.ctx];
      const bad = () => new CliError('Invalid input detected: "' + w.join(' ') + '"');
      if (w[0] === 'vlan-id' && this.mode === 'flexvlan' && (w.length === 2 || (no && w.length === 1))) {
        if (no) { fp.vlans[this.ctx2] = null; return ''; }
        if (!isDigits(w[1]) || !(parseInt(w[1], 10) >= 1 && parseInt(w[1], 10) <= 4094)) throw new CliError('VLAN-ID muss 1-4094 sein');
        fp.vlans[this.ctx2] = parseInt(w[1], 10);
        return '';
      }
      if (w[0] === 'native-vlan-id' && (w.length === 2 || (no && w.length === 1))) {
        if (no) fp.native = null;
        else if (isDigits(w[1]) && parseInt(w[1], 10) >= 1 && parseInt(w[1], 10) <= 4094) fp.native = parseInt(w[1], 10);
        else throw new CliError('VLAN-ID muss 1-4094 sein');
        this.mode = 'flex'; this.ctx2 = null;
        return '';
      }
      if (w[0] === 'vlan-name' && w.length === 2) {
        if (no) {
          if (!has(fp.vlans, w[1])) throw new CliError('VLAN-Name ' + w[1] + ' existiert im Flex Profile nicht');
          delete fp.vlans[w[1]];
          this.mode = 'flex'; this.ctx2 = null;
          return '';
        }
        if (!has(fp.vlans, w[1]) && !NAME_RE.test(w[1])) throw new CliError('VLAN-Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
        setdefault(fp.vlans, w[1], null);
        this.mode = 'flexvlan'; this.ctx2 = w[1];
        return '';
      }
      if (w[0] === 'description' && w.length > 1 && !no) { fp.descr = w.slice(1).join(' '); return ''; }
      throw bad();
    }

    _config(w) {
      const c = this.wlc;
      const no = w[0] === 'no';
      if (no) w = w.slice(1);
      if (!w.length) throw new CliError('Invalid input detected: "no"');
      const inv = () => new CliError('Invalid input detected: "' + w.join(' ') + '"');
      // Das Objekt des aktuellen Untermodus kann inzwischen (z. B. ueber die Oberflaeche) geloescht worden sein
      const store = { wlan: null, policy: c.policies, ptag: c.policyTags, flex: c.flexProfiles, flexvlan: c.flexProfiles, stag: c.siteTags,
                      radius: c.radiusServers, aaagrp: c.aaaGroups, pmap: c.webauthMaps, rfprof: c.rfProfiles, rftag: c.rfTags };
      if (this.mode === 'wlan' ? !c.wlans.has(this.ctx) : (has(store, this.mode) && store[this.mode] && !has(store[this.mode], this.ctx))) {
        this.mode = 'config'; this.ctx = null; this.ctx2 = null;
        throw new CliError('Das Objekt existiert nicht mehr');
      }
      if (this.mode === 'config') {
        if (w[0] === 'wlan' && w.length === 4 && !no) {
          if (!isDigits(w[2]) || !(parseInt(w[2], 10) >= 1 && parseInt(w[2], 10) <= 4096)) throw new CliError('WLAN-ID muss 1-4096 sein');
          const id = parseInt(w[2], 10);
          for (const [n, x] of c.wlans) if (n !== w[1] && x.id === id) throw new CliError('WLAN-ID ' + w[2] + ' ist bereits vergeben');
          if (!c.wlans.has(w[1])) c.wlans.set(w[1], { id, ssid: w[3], shutdown: true, akm: 'open', psk: '', authlist: '' });
          this.mode = 'wlan'; this.ctx = w[1];
          return '';
        }
        if (startsWith(w, ['wireless', 'profile', 'policy']) && w.length === 4 && !no) {
          setdefault(c.policies, w[3], { vlan: '1', shutdown: true, descr: '' });
          this.mode = 'policy'; this.ctx = w[3];
          return '';
        }
        if (startsWith(w, ['wireless', 'tag', 'policy']) && w.length === 4 && !no) {
          setdefault(c.policyTags, w[3], dict());
          this.mode = 'ptag'; this.ctx = w[3];
          return '';
        }
        if (w[0] === 'ap' && w.length === 2 && !no) {
          let eth;
          try { eth = normMac(w[1]); } catch (e) { throw new CliError(e.message); }
          setdefault(c.apCfg, eth, dict());
          this.mode = 'ap'; this.ctx = eth;
          return '';
        }
        if (startsWith(w, ['wireless', 'profile', 'flex']) && w.length === 4 && !no) {
          if (!has(c.flexProfiles, w[3]) && !NAME_RE.test(w[3])) throw new CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
          setdefault(c.flexProfiles, w[3], newFlex());
          this.mode = 'flex'; this.ctx = w[3];
          return '';
        }
        if (startsWith(w, ['wireless', 'tag', 'site']) && w.length === 4 && !no) {
          if (!has(c.siteTags, w[3]) && !NAME_RE.test(w[3])) throw new CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
          setdefault(c.siteTags, w[3], newSite());
          this.mode = 'stag'; this.ctx = w[3];
          return '';
        }
        if (w[0] === 'username' && !no && [4, 5, 6, 7].includes(w.length)) {
          let i = 2;
          if (w[i] === 'privilege' && w.length >= 6 && isDigits(w[3]) && parseInt(w[3], 10) >= 0 && parseInt(w[3], 10) <= 15) i = 4;
          if ((w.length - i === 2 || w.length - i === 3) && w[i] === 'password' && (w.length - i === 2 || w[i + 1] === '0')) {
            if (!NAME_RE.test(w[1])) throw new CliError('Benutzername: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
            c.localUsers[w[1]] = w[w.length - 1];
            return '';
          }
          throw inv();
        }
        if (no && w[0] === 'username' && w.length === 2) {
          if (!has(c.localUsers, w[1])) throw new CliError('Benutzer ' + w[1] + ' existiert nicht');
          delete c.localUsers[w[1]];
          return '';
        }
        if (startsWith(w, ['aaa', 'authentication', 'login']) && w.length === 5 && w[4] === 'local' && !no) {
          if (!NAME_RE.test(w[3])) throw new CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
          c.loginLists[w[3]] = { method: 'local' };
          return '';
        }
        if (no && startsWith(w, ['aaa', 'authentication', 'login']) && w.length === 4) {
          if (!has(c.loginLists, w[3])) throw new CliError('Authentication List ' + w[3] + ' existiert nicht');
          const users = [...c.wlans.keys()].filter(n => (c.wlans.get(n).webauth_list || undefined) === w[3]).sort(cmp);
          if (users.length) throw new CliError('Authentication List ' + w[3] + ' wird von WLANs verwendet (' + users.join(', ') + ') - zuerst dort entfernen');
          delete c.loginLists[w[3]];
          return '';
        }
        if (eq(w, ['aaa', 'authorization', 'network', 'default', 'local']) || (no && startsWith(w, ['aaa', 'authorization', 'network', 'default']))) {
          c.authzDefaultLocal = !no;
          return '';
        }
        if (startsWith(w, ['parameter-map', 'type', 'webauth']) && w.length === 4 && !no) {
          if (!has(c.webauthMaps, w[3]) && !NAME_RE.test(w[3])) throw new CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
          setdefault(c.webauthMaps, w[3], { type: 'webauth', virtual_ip: '' });
          this.mode = 'pmap'; this.ctx = w[3];
          return '';
        }
        if (no && startsWith(w, ['parameter-map', 'type', 'webauth']) && w.length === 4) {
          if (w[3] === DEF_WEBAUTH_MAP) throw new CliError(DEF_WEBAUTH_MAP + ' ist vordefiniert und kann nicht geloescht werden');
          if (!has(c.webauthMaps, w[3])) throw new CliError('Parameter Map ' + w[3] + ' existiert nicht');
          const users = [...c.wlans.keys()].filter(n => (c.wlans.get(n).webauth_map || undefined) === w[3]).sort(cmp);
          if (users.length) throw new CliError('Parameter Map ' + w[3] + ' wird von WLANs verwendet (' + users.join(', ') + ') - zuerst dort entfernen');
          delete c.webauthMaps[w[3]];
          return '';
        }
        if (startsWith(w, ['ap', 'dot11']) && has(RF_BANDS, w[2]) && w.length === 5 && w[3] === 'rf-profile' && !no) {
          const known = sortedKeys(c.rfProfiles).some(k => c.rfProfiles[k].band === w[2] && c.rfProfiles[k].name === w[4]);
          if (!known && !NAME_RE.test(w[4])) throw new CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
          const key = w[2] + ':' + w[4];
          setdefault(c.rfProfiles, key, { band: w[2], name: w[4], shutdown: true, tx_min: null, tx_max: null, descr: '' });
          this.mode = 'rfprof'; this.ctx = key;
          return '';
        }
        if (no && startsWith(w, ['ap', 'dot11']) && w.length === 5 && has(RF_BANDS, w[2]) && w[3] === 'rf-profile') {
          const key = w[2] + ':' + w[4];
          if (!has(c.rfProfiles, key)) throw new CliError('RF-Profil ' + w[4] + ' existiert fuer ' + RF_BANDS[w[2]] + ' nicht');
          const users = sortedKeys(c.rfTags).filter(n => c.rfTags[n][w[2]] === w[4]);
          if (users.length) throw new CliError('RF-Profil ' + w[4] + ' wird von RF Tags verwendet (' + users.join(', ') + ') - zuerst dort entfernen');
          delete c.rfProfiles[key];
          return '';
        }
        if (startsWith(w, ['wireless', 'tag', 'rf']) && w.length === 4 && !no) {
          if (!has(c.rfTags, w[3]) && !NAME_RE.test(w[3])) throw new CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
          setdefault(c.rfTags, w[3], { '24ghz': '', '5ghz': '' });
          this.mode = 'rftag'; this.ctx = w[3];
          return '';
        }
        if (no && startsWith(w, ['wireless', 'tag', 'rf']) && w.length === 4) {
          if (w[3] === DEF_RF_TAG) throw new CliError(DEF_RF_TAG + ' ist vordefiniert und kann nicht geloescht werden');
          if (!has(c.rfTags, w[3])) throw new CliError('RF Tag ' + w[3] + ' existiert nicht');
          const aps = c.world.aps.filter(a => c.rfTagOf(a) === w[3]).map(a => a.name).sort(cmp);
          if (aps.length) throw new CliError('RF Tag ' + w[3] + ' ist APs zugewiesen (' + aps.join(', ') + ') - zuerst dort entfernen');
          delete c.rfTags[w[3]];
          return '';
        }
        if (startsWith(w, ['wireless', 'mobility', 'group', 'name']) && w.length === 5 && !no) {
          if (!NAME_RE.test(w[4])) throw new CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
          c.mobilityGroup = w[4];
          return '';
        }
        if (startsWith(w, ['wireless', 'mobility', 'group', 'member', 'mac-address']) && w.length === 10 && w[6] === 'ip' && w[8] === 'group' && !no) {
          let mac;
          try { mac = normMac(w[5]); } catch (e) { throw new CliError(e.message); }
          if (!isIpv4(w[7])) throw new CliError('IPv4-Adresse ungueltig: ' + w[7]);
          if (!NAME_RE.test(w[9])) throw new CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
          if (w[7] === c.world.wlc.ip) throw new CliError('Die eigene Adresse kann kein Mobility-Peer sein');
          c.mobilityPeers[w[7]] = { mac, group: w[9] };
          return '';
        }
        if (no && startsWith(w, ['wireless', 'mobility', 'group', 'member', 'ip']) && w.length === 6) {
          if (!has(c.mobilityPeers, w[5])) throw new CliError('Mobility-Peer ' + w[5] + ' existiert nicht');
          delete c.mobilityPeers[w[5]];
          return '';
        }
        if (eq(w, ['aaa', 'new-model'])) return '';   // AAA ist im Simulator immer aktiv; der Befehl wird angenommen
        if (startsWith(w, ['radius', 'server']) && w.length === 3 && !no) {
          if (!has(c.radiusServers, w[2]) && !NAME_RE.test(w[2])) throw new CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
          setdefault(c.radiusServers, w[2], { ip: '', auth_port: 1812, acct_port: 1813, key: '', timeout: 5, retransmit: 3 });
          this.mode = 'radius'; this.ctx = w[2];
          return '';
        }
        if (startsWith(w, ['aaa', 'group', 'server', 'radius']) && w.length === 5 && !no) {
          if (!has(c.aaaGroups, w[4]) && !NAME_RE.test(w[4])) throw new CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
          setdefault(c.aaaGroups, w[4], { servers: [] });
          this.mode = 'aaagrp'; this.ctx = w[4];
          return '';
        }
        if (startsWith(w, ['aaa', 'authentication', 'dot1x']) && w.length === 6 && w[4] === 'group' && !no) {
          if (!NAME_RE.test(w[3])) throw new CliError('Name: 1-32 Zeichen (Buchstaben, Ziffern, . _ -)');
          if (!has(c.aaaGroups, w[5])) throw new CliError('Server Group ' + w[5] + ' existiert nicht');
          c.aaaLists[w[3]] = { group: w[5] };
          return '';
        }
        if (no && startsWith(w, ['aaa', 'authentication', 'dot1x']) && w.length === 4) {
          if (!has(c.aaaLists, w[3])) throw new CliError('Authentication List ' + w[3] + ' existiert nicht');
          const users = [...c.wlans.keys()].filter(n => (c.wlans.get(n).authlist || undefined) === w[3]).sort(cmp);
          if (users.length) throw new CliError('Authentication List ' + w[3] + ' wird von WLANs verwendet (' + users.join(', ') + ') - zuerst dort entfernen');
          delete c.aaaLists[w[3]];
          return '';
        }
        if (no && startsWith(w, ['aaa', 'group', 'server', 'radius']) && w.length === 5) {
          if (!has(c.aaaGroups, w[4])) throw new CliError('Server Group ' + w[4] + ' existiert nicht');
          const users = sortedKeys(c.aaaLists).filter(n => c.aaaLists[n].group === w[4]);
          if (users.length) throw new CliError('Server Group ' + w[4] + ' wird von Authentication Lists verwendet (' + users.join(', ') + ') - zuerst dort entfernen');
          delete c.aaaGroups[w[4]];
          return '';
        }
        if (no && startsWith(w, ['radius', 'server']) && w.length === 3) {
          if (!has(c.radiusServers, w[2])) throw new CliError('RADIUS-Server ' + w[2] + ' existiert nicht');
          const users = sortedKeys(c.aaaGroups).filter(n => c.aaaGroups[n].servers.includes(w[2]));
          if (users.length) throw new CliError('RADIUS-Server ' + w[2] + ' ist in Server Groups eingetragen (' + users.join(', ') + ') - zuerst dort entfernen');
          delete c.radiusServers[w[2]];
          return '';
        }
        if (no && startsWith(w, ['wireless', 'profile', 'flex']) && w.length === 4) {
          if (w[3] === DEF_FLEX_PROFILE) throw new CliError(DEF_FLEX_PROFILE + ' ist vordefiniert und kann nicht geloescht werden');
          if (!has(c.flexProfiles, w[3])) throw new CliError('Flex Profile ' + w[3] + ' existiert nicht');
          const users = sortedKeys(c.siteTags).filter(n => c.siteTags[n].flex === w[3]);
          if (users.length) throw new CliError('Flex Profile ' + w[3] + ' wird von Site Tags verwendet (' + users.join(', ') + ') - zuerst dort entfernen');
          delete c.flexProfiles[w[3]];
          return '';
        }
        if (no && startsWith(w, ['wireless', 'tag', 'site']) && w.length === 4) {
          if (w[3] === DEF_SITE_TAG) throw new CliError(DEF_SITE_TAG + ' ist vordefiniert und kann nicht geloescht werden');
          if (!has(c.siteTags, w[3])) throw new CliError('Site Tag ' + w[3] + ' existiert nicht');
          const aps = c.world.aps.filter(a => c.siteTagOf(a) === w[3]).map(a => a.name).sort(cmp);
          if (aps.length) throw new CliError('Site Tag ' + w[3] + ' ist APs zugewiesen (' + aps.join(', ') + ') - zuerst dort entfernen');
          delete c.siteTags[w[3]];
          return '';
        }
        if (no && w[0] === 'wlan' && w.length === 2) {
          if (!c.wlans.has(w[1])) throw new CliError('WLAN-Profil ' + w[1] + ' existiert nicht');
          const users = sortedKeys(c.policyTags).filter(t => has(c.policyTags[t], w[1]));
          if (users.length) throw new CliError('WLAN-Profil ' + w[1] + ' ist in Policy Tags eingetragen (' + users.join(', ') + ') - zuerst dort entfernen');
          c.wlans.delete(w[1]);
          return '';
        }
        if (no && startsWith(w, ['wireless', 'profile', 'policy']) && w.length === 4) {
          if (!has(c.policies, w[3])) throw new CliError('Policy Profile ' + w[3] + ' existiert nicht');
          const users = sortedKeys(c.policyTags).filter(t => Object.keys(c.policyTags[t]).some(k => c.policyTags[t][k] === w[3]));
          if (users.length) throw new CliError('Policy Profile ' + w[3] + ' wird von Policy Tags verwendet (' + users.join(', ') + ') - zuerst dort entfernen');
          delete c.policies[w[3]];
          return '';
        }
        if (no && startsWith(w, ['wireless', 'tag', 'policy']) && w.length === 4) {
          if (w[3] === DEF_POLICY_TAG) throw new CliError(DEF_POLICY_TAG + ' ist vordefiniert und kann nicht geloescht werden');
          if (!has(c.policyTags, w[3])) throw new CliError('Policy Tag ' + w[3] + ' existiert nicht');
          const aps = c.world.aps.filter(a => c.policyTagOf(a) === w[3]).map(a => a.name).sort(cmp);
          if (aps.length) throw new CliError('Policy Tag ' + w[3] + ' ist APs zugewiesen (' + aps.join(', ') + ') - zuerst dort entfernen');
          delete c.policyTags[w[3]];
          return '';
        }
        throw inv();
      }
      if (this.mode === 'wlan') {
        const x = c.wlans.get(this.ctx);
        if (w[0] === 'shutdown') x.shutdown = !no;
        else if (startsWith(w, ['security', 'wpa', 'psk', 'set-key']) && w.length === 7 && w[4] === 'ascii') x.psk = w[6];
        else if (startsWith(w, ['security', 'wpa', 'akm']) && w.length === 4 && w[3] === 'psk') x.akm = no ? 'open' : 'psk';
        else if (startsWith(w, ['security', 'wpa', 'akm']) && w.length === 4 && w[3] === 'dot1x') x.akm = no ? 'open' : 'dot1x';
        else if (startsWith(w, ['security', 'dot1x', 'authentication-list']) && (w.length === 4 || (no && w.length === 3))) x.authlist = no ? '' : w[3];
        else if (eq(w, ['security', 'web-auth'])) { x.webauth = !no; if (no) { x.webauth_list = ''; x.webauth_map = ''; } }
        else if (startsWith(w, ['security', 'web-auth', 'authentication-list']) && (w.length === 4 || (no && w.length === 3))) x.webauth_list = no ? '' : w[3];
        else if (startsWith(w, ['security', 'web-auth', 'parameter-map']) && (w.length === 4 || (no && w.length === 3))) x.webauth_map = no ? '' : w[3];
        else throw inv();
        return '';
      }
      if (this.mode === 'policy') {
        const x = c.policies[this.ctx];
        if (w[0] === 'shutdown') x.shutdown = !no;
        else if (w[0] === 'vlan' && w.length === 2 && NAME_RE.test(w[1])) x.vlan = w[1];
        else if (eq(w, ['central', 'switching'])) x.central = !no;
        else if (eq(w, ['aaa-override'])) x.aaa_override = !no;
        else if (w[0] === 'description' && w.length > 1) x.descr = w.slice(1).join(' ');
        else throw inv();
        return '';
      }
      if (this.mode === 'ptag') {
        if (w[0] === 'wlan' && w.length === 4 && w[2] === 'policy') {
          if (no) delete c.policyTags[this.ctx][w[1]]; else c.policyTags[this.ctx][w[1]] = w[3];
          return '';
        }
        throw inv();
      }
      if (this.mode === 'flex' || this.mode === 'flexvlan') return this._flex(w, no);
      if (this.mode === 'radius') {
        const r = c.radiusServers[this.ctx];
        if (startsWith(w, ['address', 'ipv4']) && (w.length === 3 || w.length === 7) && !no) {
          if (!isIpv4(w[2])) throw new CliError('IPv4-Adresse ungueltig: ' + w[2]);
          if (w.length === 7) {
            if (w[3] !== 'auth-port' || w[5] !== 'acct-port' || !isDigits(w[4]) || !isDigits(w[6]) ||
                !(parseInt(w[4], 10) >= 1 && parseInt(w[4], 10) <= 65535 && parseInt(w[6], 10) >= 1 && parseInt(w[6], 10) <= 65535)) throw inv();
            r.auth_port = parseInt(w[4], 10); r.acct_port = parseInt(w[6], 10);
          }
          r.ip = w[2];
        } else if (w[0] === 'key' && !no && (w.length === 2 || (w.length === 3 && w[1] === '0'))) r.key = w[w.length - 1];
        else if ((w[0] === 'timeout' || w[0] === 'retransmit') && w.length === 2 && !no) {
          const hi = w[0] === 'timeout' ? 1000 : 100, lo = w[0] === 'retransmit' ? 0 : 1;
          if (!isDigits(w[1]) || !(lo <= parseInt(w[1], 10) && parseInt(w[1], 10) <= hi)) throw new CliError('Wert ausserhalb des Bereichs');
          r[w[0]] = parseInt(w[1], 10);
        } else throw inv();
        return '';
      }
      if (this.mode === 'pmap') {
        const m = c.webauthMaps[this.ctx];
        if (eq(w, ['type', 'webauth']) && !no) m.type = 'webauth';
        else if (startsWith(w, ['virtual-ip', 'ipv4']) && w.length === 3 && !no) {
          if (!isIpv4(w[2])) throw new CliError('IPv4-Adresse ungueltig: ' + w[2]);
          m.virtual_ip = w[2];
        } else if (no && startsWith(w, ['virtual-ip', 'ipv4'])) m.virtual_ip = '';
        else throw inv();
        return '';
      }
      if (this.mode === 'aaagrp') {
        const g = c.aaaGroups[this.ctx];
        if (startsWith(w, ['server', 'name']) && w.length === 3) {
          if (no) {
            if (!g.servers.includes(w[2])) throw new CliError('RADIUS-Server ' + w[2] + ' ist nicht in der Group');
            g.servers.splice(g.servers.indexOf(w[2]), 1);
          } else {
            if (!has(c.radiusServers, w[2])) throw new CliError('RADIUS-Server ' + w[2] + ' existiert nicht');
            if (!g.servers.includes(w[2])) g.servers.push(w[2]);
          }
          return '';
        }
        throw inv();
      }
      if (this.mode === 'stag') {
        const st = c.siteTags[this.ctx];
        if (w[0] === 'flex-profile' && (w.length === 2 || (no && w.length === 1))) {
          if (no) { st.flex = null; return ''; }
          if (st.local) throw new CliError('Das Flex Profile steht nur zur Verfuegung, wenn Local Site deaktiviert ist (no local-site)');
          if (!has(c.flexProfiles, w[1])) throw new CliError('Flex Profile ' + w[1] + ' existiert nicht');
          st.flex = w[1];
        } else if (eq(w, ['local-site'])) {
          st.local = !no;
          if (st.local) st.flex = null;
        } else if (w[0] === 'description' && w.length > 1 && !no) st.descr = w.slice(1).join(' ');
        else throw inv();
        return '';
      }
      if (this.mode === 'rfprof') {
        const x = c.rfProfiles[this.ctx];
        if (w[0] === 'shutdown' && w.length === 1) x.shutdown = !no;
        else if (w[0] === 'tx-power' && w.length === 3 && (w[1] === 'min' || w[1] === 'max') && !no) {
          if (!isDigits(w[2]) || !(parseInt(w[2], 10) >= 1 && parseInt(w[2], 10) <= 30)) throw new CliError('Sendeleistung: 1-30 dBm (Simulator-Wertebereich)');
          const v = parseInt(w[2], 10);
          const lo = w[1] === 'min' ? v : x.tx_min, hi = w[1] === 'min' ? x.tx_max : v;
          if (lo !== null && hi !== null && lo > hi) throw new CliError('tx-power min darf nicht groesser als tx-power max sein');
          x['tx_' + w[1]] = v;
        } else if (w[0] === 'tx-power' && w.length === 2 && (w[1] === 'min' || w[1] === 'max') && no) x['tx_' + w[1]] = null;
        else if (w[0] === 'description' && w.length > 1 && !no) x.descr = w.slice(1).join(' ');
        else throw inv();
        return '';
      }
      if (this.mode === 'rftag') {
        const t = c.rfTags[this.ctx];
        if ((w[0] === '24ghz-rf-policy' || w[0] === '5ghz-rf-policy') && (w.length === 2 || (no && w.length === 1))) {
          const band = w[0].slice(0, -'-rf-policy'.length);
          if (no) t[band] = '';
          else {
            if (!has(c.rfProfiles, band + ':' + w[1])) throw new CliError('RF-Profil ' + w[1] + ' existiert fuer ' + RF_BANDS[band] + ' nicht');
            t[band] = w[1];
          }
          return '';
        }
        throw inv();
      }
      if (this.mode === 'ap') {
        if (w[0] === 'rf-tag' && (w.length === 2 || (no && w.length === 1))) {
          if (no) delete c.apCfg[this.ctx].rf_tag;
          else {
            if (!has(c.rfTags, w[1])) throw new CliError('RF Tag ' + w[1] + ' existiert nicht');
            c.apCfg[this.ctx].rf_tag = w[1];
          }
          return '';
        }
        if (w[0] === 'site-tag' && (w.length === 2 || (no && w.length === 1))) {
          if (no) delete c.apCfg[this.ctx].site_tag;
          else {
            if (!has(c.siteTags, w[1])) throw new CliError('Site Tag ' + w[1] + ' existiert nicht');
            c.apCfg[this.ctx].site_tag = w[1];
          }
          return '';
        }
        if (w[0] === 'policy-tag' && (w.length === 2 || (no && w.length === 1))) {
          if (no) delete c.apCfg[this.ctx].policy_tag; else c.apCfg[this.ctx].policy_tag = w[1];
          return '';
        }
        throw inv();
      }
      throw new CliError('Invalid input detected');
    }
  }

  function applyCommands(wlc, commands) {
    /* Atomar: Bei einem Fehler wird die Konfiguration auf den Stand davor zurueckgesetzt. */
    const snap = wlc.snapshot();
    const cli = new Cli(wlc);
    const results = [];
    for (const line of ['configure terminal'].concat(commands, ['end'])) {
      const out = cli.run(line);
      results.push({ command: line, output: out });
      if (out.startsWith('% ')) { wlc.restore(snap); return [false, results, { command: line, message: out.slice(2) }]; }
    }
    return [true, results, null];
  }

  // ------------------------------------------------------------------ Persistenz
  function validateState(d) {
    if (!isDict(d) || d.kind !== KIND) throw new StoreError('Kein Campus-Prep-Stand');
    if (!ACCEPTED.includes(d.version)) throw new StoreError('Stand hat Version ' + pyStr(d.version) + ', erwartet wird ' + ACCEPTED.join(' oder '));
    const w = d.world, c = d.wlc;
    if (!isDict(w) || !isDict(w.wlc) || !Array.isArray(w.aps) || !Array.isArray(w.clients) || !isDict(c)) throw new StoreError('Stand ist unvollstaendig');
    for (const a of w.aps) {
      if (!isDict(a) || !['name', 'ethMac', 'radioMac', 'ip', 'model', 'joined'].every(k => has(a, k))) throw new StoreError('Stand: AP-Eintrag unvollstaendig');
    }
    for (const cl of w.clients) {
      if (!isDict(cl) || !['mac', 'ssid', 'ap', 'protocol'].every(k => has(cl, k))) throw new StoreError('Stand: Client-Eintrag unvollstaendig');
    }
    for (const k of ['wlans', 'policies', 'policyTags', 'apCfg']) if (!isDict(c[k])) throw new StoreError('Stand: ' + k + ' fehlt');
    return d;
  }
  function checkName(name) {
    if (typeof name !== 'string' || !STORE_NAME_RE.test(name)) throw new StoreError('Name: 1-40 Zeichen (Buchstaben, Ziffern, . _ -), beginnt mit Buchstabe oder Ziffer');
    return name;
  }

  class Store {
    /* storage: {get(key), set(key, text), remove(key), keys()} (Text-Speicher, z. B. localStorage). */
    constructor(storage) { this.s = storage; this.last = {}; this.P = 'campusprep:'; }
    write(key, obj) {
      const text = stableStringify(obj);
      if (this.last[key] === text) return;
      this.s.set(key, text); this.last[key] = text;
    }
    read(key) { const t = this.s.get(key); return t === null || t === undefined ? undefined : JSON.parse(t); }
    quarantine(key) { const t = this.s.get(key); if (t !== null && t !== undefined) this.s.set(key + '.bad', t); this.s.remove(key); delete this.last[key]; }

    writeState(d) { this.write(this.P + 'state', d); }
    readState() {
      const key = this.P + 'state';
      if (this.s.get(key) === null || this.s.get(key) === undefined) return null;
      try { return validateState(this.read(key)); } catch (e) { this.quarantine(key); return null; }
    }
    writeProgress(p) { this.write(this.P + 'progress', { kind: 'campusprep-progress', version: VERSION, labs: p }); }
    readProgress() {
      const key = this.P + 'progress';
      if (this.s.get(key) === null || this.s.get(key) === undefined) return {};
      try {
        const d = this.read(key);
        if (!(isDict(d) && d.kind === 'campusprep-progress' && ACCEPTED.includes(d.version) && isDict(d.labs))) throw new Error('Format');
        return d.labs;
      } catch (e) { this.quarantine(key); return {}; }
    }
    savePath(name) { return this.P + 'saves:' + checkName(name); }
    saveNamed(name, d) { this.write(this.savePath(name), d); }
    loadNamed(name) {
      const key = this.savePath(name);
      if (this.s.get(key) === null || this.s.get(key) === undefined) throw new StoreError('Stand ' + name + ' gibt es nicht', 404);
      let d;
      try { d = this.read(key); } catch (e) { throw new StoreError('Stand ' + name + ' ist nicht lesbar'); }
      return validateState(d);
    }
    deleteNamed(name) {
      const key = this.savePath(name);
      if (this.s.get(key) === null || this.s.get(key) === undefined) throw new StoreError('Stand ' + name + ' gibt es nicht', 404);
      this.s.remove(key); delete this.last[key];
    }
    listNamed() {
      const pre = this.P + 'saves:';
      const names = this.s.keys().filter(k => k.startsWith(pre)).map(k => k.slice(pre.length)).sort((a, b) => cmp(a + '.json', b + '.json'));
      return names.map(name => {
        try {
          const d = validateState(this.read(pre + name));
          return { name, lab: (d.lab || {}).id === undefined ? null : d.lab.id, wlans: Object.keys(d.wlc.wlans).length };
        } catch (e) { return { name, lab: null, wlans: 0, broken: true }; }
      });
    }
  }

  // ------------------------------------------------------------------ Labs
  function runCheck(chk, st) {
    const t = chk.type;
    const diff = (obj, attrs) => {
      const bad = {};
      for (const k of Object.keys(attrs)) if (obj[k] !== attrs[k] && !(obj[k] === undefined && attrs[k] === null)) bad[k] = obj[k] === undefined ? null : obj[k];
      return bad;
    };
    const fmtBad = bad => 'abweichend: ' + sortedKeys(bad).map(k => k + '=' + pyStr(bad[k])).join(', ');
    if (t === 'client') {
      const c = st.clients.find(x => x.mac === chk.mac);
      if (!c) return [false, 'Client ' + chk.mac + ' unbekannt'];
      const ok = c.state === chk.state && (chk.vlan === undefined || chk.vlan === null || String(c.vlan) === String(chk.vlan)) &&
                 (chk.switching === undefined || chk.switching === null || c.switching === chk.switching) &&
                 (chk.roam === undefined || chk.roam === null || c.roam === chk.roam);
      return [ok, 'Zustand ' + c.state + (c.vlan ? ', VLAN ' + c.vlan : '') + (c.state === 'Run' && c.switching ? ', ' + c.switching + ' geschaltet' : '')];
    }
    if (t === 'wlan') {
      const w = st.wlans.find(x => x.profile === chk.profile);
      if (!w) return [false, 'WLAN-Profil ' + chk.profile + ' fehlt'];
      const bad = diff(w, chk.attrs);
      return [!Object.keys(bad).length, Object.keys(bad).length ? fmtBad(bad) : 'passt'];
    }
    if (t === 'policy') {
      const p = st.policies.find(x => x.name === chk.name);
      if (!p) return [false, 'Policy Profile ' + chk.name + ' fehlt'];
      const bad = diff(p, chk.attrs);
      return [!Object.keys(bad).length, Object.keys(bad).length ? fmtBad(bad) : 'passt'];
    }
    if (t === 'aptag') {
      const a = st.aps.find(x => x.name === chk.ap);
      return [!!a && a.policyTag === chk.tag, 'Policy Tag ' + (a ? a.policyTag : '?')];
    }
    if (t === 'apmode') {
      const a = st.aps.find(x => x.name === chk.ap);
      return [!!a && a.mode === chk.mode, 'Modus ' + (a ? a.mode : '?')];
    }
    if (t === 'aprf') {
      const a = st.aps.find(x => x.name === chk.ap);
      const r = a ? a.rf[chk.band] : null;
      const ok = !!r && Object.keys(chk.attrs).every(k => r[k] === chk.attrs[k]);
      return [ok, !r ? 'nicht gefunden' : 'Profil ' + (r.profile || '-') + ', max. Sendeleistung ' + (r.txMax !== null ? r.txMax : 'automatisch') + ', Funk ' + r.radio];
    }
    if (t === 'mobilitypeer') {
      const pr = st.mobilityPeers.find(x => x.ip === chk.ip);
      return [!!pr && pr.control === 'Up' && pr.data === 'Up', 'Peer ' + chk.ip + ': ' + (!pr ? 'nicht konfiguriert' : 'Control ' + pr.control + ', Data ' + pr.data)];
    }
    if (t === 'wlanservers') {
      const got = (st._wlan_servers && st._wlan_servers[chk.profile]) || [];
      return [chk.servers.every(ip => got.includes(ip)), 'Server in der Kette: ' + (got.length ? got.join(', ') : 'keine')];
    }
    if (t === 'tagmap') {
      const tg = st.policyTags.find(x => x.name === chk.tag);
      const got = tg ? Object.fromEntries(tg.maps.map(m => [m.wlan, m.policy])) : null;
      return [got !== null && deepEqual(got, chk.maps), 'Zuordnung ' + (got !== null ? pyRepr(got) : 'Tag fehlt')];
    }
    if (t === 'absent') {
      const key = { wlan: ['wlans', 'profile'], policy: ['policies', 'name'], tag: ['policyTags', 'name'] }[chk.kind];
      const there = st[key[0]].some(x => x[key[1]] === chk.name);
      return [!there, there ? 'vorhanden' : 'entfernt'];
    }
    throw new Error('Pruefungstyp unbekannt: ' + t);
  }

  const emptyProgress = () => ({ starts: 0, checks: 0, passed: false, guidedPassed: false, examPassed: false, bestHints: null, questionsRight: 0 });

  class LabEngine {
    constructor(sim, labs) {
      this.sim = sim;
      this.labs = dict();
      for (const l of labs) this.labs[l.id] = l;
      this.session = null;
      this.progress = {};
    }
    prog(id) { return setdefault(this.progress, id, emptyProgress()); }
    list() {
      return Object.keys(this.labs).map(id => {
        const lab = this.labs[id];
        const d = {};
        for (const k of ['id', 'title', 'topic', 'level', 'duration', 'kind', 'modes']) d[k] = lab[k];
        d.track = lab.track;
        d.progress = Object.assign({}, has(this.progress, id) ? this.progress[id] : emptyProgress());
        return d;
      });
    }
    resetProgress() { this.progress = {}; }
    start(id, mode) {
      mode = mode === undefined ? 'guided' : mode;
      const lab = get(this.labs, id);
      if (!lab) throw new LabError('Lab ' + id + ' gibt es nicht', 404);
      if (!lab.modes.includes(mode)) throw new LabError('Modus ' + pyStr(mode) + ' ist fuer dieses Lab nicht vorgesehen');
      this.sim.resetWorld(lab.worldClients, lab.worldRadius, lab.worldMobility);
      const [ok, , err] = this.sim.apply(lab.startCommands || []);
      if (!ok) throw new LabError('Startkonfiguration von ' + id + ' fehlerhaft: ' + err.message, 500);
      this.session = { id, mode, hints: 0, answers: {}, checks: 0 };
      this.prog(id).starts += 1;
      return this.pub();
    }
    reset() { const s = this.need(); return this.start(s.id, s.mode); }
    stop() { this.session = null; }
    restoreSession(d) {
      this.session = null;
      if (!isDict(d) || !has(this.labs, d.id) || !MODES.includes(d.mode)) return;
      const lab = this.labs[d.id];
      const hints = Number.isInteger(d.hints) ? d.hints : 0;
      const answers = isDict(d.answers) ? d.answers : {};
      const qids = {};
      for (const q of lab.questions || []) qids[q.id] = q.options.length;
      const ans = {};
      for (const k of Object.keys(answers)) if (has(qids, k) && Number.isInteger(answers[k]) && answers[k] >= 0 && answers[k] < qids[k]) ans[k] = answers[k];
      this.session = { id: d.id, mode: d.mode, hints: Math.max(0, Math.min(hints, lab.hints.length)), answers: ans,
                       checks: Number.isInteger(d.checks) ? d.checks : 0 };
    }
    need() { if (this.session === null) throw new LabError('Es laeuft kein Lab', 409); return this.session; }
    pub() {
      if (this.session === null) return null;
      const s = this.session, lab = this.labs[s.id];
      const out = {};
      for (const k of Object.keys(lab)) if (!HIDDEN.includes(k)) out[k] = lab[k];
      const exam = s.mode === 'exam';
      return Object.assign(out, {
        mode: s.mode, hintsTotal: exam ? 0 : lab.hints.length, hintsUsed: s.hints, hints: exam ? [] : lab.hints.slice(0, s.hints), checksRun: s.checks,
        questions: (lab.questions || []).map(q => { const o = {}; for (const k of Object.keys(q)) if (k !== 'answer' && k !== 'explain') o[k] = q[k]; return o; }),
        answers: Object.assign({}, s.answers),
      });
    }
    hint() {
      const s = this.need(), lab = this.labs[s.id];
      if (s.mode === 'exam') throw new LabError('Im Prüfungsmodus gibt es keine Hinweise', 403);
      if (s.hints >= lab.hints.length) throw new LabError('Alle Hinweise sind bereits freigeschaltet', 409);
      s.hints += 1;
      return this.pub();
    }
    solution() {
      const s = this.need();
      if (s.mode === 'exam') throw new LabError('Im Prüfungsmodus gibt es keine Lösung', 403);
      return { solution: this.labs[s.id].solution };
    }
    answer(qid, idx) {
      const s = this.need();
      const q = (this.labs[s.id].questions || []).find(x => x.id === qid);
      if (!q || !Number.isInteger(idx) || !(idx >= 0 && idx < q.options.length)) throw new LabError('Frage oder Antwort ungueltig');
      s.answers[qid] = idx;
      return { correct: idx === q.answer, explain: s.mode === 'exam' ? null : q.explain };
    }
    check() {
      const s = this.need(), lab = this.labs[s.id];
      s.checks += 1;
      const st = this.sim.wlc.state();
      st._wlan_servers = {};
      for (const [n, w] of this.sim.wlc.wlans) st._wlan_servers[n] = this.sim.wlc.wlanServers(w);
      const exam = s.mode === 'exam';
      const res = [];
      for (const c of lab.checks) {
        const [ok, detail] = runCheck(c, st);
        const r = { desc: c.desc, ok, category: c.category || 'function' };
        if (!exam) r.detail = detail;
        res.push(r);
      }
      const cats = {};
      for (const r of res) { const e = setdefault(cats, r.category, [0, 0]); e[1] += 1; e[0] += r.ok ? 1 : 0; }
      const qs = lab.questions || [];
      const right = qs.filter(q => s.answers[q.id] === q.answer).length;
      const passed = res.every(r => r.ok);
      const p = this.prog(s.id);
      p.checks += 1;
      p.questionsRight = Math.max(p.questionsRight, right);
      if (passed) {
        p.passed = true;
        p[exam ? 'examPassed' : 'guidedPassed'] = true;
        if (!exam) p.bestHints = p.bestHints === null ? s.hints : Math.min(p.bestHints, s.hints);
      }
      const categories = {};
      for (const k of Object.keys(cats)) categories[k] = { ok: cats[k][0], total: cats[k][1] };
      return { passed, checks: res, categories, questions: { right, total: qs.length }, hintsUsed: s.hints, mode: s.mode };
    }
  }

  // ------------------------------------------------------------------ Sim (Gegenstueck zu Sim und HTTP-Handler in server.py)
  class Sim {
    constructor(opts) {
      opts = opts || {};
      this.standalone = opts.standalone !== undefined ? opts.standalone : true;
      this.resetWorld();
      this.labs = new LabEngine(this, opts.labs || []);
      this.store = opts.storage ? new Store(opts.storage) : null;
      if (this.store) {
        this.labs.progress = this.store.readProgress();
        const st = this.store.readState();
        if (st !== null) { try { this.restoreAll(st); } catch (e) { if (e instanceof StoreError) this.store.quarantine(this.store.P + 'state'); else throw e; } }
      }
    }
    resetWorld(clients, radius, mobility) {
      this.world = newWorld();
      if (clients !== undefined && clients !== null) this.world.clients = clone(clients);
      if (radius !== undefined && radius !== null) this.world.radius = { servers: clone(radius) };
      if (mobility !== undefined && mobility !== null) this.world.mobility = { controllers: clone(mobility) };
      this.wlc = new Wlc(this.world);
      this.cli = new Cli(this.wlc);
    }
    apply(commands) { return applyCommands(this.wlc, commands); }
    uiState() {
      const st = this.wlc.state();
      const sess = this.labs.session;
      const exam = !!(sess && sess.mode === 'exam');
      if (exam) for (const c of st.clients) c.reasons = [];
      st.diagAvailable = !exam;
      st.lab = sess ? { id: sess.id, mode: sess.mode } : null;
      st.persistent = this.store !== null;
      st.standalone = this.standalone;
      return st;
    }
    snapshotAll() {
      return plain({ kind: KIND, version: VERSION, world: this.world, wlc: this.wlc.dump(), lab: this.labs.session });
    }
    restoreAll(d) {
      validateState(d);
      const world = clone(d.world);
      if (!has(world, 'radius')) world.radius = defaultRadius();   // aeltere Staende kennen keinen RADIUS-Server
      if (!has(world, 'mobility')) world.mobility = defaultMobility();   // und keine Mobility-Gegenseite
      const wlc = new Wlc(world);
      try { wlc.load(d.wlc); wlc.state(); } catch (e) { throw new StoreError('Stand ist beschaedigt'); }
      this.world = world; this.wlc = wlc; this.cli = new Cli(wlc);
      this.labs.restoreSession(d.lab);
    }
    persist() {
      if (this.store) { this.store.writeState(this.snapshotAll()); this.store.writeProgress(this.labs.progress); }
    }

    /* handle(method, path, body) -> {status, body}: dieselben Endpunkte wie der Python-Server. */
    handle(method, path, body) {
      const r = this._route(method, path, body);
      if (method === 'POST') this.persist();      // vor der Antwort, wie im Server
      return { status: r[0], body: plain(r[1]) };
    }
    _route(method, path, body) {
      if (method === 'GET' && path === '/wlc/api/state') return [200, this.uiState()];
      if (path.startsWith('/wlc/api/saves') || path === '/wlc/api/progress/reset') return this._saves(method, path, body);
      if (path.startsWith('/wlc/api/lab')) return this._lab(method, path, body);
      if (method === 'POST' && path === '/wlc/api/apply') {
        const b = body === undefined ? {} : body;       // kein Body = {} wie im Server; ein JSON-null ist ungueltig
        const cmds = isDict(b) ? b.commands : undefined;
        if (!isDict(b) || !Array.isArray(cmds) || !cmds.every(x => typeof x === 'string')) return [400, { error: 'JSON erwartet: {"commands": ["..."]}' }];
        const [ok, results, err] = this.apply(cmds);
        return [ok ? 200 : 400, { ok, results, error: err }];
      }
      if (method === 'POST' && path === '/wlc/cli') {
        const b = body === undefined ? {} : body;
        if (!isDict(b) || (b.command !== undefined && typeof b.command !== 'string')) return [400, { error: 'JSON erwartet: {"command": "..."}' }];
        const out = this.cli.run(b.command || '');
        return [200, { output: out, prompt: this.cli.prompt }];
      }
      return [404, { error: 'nicht gefunden' }];
    }
    _saves(method, path, body) {
      if (this.store === null) return [409, { error: 'Persistenz ist ausgeschaltet' }];
      if (body !== undefined && !isDict(body)) return [400, { error: 'JSON-Objekt erwartet' }];
      body = body || {};
      try {
        if (method === 'GET' && path === '/wlc/api/saves') return [200, { saves: this.store.listNamed() }];
        if (method === 'POST' && path === '/wlc/api/saves') { this.store.saveNamed(body.name, this.snapshotAll()); return [200, { saves: this.store.listNamed() }]; }
        if (method === 'POST' && path === '/wlc/api/saves/load') { this.restoreAll(this.store.loadNamed(body.name)); return [200, { ok: true }]; }
        if (method === 'POST' && path === '/wlc/api/saves/delete') { this.store.deleteNamed(body.name); return [200, { saves: this.store.listNamed() }]; }
        if (method === 'POST' && path === '/wlc/api/progress/reset') { this.labs.resetProgress(); return [200, { labs: this.labs.list() }]; }
      } catch (e) { if (e instanceof StoreError) return [e.status, { error: e.message }]; throw e; }
      return [404, { error: 'Endpunkt nicht umgesetzt' }];
    }
    _lab(method, path, body) {
      const L = this.labs;
      if (body !== undefined && !isDict(body)) return [400, { error: 'JSON-Objekt erwartet' }];
      body = body || {};
      const is = (m, p) => method === m && path === p;
      try {
        if (is('GET', '/wlc/api/labs')) return [200, { labs: L.list(), current: L.pub() }];
        if (is('GET', '/wlc/api/lab')) return [200, { current: L.pub() }];
        if (is('POST', '/wlc/api/lab/start')) return [200, { current: L.start(body.id === undefined ? '' : body.id, body.mode === undefined ? 'guided' : body.mode) }];
        if (is('POST', '/wlc/api/lab/reset')) return [200, { current: L.reset() }];
        if (is('POST', '/wlc/api/lab/stop')) { L.stop(); return [200, { current: null }]; }
        if (is('POST', '/wlc/api/lab/hint')) return [200, { current: L.hint() }];
        if (is('GET', '/wlc/api/lab/solution')) return [200, L.solution()];
        if (is('POST', '/wlc/api/lab/answer')) return [200, L.answer(body.id === undefined ? '' : body.id, body.answer)];
        if (is('POST', '/wlc/api/lab/check')) return [200, L.check()];
      } catch (e) { if (e instanceof LabError) return [e.status, { error: e.message }]; throw e; }
      return [404, { error: 'Endpunkt nicht umgesetzt' }];
    }
  }

  /* Text-Speicher auf Basis von localStorage; null, wenn er nicht nutzbar ist (z. B. gesperrt). */
  function browserStorage() {
    try {
      const ls = root.localStorage;
      const probe = 'campusprep:probe';
      ls.setItem(probe, '1'); ls.removeItem(probe);
      return { get: k => ls.getItem(k), set: (k, v) => ls.setItem(k, v), remove: k => ls.removeItem(k),
               keys: () => { const out = []; for (let i = 0; i < ls.length; i++) out.push(ls.key(i)); return out; } };
    } catch (e) { return null; }
  }
  function memoryStorage() {
    const m = new Map();
    return { get: k => (m.has(k) ? m.get(k) : null), set: (k, v) => { m.set(k, v); }, remove: k => { m.delete(k); }, keys: () => [...m.keys()] };
  }

  const api = { createSim: opts => new Sim(opts), browserStorage, memoryStorage, Sim, Wlc, Cli, StoreError, LabError, validateState, applyCommands };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CampusEngine = api;
})(typeof window !== 'undefined' ? window : globalThis);
