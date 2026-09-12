"""Independent classifier for the SPEC_KITTY_HOME effect class. AST only."""
from __future__ import annotations
import ast, sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path("/home/jeroennouws/dev/sk-missions/3121")
KEY = "SPEC_KITTY_HOME"
UNWRAP = {"str", "Path", "PurePath", "PosixPath", "fspath", "os.fspath"}

def is_key(n): return isinstance(n, ast.Constant) and n.value == KEY

def fname(f):
    if isinstance(f, ast.Attribute): return f.attr
    if isinstance(f, ast.Name): return f.id
    return None

class Scopes:
    """Map every AST node to its enclosing def-chain and collect per-scope bindings."""
    def __init__(self, tree):
        self.chain = {}      # node -> tuple of enclosing FunctionDef nodes (outermost first)
        self.bindings = {}   # scope-node -> {name: [value-exprs]}
        self.classchain = {} # node -> tuple of enclosing ClassDef names
        self._walk(tree, (), ())
    def _walk(self, node, chain, cchain):
        self.chain[node] = chain
        self.classchain[node] = cchain
        newchain, newc = chain, cchain
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            newchain = chain + (node,)
            self.bindings.setdefault(node, defaultdict(list))
        elif isinstance(node, ast.ClassDef):
            newc = cchain + (node.name,)
        elif isinstance(node, ast.Module):
            self.bindings.setdefault(node, defaultdict(list))
        # record bindings into nearest scope (module or innermost def)
        scope = chain[-1] if chain else self._module
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    self.bindings.setdefault(scope, defaultdict(list))[t.id].append(node.value)
                elif isinstance(t, (ast.Tuple, ast.List)):
                    for e in t.elts:
                        if isinstance(e, ast.Name):
                            self.bindings.setdefault(scope, defaultdict(list))[e.id].append(None)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            self.bindings.setdefault(scope, defaultdict(list))[node.target.id].append(node.value)
        elif isinstance(node, (ast.AugAssign,)) and isinstance(node.target, ast.Name):
            self.bindings.setdefault(scope, defaultdict(list))[node.target.id].append(None)
        elif isinstance(node, ast.withitem) and isinstance(node.optional_vars, ast.Name):
            self.bindings.setdefault(scope, defaultdict(list))[node.optional_vars.id].append(None)
        elif isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            self.bindings.setdefault(scope, defaultdict(list))[node.target.id].append(None)
        for ch in ast.iter_child_nodes(node):
            self._walk(ch, newchain, newc)

def build(tree):
    s = Scopes.__new__(Scopes)
    s.chain = {}; s.bindings = {}; s.classchain = {}
    s._module = tree
    s.bindings[tree] = defaultdict(list)
    Scopes._walk(s, tree, (), ())
    return s

def params(fn):
    a = fn.args
    names = [x.arg for x in (list(a.posonlyargs)+list(a.args))]
    if names and names[0] in ("self", "cls"):
        names = names[1:]
    names += [x.arg for x in a.kwonlyargs]
    if a.vararg: names.append(a.vararg.arg)
    if a.kwarg: names.append(a.kwarg.arg)
    return set(names)

MAXD = 12
def resolve(node, chain, sc, depth=0, seen=None):
    """Return (root_symbol, (segments...)) or None."""
    if node is None or depth > MAXD: return None
    seen = seen or set()
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return ("<literal>", tuple(x for x in node.value.split("/") if x))
        return None
    if isinstance(node, ast.Call):
        nm = fname(node.func)
        full = None
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            full = f"{node.func.value.id}.{node.func.attr}"
        if (nm in ("str","Path","PurePath","PosixPath","fspath") or full == "os.fspath") and len(node.args)==1 and not node.keywords:
            return resolve(node.args[0], chain, sc, depth+1, seen)
        if nm == "joinpath" and isinstance(node.func, ast.Attribute):
            base = resolve(node.func.value, chain, sc, depth+1, seen)
            if base is None: return None
            segs = list(base[1])
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    segs += [x for x in a.value.split("/") if x]
                else:
                    return None
            return (base[0], tuple(segs))
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        l = resolve(node.left, chain, sc, depth+1, seen)
        r = node.right
        if l is None: return None
        if isinstance(r, ast.Constant) and isinstance(r.value, str):
            return (l[0], l[1] + tuple(x for x in r.value.split("/") if x))
        rr = resolve(r, chain, sc, depth+1, seen)
        if rr is not None and rr[0] == "<literal>":
            return (l[0], l[1] + rr[1])
        return None
    if isinstance(node, ast.JoinedStr):
        segs = []
        root = None
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                segs += [x for x in part.value.split("/") if x]
            elif isinstance(part, ast.FormattedValue):
                sub = resolve(part.value, chain, sc, depth+1, seen)
                if sub is None: return None
                if sub[0] == "<literal>":
                    segs += list(sub[1])
                else:
                    if root is not None or segs: return None
                    root = sub[0]; segs = list(sub[1])
            else:
                return None
        if root is None: return ("<literal>", tuple(segs))
        return (root, tuple(segs))
    if isinstance(node, ast.Name):
        # parameter of some enclosing def -> root symbol
        for fn in chain:
            if node.id in params(fn):
                return (node.id, ())
        if node.id in seen: return None
        # single-assignment local binding, innermost scope outward, then module
        scopes = list(reversed(chain)) + [sc._module]
        for scope in scopes:
            b = sc.bindings.get(scope)
            if b and node.id in b:
                vals = b[node.id]
                if len(vals) != 1 or vals[0] is None:
                    return None
                return resolve(vals[0], chain, sc, depth+1, seen | {node.id})
        return None
    if isinstance(node, ast.Attribute):
        return None
    return None

