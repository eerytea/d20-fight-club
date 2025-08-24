import os, time
ROOT = os.path.dirname(os.path.dirname(__file__))
def walk(root):
    for dirpath, dirs, files in os.walk(root):
        if any(skip in dirpath for skip in (".git", "__pycache__", ".venv")):
            continue
        rel = os.path.relpath(dirpath, ROOT)
        print(f"\n[{rel}]")
        for f in sorted(files):
            p = os.path.join(dirpath, f)
            try:
                sz = os.path.getsize(p)
                mt = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(p)))
                print(f"  {f:35}  {sz:8} bytes   {mt}")
            except OSError:
                pass
if __name__ == "__main__":
    walk(ROOT)
