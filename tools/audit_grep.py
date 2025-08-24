import os, re
ROOT = os.path.dirname(os.path.dirname(__file__))
PATTERNS = {
    "TODO/FIXME": re.compile(r"#\s*(TODO|FIXME|HACK|XXX)", re.I),
    "Mutable defaults": re.compile(r"def\s+\w+\(.*=\s*(\[\]|\{\}|set\(\))"),
    "Bare except": re.compile(r"except\s*:\s"),
    "Random use": re.compile(r"\brandom\.(rand|choice|shuffle)"),
    "Global state": re.compile(r"\bglobal\s+\w+"),
}
for dirpath, _, files in os.walk(ROOT):
    if any(s in dirpath for s in (".git","__pycache__","venv","tools")):
        continue
    for f in files:
        if not f.endswith(".py"): continue
        p = os.path.join(dirpath, f)
        try:
            text = open(p,"r",encoding="utf-8").read()
        except: 
            continue
        for label, rx in PATTERNS.items():
            for m in rx.finditer(text):
                line_no = text.count("\n", 0, m.start()) + 1
                print(f"{label:18} {os.path.relpath(p, ROOT)}:{line_no}")
