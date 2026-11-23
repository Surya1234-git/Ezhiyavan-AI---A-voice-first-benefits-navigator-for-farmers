"""Dependency-free static check for the bug classes that slipped through before (no ruff/pyflakes needed):
 1. a module-level function uses a name in a decorator/default argument BEFORE that name is defined (NameError at import)
 2. a name is read but never bound anywhere in the module (typo / missing import)
Usage: python scripts/check_names.py backend/app/*.py     Exit 1 on findings.  CI additionally runs `ruff check --select F`."""
import ast, builtins, sys

def bound_names(tree):
    out = set(dir(builtins)) | {"__file__", "__name__"}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): out.add(n.name)
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)): out.add(n.id)
        if isinstance(n, ast.arg): out.add(n.arg)
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names: out.add((a.asname or a.name).split(".")[0])
        if isinstance(n, ast.ExceptHandler) and n.name: out.add(n.name)
        if isinstance(n, (ast.Global, ast.Nonlocal)): out.update(n.names)
        if isinstance(n, ast.MatchAs) and n.name: out.add(n.name)
    return out

def check(path):
    with open(path, encoding="utf-8") as fh: src = fh.read()
    tree = ast.parse(src, path); problems = []
    bound = bound_names(tree)
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in bound: problems.append(f"{path}:{n.lineno}: undefined name '{n.id}'")
    defined_at = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): defined_at.setdefault(n.name, n.lineno)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name): defined_at.setdefault(t.id, n.lineno)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names: defined_at.setdefault((a.asname or a.name).split(".")[0], n.lineno)
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            evaluated = list(n.decorator_list) + list(n.args.defaults) + [d for d in n.args.kw_defaults if d]
            for e in evaluated:
                for c in ast.walk(e):
                    if isinstance(c, ast.Name) and c.id in defined_at and defined_at[c.id] > n.lineno:
                        problems.append(f"{path}:{n.lineno}: '{n.name}' uses '{c.id}' before it is defined (line {defined_at[c.id]}): NameError at import")
    return problems

if __name__ == "__main__":
    bad = [p for f in sys.argv[1:] for p in check(f)]
    print("\n".join(bad) if bad else f"check_names: {len(sys.argv) - 1} files OK"); sys.exit(1 if bad else 0)
