# core/config.py
from __future__ import annotations
from pathlib import Path
import json

DEFAULT_SETTINGS = {
    "audio": {
        "master": 0.8,
        "music": 0.7,
        "sfx": 0.8,
        "mute": False,
    },
    "video": {
        "fullscreen": False,
        "resolution": [1280, 720],
        "fps_cap": 60,
    }
}

def _deep_merge(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict):
            dst[k] = _deep_merge(dst.get(k, {}), v)
        else:
            dst.setdefault(k, v)
    return dst

def load_settings(path: str | Path = "saves/settings.json") -> dict:
    p = Path(path)
    if not p.exists():
        return json.loads(json.dumps(DEFAULT_SETTINGS))
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(json.dumps(DEFAULT_SETTINGS))
    # backfill any new keys
    merged = json.loads(json.dumps(DEFAULT_SETTINGS))
    _deep_merge(merged, obj)
    return merged

def save_settings(settings: dict, path: str | Path = "saves/settings.json") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(settings, indent=2), encoding="utf-8")

def apply_settings(app, settings: dict) -> None:
    """
    Applies resolution/fullscreen and fps cap. Also sets mixer volumes if mixer is loaded.
    """
    import pygame

    # Video
    fs = settings["video"].get("fullscreen", False)
    w, h = settings["video"].get("resolution", [1280, 720])
    flags = pygame.FULLSCREEN if fs else 0
    app.WIDTH, app.HEIGHT = int(w), int(h)
    app.screen = pygame.display.set_mode((app.WIDTH, app.HEIGHT), flags)
    pygame.display.set_caption(app.TITLE)

    # FPS
    app.FPS = int(settings["video"].get("fps_cap", 60))

    # Audio
    master = float(settings["audio"].get("master", 0.8))
    music = float(settings["audio"].get("music", 0.7))
    sfx = float(settings["audio"].get("sfx", 0.8))
    mute = bool(settings["audio"].get("mute", False))
    vol_master = 0.0 if mute else max(0.0, min(1.0, master))
    try:
        import pygame.mixer  # ensure exists even if not pre-inited
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.set_volume(vol_master * music)
        # For SFX you’d set each Sound’s volume when creating it; as a simple global:
        pygame.mixer.set_num_channels(16)
        for ch in range(pygame.mixer.get_num_channels()):
            pygame.mixer.Channel(ch).set_volume(vol_master * sfx)
    except Exception:
        # no mixer available = skip
        pass