def qualname(node_chain, cchain, fn):
    parts = list(cchain) + [f.name for f in node_chain if not isinstance(f, ast.Lambda)]
    return ".".join(parts)

def classify(files):
    all_sites = []
    for p in files:
        b = p.read_bytes()
        if b"SPEC_KITTY_HOME" not in b:
            continue
        tree = ast.parse(b, filename=str(p))
        sc = build(tree)
        for n in ast.walk(tree):
            valnode = None; form = None
            if isinstance(n, ast.Call):
                nm = fname(n.func)
                if nm == "setenv" and n.args and is_key(n.args[0]):
                    form = "setenv"; valnode = n.args[1] if len(n.args)>1 else None
                elif nm == "setdefault" and n.args and is_key(n.args[0]):
                    form = "setdefault"; valnode = n.args[1] if len(n.args)>1 else None
            elif isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Subscript) and is_key(t.slice):
                        v = t.value
                        base = v.attr if isinstance(v, ast.Attribute) else (v.id if isinstance(v, ast.Name) else None)
                        if base == "environ":
                            form = "environ"; valnode = n.value
            if form is None: continue
            chain = sc.chain[n]
            defchain = tuple(f for f in chain if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)))
            val = resolve(valnode, defchain, sc)
            # membership
            req = {"tmp_path", "monkeypatch"}
            keyed = None; acc = set()
            for f in defchain:
                acc |= params(f)
                if req <= acc:
                    keyed = f; break
            innermost_ok = None
            if defchain:
                # innermost attribution: only the innermost def's own params
                inner = defchain[-1]
                if req <= params(inner): innermost_ok = inner
            all_sites.append(dict(
                path=str(p.relative_to(ROOT)), lineno=n.lineno, form=form,
                value=val, valsrc=ast.unparse(valnode) if valnode is not None else None,
                defchain=[f.name for f in defchain],
                keyed=keyed.name if keyed else None,
                keyed_line=keyed.lineno if keyed else None,
                keyed_qual=".".join(list(sc.classchain[keyed]) + [keyed.name]) if keyed else None,
                keyed_decorated=bool(keyed and keyed.decorator_list) if keyed else None,
                keyed_isfixture=(bool(keyed) and any("fixture" in ast.unparse(d) for d in keyed.decorator_list)) if keyed else None,
                innermost_member=innermost_ok.name if innermost_ok else None,
                innermost_qual=".".join(list(sc.classchain[innermost_ok]) + [innermost_ok.name]) if innermost_ok else None,
                site_kindchain=[bool(f.decorator_list) for f in defchain],
            ))
    return all_sites

if __name__ == "__main__":
    files = sorted((ROOT/"tests").rglob("*.py"))
    sites = classify(files)
    print("sites:", len(sites))
    buckets = Counter()
    bfiles = defaultdict(set)
    for s in sites:
        v = s["value"]
        k = "UNRESOLVED" if v is None else (v[0] + "".join("/"+x for x in v[1]))
        buckets[k] += 1
        bfiles[k].add(s["path"])
    print("\n== value buckets ==")
    for k,c in buckets.most_common():
        print(f"{c:4d} sites  {len(bfiles[k]):3d} files   {k}")
