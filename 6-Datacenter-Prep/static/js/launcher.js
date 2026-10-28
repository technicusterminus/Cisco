/* Startseite: Benutzer wählen oder anlegen. Jeder Benutzer hat eine eigene Übungswelt. */
'use strict';

const Launcher = {
  me: null,

  async users() {
    return (await fetch('/dp/users', { cache: 'no-store' })).json();
  },

  labLabel(id) { return id ? 'Lab ' + id.slice(0, 2) : 'freies Üben'; },

  async show(msg) {
    clearInterval(App.timer);
    const d = await this.users();
    const root = clear(document.getElementById('app'));
    const err = h('div', { class: 'login-err' }, msg || '');
    const grid = h('div', { class: 'ucards' });
    const login = async (name, pwd) => {
      err.textContent = '';
      const r = await fetch('/dp/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, password: pwd || '' }) });
      if (!r.ok) { const j = await r.json(); err.textContent = j.imdata[0].error.attributes.text; return false; }
      location.reload();
      return true;
    };
    d.users.forEach(u => {
      const pwd = h('input', { type: 'password', placeholder: 'Passwort', autocomplete: 'current-password' });
      const pwRow = h('div', { class: 'ucard-pw', style: { display: 'none' } }, pwd, h('button', { class: 'btn primary small', onclick: ev => { ev.stopPropagation(); login(u.name, pwd.value); } }, 'Anmelden'));
      pwd.addEventListener('keydown', e => { if (e.key === 'Enter') login(u.name, pwd.value); });
      pwd.addEventListener('click', e => e.stopPropagation());
      grid.appendChild(h('div', { class: 'ucard', onclick: () => {
        if (!u.password) return login(u.name, '');
        grid.querySelectorAll('.ucard-pw').forEach(x => { x.style.display = 'none'; });
        pwRow.style.display = '';
        pwd.focus();
      } },
      h('div', { class: 'uavatar' }, u.name.slice(0, 1).toUpperCase()),
      h('div', { class: 'uname' }, u.name, u.password ? ' 🔒' : ''),
      h('div', { class: 'umeta' }, (u.role === 'verwalter' ? 'Verwalter · ' : '') + u.labsDone + ' Labs bestanden'),
      h('div', { class: 'umeta' }, 'zuletzt: ' + (u.lastSeen ? fmtTs(u.lastSeen) : 'noch nie') + ' · ' + this.labLabel(u.lab)),
      pwRow));
    });
    const nf = { name: h('input', { placeholder: 'Name, z. B. Anna', maxlength: 32 }), pwd: h('input', { type: 'password', placeholder: 'Passwort (optional)', autocomplete: 'new-password' }),
      pwd2: h('input', { type: 'password', placeholder: 'Passwort wiederholen', autocomplete: 'new-password' }) };
    const create = async () => {
      err.textContent = '';
      if (nf.pwd.value !== nf.pwd2.value) { err.textContent = 'Die Passwörter stimmen nicht überein.'; return; }
      const r = await fetch('/dp/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ op: 'create', name: nf.name.value, password: nf.pwd.value }) });
      const j = await r.json();
      if (!r.ok) { err.textContent = j.imdata[0].error.attributes.text; return; }
      await login(j.name, nf.pwd.value);
    };
    nf.pwd2.addEventListener('keydown', e => { if (e.key === 'Enter') create(); });
    const newCard = d.openSignup ? h('div', { class: 'ucard new' }, h('div', { class: 'uavatar' }, '+'), h('div', { class: 'uname' }, 'Neuer Benutzer'),
      h('div', { class: 'ucard-form' }, nf.name, nf.pwd, nf.pwd2, h('button', { class: 'btn primary small', onclick: create }, 'Anlegen und starten'))) : null;
    if (newCard) grid.appendChild(newCard);
    root.appendChild(h('div', { class: 'login' }, h('div', { class: 'login-box launcher' },
      h('div', { class: 'login-brand' }, h('div', { class: 'logo-mark' }, 'DC'), h('div', null, h('b', null, 'Datacenter Prep'), h('div', { class: 'muted' }, 'Wer übt heute?'))),
      h('p', { class: 'muted small' }, 'Jeder Benutzer hat eine eigene Übungswelt mit eigenen Labs, Speicherständen und eigenem Fortschritt. Danach meldest du dich wie gewohnt am simulierten APIC an (Standard: admin / admin).'),
      grid, err,
      h('p', { class: 'muted small' }, 'Simulierte Umgebung zum Üben, kein Cisco-Produkt.'))));
  },

  /* Benutzermenü in der Kopfzeile */
  async menu(ev) {
    const r = ev.currentTarget.getBoundingClientRect();
    const d = await this.users();
    const items = [{ l: 'Benutzer wechseln', fn: () => this.logout() }, { l: 'Passwort ändern …', fn: () => this.passwordDialog(d.me, true) },
      { l: 'Meine Übungswelt zurücksetzen …', fn: () => this.resetDialog(d.me, true) }];
    if (d.admin) items.push('-', { l: 'Benutzerverwaltung …', fn: () => this.adminDialog() });
    items.push('-', { l: 'Mein Benutzerkonto löschen …', danger: true, fn: () => this.deleteDialog(d.me, true) });
    Ctx.open({ clientX: r.right - 260, clientY: r.bottom + 2 }, items);
  },

  async logout() {
    await fetch('/dp/logout', { method: 'POST' });
    location.reload();
  },

  async op(body) {
    const r = await fetch('/dp/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const j = await r.json();
    if (!r.ok) throw new ApiError(j.imdata[0].error.attributes.code, j.imdata[0].error.attributes.text);
    return j;
  },

  passwordDialog(name, self) {
    const f = buildForm((self ? [{ k: 'old', l: 'Bisheriges Passwort', t: 'password' }] : []).concat([{ k: 'pwd', l: 'Neues Passwort', t: 'password', help: 'leer = ohne Passwort' }, { k: 'pwd2', l: 'Wiederholen', t: 'password' }]), {}, {}, 'create');
    modal('Passwort für ' + name, f.el, [{ l: 'Abbrechen' }, { l: 'Speichern', primary: true, fn: async () => {
      const v = f.get();
      if ((v.pwd || '') !== (v.pwd2 || '')) throw new ApiError('Eingabe', 'Die Passwörter stimmen nicht überein');
      await this.op({ op: 'password', name, old: v.old, password: v.pwd });
      toast(v.pwd ? 'Passwort gesetzt' : 'Passwort entfernt');
    } }]);
  },

  resetDialog(name, self) {
    confirmBox((self ? 'Deine' : 'Die') + ' Übungswelt von „' + name + '" komplett zurücksetzen? Konfiguration, alle Speicherstände, Snapshots und der Lab-Fortschritt werden gelöscht. Das Benutzerkonto bleibt.', async () => {
      await this.op({ op: 'reset', name });
      if (self) location.reload(); else toast('Übungswelt von ' + name + ' zurückgesetzt');
    });
  },

  deleteDialog(name, self) {
    confirmBox('Benutzer „' + name + '" mit seiner ganzen Übungswelt löschen? Das lässt sich nicht rückgängig machen.', async () => {
      await this.op({ op: 'delete', name });
      if (self) location.reload(); else toast('Benutzer ' + name + ' gelöscht');
    });
  },

  async adminDialog() {
    const body = h('div');
    const draw = async () => {
      const d = await this.users();
      clear(body);
      const open = h('input', { type: 'checkbox', checked: d.openSignup, onchange: async () => { await this.op({ op: 'signup', open: open.checked }); toast(open.checked ? 'Jeder kann sich auf der Startseite anlegen' : 'Nur Verwalter legen Benutzer an'); } });
      body.appendChild(h('label', { class: 'check' }, open, h('span', null, 'Neue Benutzer dürfen sich auf der Startseite selbst anlegen')));
      body.appendChild(table([{ l: 'Benutzer', f: u => h('b', null, u.name) }, { l: 'Rolle', f: u => u.role }, { l: 'Passwort', f: u => u.password ? 'ja' : '—' },
        { l: 'Labs bestanden', f: u => u.labsDone }, { l: 'Zuletzt', f: u => u.lastSeen ? fmtTs(u.lastSeen) : '—' }], d.users, {
        actions: u => [h('button', { class: 'btn small', onclick: () => this.passwordDialog(u.name, false) }, 'Passwort'),
          h('button', { class: 'btn small', onclick: async () => { try { await this.op({ op: 'role', name: u.name, role: u.role === 'verwalter' ? 'benutzer' : 'verwalter' }); draw(); } catch (e) { errToast(e); } } }, u.role === 'verwalter' ? '→ Benutzer' : '→ Verwalter'),
          h('button', { class: 'btn small', onclick: () => this.resetDialog(u.name, u.name === d.me) }, 'Zurücksetzen'),
          u.name !== d.me ? iconBtn('🗑', 'Löschen', () => { this.deleteDialog(u.name, false); setTimeout(draw, 800); }, 'danger') : null],
      }));
      const nf = buildForm([{ k: 'name', l: 'Name', req: true }, { k: 'pwd', l: 'Passwort', t: 'password', help: 'optional' }, { k: 'role', l: 'Rolle', t: 'radio', o: [['benutzer', 'Benutzer'], ['verwalter', 'Verwalter']] }], { role: 'benutzer' }, {}, 'create');
      body.appendChild(h('div', { class: 'card' }, h('div', { class: 'card-h' }, 'Benutzer anlegen'), nf.el,
        h('div', { class: 'formbtns' }, h('button', { class: 'btn primary', onclick: async () => { const v = nf.get(); try { await this.op({ op: 'create', name: v.name, password: v.pwd, role: v.role }); toast('Benutzer ' + v.name + ' angelegt'); draw(); } catch (e) { errToast(e); } } }, 'Anlegen'))));
    };
    await draw();
    modal('Benutzerverwaltung', body, null, { wide: true });
  },
};
