/* Ersteinrichtung: serielle Konsole des APIC mit dem Setup-Dialog */
'use strict';

const SetupConsole = {
  async show(info) {
    const root = clear(document.getElementById('app'));
    const out = h('pre', { class: 'term-out' });
    const pr = h('span', { class: 'term-pr' });
    const inp = h('input', { class: 'term-in', spellcheck: 'false', autocomplete: 'off' });
    root.appendChild(h('div', { class: 'setupwrap' },
      h('div', { class: 'setuphead' }, h('b', null, 'APIC Console'), h('span', { class: 'muted' }, ' · ' + info.serial + ' · serielle Konsole / CIMC KVM'),
        h('span', { class: 'grow' }), h('span', { class: 'muted small' }, 'Datacenter Prep – Ersteinrichtung des APIC')),
      h('div', { class: 'setupbody' }, h('div', { class: 'term setupterm' }, out, h('div', { class: 'term-line' }, pr, inp)),
        info.lab ? h('div', { class: 'setuplab' }, h('h3', null, info.lab.title), md(info.lab.intro || '')) : null)));
    const print = t => { out.textContent += t; out.scrollTop = out.scrollHeight; };
    const ask = (prompt, secret) => new Promise(res => {
      pr.textContent = prompt;
      inp.type = secret ? 'password' : 'text';
      inp.value = '';
      inp.focus();
      inp.onkeydown = ev => {
        if (ev.key !== 'Enter') return;
        const v = inp.value;
        inp.onkeydown = null;
        pr.textContent = '';
        inp.value = '';
        print(prompt + (secret ? '' : v) + '\n');
        res(v);
      };
    });
    const check = async (key, value, answers) => (await API.post('/sim/setup', { check: key, value, answers }, true)).error;
    print('Cisco APIC  (Datacenter Prep)\nBIOS ... Booting from local disk ... Starting services ...\n\n' +
      'Press any key to continue...\n\n' +
      'Starting Setup Utility\n\nThis setup utility will guide you through the basic configuration of\n' +
      'the system. Setup can configure only enough connectivity for management\nof the system.\n\n' +
      '*Note: setup is mainly used for configuring the system initially,\nwhen no configuration is present. So setup always assumes system\n' +
      'defaults and not the current system configuration values.\n\nPress Enter at anytime to assume the default values. Use ctrl-d at\n' +
      'anytime to restart from the beginning.\n\n');
    let ans = {};
    for (;;) {
      const prev = ans;
      ans = {};
      for (const [key, section, text, def0] of info.questions) {
        if (key === 'standby' || key === 'ctrlId') {
          if (key === 'standby' && Number(ans.ctrlCount || 1) === 1) { ans.standby = 'NO'; continue; }
        }
        if (section) print('\n' + section + '\n');
        if (info.notes[key]) print('  ' + info.notes[key].replace(/\n/g, '\n  ') + '\n');
        const def = prev[key] !== undefined && key !== 'pwd' ? prev[key] : def0;
        for (;;) {
          if (key === 'pwd') {
            const a = await ask('  Enter the password for admin: ', true);
            const err = await check('pwd', a, ans);
            if (err) { print('  ' + err + '\n'); continue; }
            const b = await ask('  Reenter the password for admin: ', true);
            if (a !== b) { print('  Error: passwords do not match\n'); continue; }
            ans.pwd = a;
            break;
          }
          const v = (await ask('  ' + text + (def !== null && def !== undefined ? ' [' + def + ']' : '') + ': ')).trim() || def || '';
          const err = await check(key, v, ans);
          if (err) { print('  ' + err + '\n'); continue; }
          ans[key] = v;
          break;
        }
      }
      const sum = (await API.post('/sim/setup', { summary: true, answers: ans }, true)).text;
      print('\nNone of the above can be changed after the configuration is applied\nwithout wiping the fabric (acidiag touch clean).\n\n' + sum + '\n\n');
      const edit = (await ask('Would you like to edit the configuration? (y/n) [n]: ')).trim().toLowerCase();
      if (edit.startsWith('y')) { print('\n'); continue; }
      try {
        await API.post('/sim/setup', { answers: ans }, true);
      } catch (e) {
        print('\n' + (e.text || e.message) + '\n\n');
        continue;
      }
      break;
    }
    print('\nApplying configuration ...\nConfiguring management interface ...\nStarting APIC services, this takes a few minutes ...\n\n' +
      'System pre-configured successfully.\nUse: https://' + ans.oobIp.split('/')[0] + ' to complete the bootstrapping\n\n');
    pr.textContent = '';
    inp.disabled = true;
    setTimeout(() => location.reload(), 2500);
  },
};
