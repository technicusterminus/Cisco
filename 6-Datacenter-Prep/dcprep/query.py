"""REST-Abfragen im APIC-Format: /api/mo/<dn>.json und /api/class/<klasse>.json."""
import re

from .model import CLASSES, AciError, COMMON_RW

HIDDEN = {'pwd', 'password', 'key', 'userPasswd', 'passphrase'}
SKIP_IN_SUBTREE = {'faultInst', 'healthInst'}


# --------------------------------------------------------------------------
# query-target-filter
# --------------------------------------------------------------------------

def parse_filter(text):
    s = text.strip()
    pos = [0]

    def ws():
        while pos[0] < len(s) and s[pos[0]] in ' \t':
            pos[0] += 1

    def expr():
        ws()
        m = re.match(r'[A-Za-z_][\w]*', s[pos[0]:])
        if not m:
            raise AciError(400, 'Invalid filter: %s' % text)
        name = m.group(0)
        pos[0] += len(name)
        ws()
        if pos[0] >= len(s) or s[pos[0]] != '(':
            raise AciError(400, 'Invalid filter: %s' % text)
        pos[0] += 1
        args = []
        while True:
            ws()
            if pos[0] >= len(s):
                raise AciError(400, 'Invalid filter: %s' % text)
            ch = s[pos[0]]
            if ch == ')':
                pos[0] += 1
                break
            if ch == '"':
                end = s.index('"', pos[0] + 1)
                args.append(('str', s[pos[0] + 1:end]))
                pos[0] = end + 1
            else:
                m = re.match(r'[^(),"]+', s[pos[0]:])
                tok = m.group(0).strip() if m else ''
                save = pos[0]
                pos[0] += len(m.group(0)) if m else 0
                ws()
                if pos[0] < len(s) and s[pos[0]] == '(':
                    pos[0] = save
                    args.append(expr())
                else:
                    args.append(('prop', tok))
            ws()
            if pos[0] < len(s) and s[pos[0]] == ',':
                pos[0] += 1
        return (name, args)

    tree = expr()
    return tree


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def eval_filter(tree, cls, attrs):
    op, args = tree
    if op == 'and':
        return all(eval_filter(a, cls, attrs) for a in args)
    if op == 'or':
        return any(eval_filter(a, cls, attrs) for a in args)
    if op == 'not':
        return not eval_filter(args[0], cls, attrs)
    if not args or args[0][0] != 'prop':
        raise AciError(400, 'Invalid filter operand')
    prop = args[0][1]
    if '.' in prop:
        pcls, pattr = prop.split('.', 1)
        if pcls != cls:
            return False
    else:
        pattr = prop
    val = attrs.get(pattr, '')
    vals = [a[1] for a in args[1:]]
    if op == 'eq':
        return val == vals[0]
    if op == 'ne':
        return val != vals[0]
    if op == 'wcard':
        try:
            return re.search(vals[0], val) is not None
        except re.error:
            return vals[0] in val
    if op in ('gt', 'lt', 'ge', 'le'):
        a, b = _num(val), _num(vals[0])
        if a is None or b is None:
            a, b = val, vals[0]
        return {'gt': a > b, 'lt': a < b, 'ge': a >= b, 'le': a <= b}[op]
    if op == 'bw':
        a, lo, hi = _num(val), _num(vals[0]), _num(vals[1])
        if None in (a, lo, hi):
            return vals[0] <= val <= vals[1]
        return lo <= a <= hi
    if op == 'anybit':
        return any(v in val.split(',') for v in vals[0].split(','))
    raise AciError(400, 'Unsupported filter operator %s' % op)


# --------------------------------------------------------------------------
# Ausgabe
# --------------------------------------------------------------------------

def out_attrs(store, dn, mode='all'):
    cls, attrs, oper = store.objs[dn]
    meta = CLASSES[cls]
    if mode == 'naming-only':
        a = {n: attrs.get(n, '') for n in meta.naming}
        a['dn'] = dn
        return a
    a = {}
    if not oper and cls not in ('topRoot',):
        for k in COMMON_RW:
            a[k] = ''
        a.update({'childAction': '', 'extMngdBy': '', 'lcOwn': 'local', 'uid': '15374'})
        a['userdom'] = ':all:'
    else:
        a.update({'childAction': '', 'lcOwn': 'local'})
    for k, v in attrs.items():
        if k in HIDDEN:
            continue
        if mode == 'config-only' and (k in meta.ro or k in ('modTs',)):
            continue
        a[k] = v
    a['dn'] = dn
    a['status'] = ''
    a.setdefault('modTs', 'never')
    return a


