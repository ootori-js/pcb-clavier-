"""Generate the KiCad schematic (one sheet, connections by net labels)."""
import os, sys, uuid, copy
sys.path.insert(0, os.path.dirname(__file__))
from sexp import parse, dump, find, first, Q
import design

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'carte-linux-f1c200s'
KICAD_SYM = '/usr/share/kicad/symbols'
NS = uuid.UUID('6f1c2005-0000-4000-8000-000000000000')


def uid(*a):
    return str(uuid.uuid5(NS, '/'.join(str(x) for x in a)))


_libs = {}


def load_lib(lib):
    if lib not in _libs:
        path = os.path.join(ROOT, 'lib', 'sbc.kicad_sym') if lib == 'sbc' else os.path.join(KICAD_SYM, lib + '.kicad_sym')
        tree = parse(open(path, encoding='utf-8').read())[0]
        _libs[lib] = {str(s[1]): s for s in find(tree, 'symbol')}
    return _libs[lib]


def strip_ids(node):
    """Drop legacy (id N) tokens from properties."""
    out = []
    for c in node:
        if isinstance(c, list):
            if c and c[0] == 'id':
                continue
            out.append(strip_ids(c))
        else:
            out.append(c)
    return out


def sym_pins(sym):
    """[(number, name, x, y, angle)] over all units."""
    pins = []
    for unit in find(sym, 'symbol'):
        for p in find(unit, 'pin'):
            at = first(p, 'at')
            pins.append((str(first(p, 'number')[1]), str(first(p, 'name')[1]),
                         float(at[1]), float(at[2]), int(float(at[3])) if len(at) > 3 else 0))
    return pins


def snap(v, g=2.54):
    return round(round(v / g) * g, 2)


def build():
    lib_symbols = [Q('lib_symbols')]
    lib_symbols[0] = 'lib_symbols'
    used = {}
    items = []
    root_uuid = uid('root')

    # ---- layout: one block per functional group, shelf packing inside ----
    PAGE_W, PAGE_H = 841.0, 594.0            # A1
    LABEL = 20.0                              # room for labels on each side
    gx, gy, row_h = 20.0, 25.0, 0.0
    BLOCK_W = 255.0
    for title, refs in design.GROUPS.items():
        # measure parts
        cells = []
        for ref in refs:
            p = design.PARTS[ref]
            sym = load_lib(p['lib'])[p['sym']]
            pins = sym_pins(sym)
            xs = [q[2] for q in pins]; ys = [q[3] for q in pins]
            w = max(xs) - min(xs) + 2 * LABEL
            h = max(ys) - min(ys) + 17.78
            cells.append((ref, p, sym, pins, w, h, min(xs), max(ys)))
        # big parts first
        cells.sort(key=lambda c: -c[5])
        # estimate block height with shelf packing
        def pack(x0, y0):
            x, y, shelf = x0, y0, 0.0
            pos = {}
            for ref, p, sym, pins, w, h, minx, maxy in cells:
                if x + w > x0 + BLOCK_W:
                    x, y, shelf = x0, y + shelf, 0.0
                pos[ref] = (x, y)
                x += w
                shelf = max(shelf, h)
            return pos, y + shelf - y0
        pos, bh = pack(gx, gy + 10)
        if gy + bh + 10 > PAGE_H - 15:
            gx, gy = gx + BLOCK_W + 12, 25.0
            pos, bh = pack(gx, gy + 10)
        items.append(['text', Q(title), ['at', round(gx, 2), round(gy, 2), 0],
                      ['effects', ['font', ['size', 3, 3], 'bold'], ['justify', 'left', 'bottom']],
                      ['uuid', uid('title', title)]])
        for ref, p, sym, pins, w, h, minx, maxy in cells:
            cx, cy = pos[ref]
            sx = snap(cx + LABEL - minx)
            sy = snap(cy + 7.62 + maxy)
            lib_id = f"{p['lib']}:{p['sym']}"
            if lib_id not in used:
                s = strip_ids(copy.deepcopy(sym))
                s[1] = Q(lib_id)
                lib_symbols.append(s)
                used[lib_id] = True
            inst = ['symbol', ['lib_id', Q(lib_id)], ['at', sx, sy, 0], ['unit', 1],
                    ['in_bom', 'no' if p['dnp'] else 'yes'], ['on_board', 'yes'],
                    ['dnp', 'yes' if p['dnp'] else 'no'], ['uuid', uid('sym', ref)]]
            top = sy - maxy - 2.54
            def prop(name, val, dy, hide=False):
                eff = ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left']]
                if hide:
                    eff.append('hide')
                return ['property', Q(name), Q(val), ['at', round(sx + minx, 2), round(top - dy, 2), 0], eff]
            inst.append(prop('Reference', ref, 2.54))
            inst.append(prop('Value', p['value'], 0))
            inst.append(prop('Footprint', f"{p['fplib']}:{p['fp']}", 0, True))
            inst.append(prop('LCSC', p['lcsc'], 0, True))
            for num, name, px, py, ang in pins:
                inst.append(['pin', Q(num), ['uuid', uid('pin', ref, num)]])
            inst.append(['instances', ['project', Q(NAME),
                         ['path', Q('/' + root_uuid), ['reference', Q(ref)], ['unit', 1]]]])
            items.append(inst)
            seen = set()
            for num, name, px, py, ang in pins:
                x, y = round(sx + px, 2), round(sy - py, 2)
                net = p['pins'].get(num)
                if (num, x, y) in seen:
                    continue
                seen.add((num, x, y))
                if not net:
                    items.append(['no_connect', ['at', x, y], ['uuid', uid('nc', ref, num)]])
                    continue
                lang = {0: 180, 180: 0, 90: 270, 270: 90}[ang % 360]
                just = 'right' if lang in (180, 270) else 'left'
                items.append(['label', Q(net), ['at', x, y, lang],
                              ['effects', ['font', ['size', 1.27, 1.27]], ['justify', just, 'bottom']],
                              ['uuid', uid('lbl', ref, num)]])
        gy += bh + 18
        if gy > PAGE_H - 60:
            gx, gy = gx + BLOCK_W + 12, 25.0

    sch = ['kicad_sch', ['version', 20230121], ['generator', 'eeschema'], ['uuid', root_uuid],
           ['paper', Q('A1')],
           ['title_block', ['title', Q('Carte Linux F1C200S')], ['rev', Q('A')],
            ['comment', 1, Q('Genere par gen/make_sch.py a partir de gen/design.py')]],
           lib_symbols] + items + [['sheet_instances', ['path', Q('/'), ['page', Q('1')]]]]
    out = os.path.join(ROOT, NAME + '.kicad_sch')
    open(out, 'w', encoding='utf-8').write(dump(sch) + '\n')
    print('wrote', out, len(design.PARTS), 'symbols')


if __name__ == '__main__':
    build()
