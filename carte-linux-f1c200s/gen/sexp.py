"""Minimal S-expression reader/writer for KiCad files."""
import re
_tok = re.compile(r'"(?:\\.|[^"\\])*"|\(|\)|[^\s()"]+')

class Q(str):
    """A quoted string token."""

def parse(text):
    stack = [[]]
    for m in _tok.finditer(text):
        t = m.group(0)
        if t == '(':
            new = []
            stack[-1].append(new)
            stack.append(new)
        elif t == ')':
            stack.pop()
        elif t[0] == '"':
            stack[-1].append(Q(t[1:-1].replace('\\"', '"').replace('\\\\', '\\')))
        else:
            stack[-1].append(t)
    return stack[0]

def dump(node, indent=0):
    if isinstance(node, list):
        simple = all(not isinstance(c, list) for c in node)
        if simple:
            return '(' + ' '.join(dump(c) for c in node) + ')'
        pad = '\n' + '  ' * (indent + 1)
        out = '(' + dump(node[0])
        for c in node[1:]:
            if isinstance(c, list):
                out += pad + dump(c, indent + 1)
            else:
                out += ' ' + dump(c)
        return out + '\n' + '  ' * indent + ')'
    if isinstance(node, Q):
        return '"' + node.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return str(node)

def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]

def first(node, key):
    r = find(node, key)
    return r[0] if r else None