class Opts:
    def __init__(self, q):
        g = lambda k, d='': (q.get(k) or [d])[0]
        self.target = g('query-target', 'self')
        self.target_cls = set(filter(None, g('target-subtree-class').split(',')))
        self.filter = parse_filter(g('query-target-filter')) if g('query-target-filter') else None
        self.rsp = g('rsp-subtree', 'no')
        self.rsp_cls = set(filter(None, g('rsp-subtree-class').split(',')))
        self.rsp_filter = parse_filter(g('rsp-subtree-filter')) if g('rsp-subtree-filter') else None
        self.include = set(filter(None, g('rsp-subtree-include').split(',')))
        self.prop = g('rsp-prop-include', 'all')
        self.order = g('order-by')
        self.page = int(g('page', '0') or 0)
        self.page_size = int(g('page-size', '0') or 0)
        if self.target not in ('self', 'children', 'subtree'):
            raise AciError(400, 'Invalid query-target %s' % self.target)
        if self.rsp not in ('no', 'children', 'full'):
            raise AciError(400, 'Invalid rsp-subtree %s' % self.rsp)


def _render(store, dn, o, depth, engine):
    cls = store.objs[dn][0]
    node = {'attributes': out_attrs(store, dn, o.prop)}
    kids = []
    if o.rsp != 'no' and depth < (1 if o.rsp == 'children' else 99):
        for c in store.children(dn):
            ccls = store.objs[c][0]
            if ccls in SKIP_IN_SUBTREE and not ('faults' in o.include and ccls == 'faultInst') \
                    and ccls not in o.rsp_cls:
                continue
            if o.rsp_cls and ccls not in o.rsp_cls:
                if o.rsp == 'full' and _has_desc(store, c, o.rsp_cls):
                    kids.append(_render(store, c, o, depth + 1, engine))
                continue
            if o.rsp_filter and not eval_filter(o.rsp_filter, ccls, store.objs[c][1]):
                continue
            kids.append(_render(store, c, o, depth + 1, engine))
    if 'health' in o.include and engine is not None:
        score = engine.health.get(dn)
        if score is not None:
            kids.append({'healthInst': {'attributes': {
                'cur': str(score), 'twScore': str(score), 'maxSev': 'cleared',
                'dn': dn + '/health', 'childAction': '', 'status': ''}}})
    if 'count' in o.include:
        node = {'attributes': node['attributes']}
    if kids:
        node['children'] = kids
    return {cls: node}


def _has_desc(store, dn, classes):
    for c in store.children(dn):
        if store.objs[c][0] in classes or _has_desc(store, c, classes):
            return True
    return False


def run_query(store, kind, path, q, engine=None):
    """kind='mo' (path=dn) oder 'class' (path=[scope-dn/]klasse)."""
    o = Opts(q)
    if kind == 'mo':
        dn = path
        if dn not in store.objs:
            return [], 0
        roots = [dn]
    else:
        scope = None
        cls = path
        if '/' in path:
            scope, cls = path.rsplit('/', 1)
        if cls not in CLASSES:
            raise AciError(400, 'Request failed, unresolved class for %s' % cls)
        roots = store.by_class(cls)
        if scope:
            roots = [d for d in roots if d.startswith(scope + '/')]
        roots.sort()
        if o.target == 'self' and o.filter:
            roots = [d for d in roots if eval_filter(o.filter, cls, store.objs[d][1])]
    targets = []
    for r in roots:
        if o.target == 'self':
            targets.append(r)
        elif o.target == 'children':
            targets.extend(store.children(r))
        else:
            targets.extend(store.subtree(r))
    if o.target != 'self' or kind == 'mo':
        if o.target != 'self' and o.target_cls:
            targets = [d for d in targets if store.objs[d][0] in o.target_cls]
        elif o.target != 'self':
            targets = [d for d in targets if store.objs[d][0] not in SKIP_IN_SUBTREE
                       or 'faultInst' in o.target_cls]
        if o.filter and (o.target != 'self' or kind == 'mo'):
            targets = [d for d in targets if eval_filter(o.filter, store.objs[d][0], store.objs[d][1])]
    if 'no-scoped' in o.include and 'faults' in o.include:
        out = []
        for t in targets:
            for d in store.subtree(t):
                if store.objs[d][0] == 'faultInst':
                    out.append({'faultInst': {'attributes': out_attrs(store, d)}})
        return out, len(out)
    if 'count' in o.include and o.rsp == 'no':
        return [{'moCount': {'attributes': {'count': str(len(targets)), 'childAction': '',
                                             'dn': '', 'status': ''}}}], 1
    if o.order:
        key = o.order.split('|')
        attr = key[0].split('.')[-1]
        rev = len(key) > 1 and key[1] == 'desc'
        targets.sort(key=lambda d: (_num(store.objs[d][1].get(attr)) is None,
                                    _num(store.objs[d][1].get(attr)) or 0,
                                    store.objs[d][1].get(attr, '')), reverse=rev)
    total = len(targets)
    if o.page_size:
        targets = targets[o.page * o.page_size:(o.page + 1) * o.page_size]
    res = [_render(store, d, o, 0, engine) for d in targets]
    if 'count' in o.include:
        for r, d in zip(res, targets):
            cls = next(iter(r))
            n = len([c for c in store.subtree(d)[1:]
                     if not o.rsp_cls or store.objs[c][0] in o.rsp_cls])
            r[cls]['children'] = [{'moCount': {'attributes': {'count': str(n), 'dn': '',
                                                               'childAction': '', 'status': ''}}}]
    return res, total
