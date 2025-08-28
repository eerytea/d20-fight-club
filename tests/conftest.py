# tests/conftest.py
# Ensure the project root (where the local `engine/` lives) is first on sys.path
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Optional: sanity print if you need to debug which 'engine' is being imported.
# import importlib, types
# m = importlib.import_module("engine")
# print("Using engine from:", getattr(m, "__file__", "<namespace>"))
