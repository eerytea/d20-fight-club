import os, ast, csv
ROOT = os.path.dirname(os.path.dirname(__file__))
rows = []
skip_dirs = {".git", "__pycache__", "venv", ".venv", "tools", ".pytest_cache"}

for dirpath, _, files in os.walk(ROOT):
    parts = set(os.path.relpath(dirpath, ROOT).split(os.sep))
    if parts & skip_dirs: 
        continue
    for f in files:
        if not f.endswith(".py"):
            continue
        path = os.path.join(dirpath, f)
        rel = os.path.relpath(path, ROOT)
        try:
            src = open(path, "r", encoding="utf-8").read()
            tree = ast.parse(src, filename=rel)
        except Exception as e:
            rows.append([rel, "PARSE_ERROR", str(e)])
            continue

        mod_doc = ast.get_docstring(tree) or ""
        if mod_doc.strip():
            rows.append([rel, "module_doc", mod_doc.splitlines()[0][:80]])

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                rows.append([rel, "class", node.name])
                for n2 in node.body:
                    if isinstance(n2, ast.FunctionDef):
                        rows.append([rel, f"method:{node.name}", n2.name])
            elif isinstance(node, ast.FunctionDef):
                rows.append([rel, "def", node.name])

out = os.path.join(ROOT, "tools", "audit_api.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["file","kind","name"])
    w.writerows(rows)

print(f"Wrote {out} ({len(rows)} rows)")

