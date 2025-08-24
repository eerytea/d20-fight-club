# ui/state_settings.py
import pygame
from typing import Optional, List
from .app import UIState
from .uiutil import draw_text, BIG, FONT, Button, Checkbox, Slider, Dropdown
from core.config import load_settings, save_settings, apply_settings, DEFAULT_SETTINGS

RES_PRESETS = [
    "1280 x 720",
    "1366 x 768",
    "1600 x 900",
    "1920 x 1080",
    "2560 x 1440",
    "3840 x 2160",
]

def _parse_res(s: str) -> tuple[int,int]:
    w, h = s.split("x")
    return int(w.strip()), int(h.strip())

class SettingsState(UIState):
    def __init__(self):
        self.buttons: List[Button] = []
        self.widgets: List[object] = []  # Checkbox/Slider/Dropdown
        self.settings = load_settings()
        self._res_dropdown: Optional[Dropdown] = None
        self._fs_checkbox: Optional[Checkbox] = None
        self._fps_slider: Optional[Slider] = None
        self._mvol: Optional[Slider] = None
        self._uvol: Optional[Slider] = None
        self._svol: Optional[Slider] = None
        self._mute: Optional[Checkbox] = None

    def on_enter(self) -> None:
        W = pygame._app_ref.WIDTH  # type: ignore[attr-defined]
        # buttons
        self.buttons = [
            Button(pygame.Rect(24, 24, 120, 40), "Back", on_click=self._back),
            Button(pygame.Rect(24+140, 24, 140, 40), "Apply", on_click=self._apply),
            Button(pygame.Rect(24+300, 24, 180, 40), "Reset Defaults", on_click=self._reset_defaults),
            Button(pygame.Rect(24+500, 24, 160, 40), "Save", on_click=self._save),
        ]

        # --- Video group ---
        y = 100
        draw_anchor = y  # visual alignment only
        fs = bool(self.settings["video"]["fullscreen"])
        res = self.settings["video"]["resolution"]
        fps_cap = int(self.settings["video"]["fps_cap"])
        init_res_label = f"{res[0]} x {res[1]}"
        if init_res_label not in RES_PRESETS:
            RES_PRESETS.insert(0, init_res_label)

        self._fs_checkbox = Checkbox(pygame.Rect(24, y, 26, 26), "Fullscreen", checked=fs,
                                     on_toggle=lambda val: self._set("video.fullscreen", val))
        self._res_dropdown = Dropdown(pygame.Rect(24+220, y-6, 220, 34), RES_PRESETS,
                                      index=RES_PRESETS.index(init_res_label),
                                      on_select=lambda v: self._set("video.resolution", list(_parse_res(v))))
        self._fps_slider = Slider(pygame.Rect(24+480, y-4, 220, 28), value=max(10, min(240, fps_cap))/240.0,
                                  on_change=lambda t: self._set("video.fps_cap", int(10 + t*230)))

        # --- Audio group ---
        y = draw_anchor + 80
        mute = bool(self.settings["audio"]["mute"])
        m = float(self.settings["audio"]["master"])
        mu = float(self.settings["audio"]["music"])
        sx = float(self.settings["audio"]["sfx"])
        self._mute = Checkbox(pygame.Rect(24, y, 26, 26), "Mute All", checked=mute,
                              on_toggle=lambda val: self._set("audio.mute", val))
        self._mvol = Slider(pygame.Rect(24+220, y-4, 220, 28), value=m, on_change=lambda t: self._set("audio.master", round(t,2)))
        self._uvol = Slider(pygame.Rect(24+480, y-4, 220, 28), value=mu, on_change=lambda t: self._set("audio.music", round(t,2)))
        self._svol = Slider(pygame.Rect(24+740, y-4, 220, 28), value=sx, on_change=lambda t: self._set("audio.sfx", round(t,2)))

        self.widgets = [self._fs_checkbox, self._res_dropdown, self._fps_slider,
                        self._mute, self._mvol, self._uvol, self._svol]

    def on_exit(self) -> None:
        self.buttons.clear()
        self.widgets.clear()

    # ----- helpers -----
    def _set(self, dotted_key: str, value):
        # dotted path update
        cur = self.settings
        parts = dotted_key.split(".")
        for p in parts[:-1]:
            cur = cur[p]
        cur[parts[-1]] = value

    def _apply(self):
        from core.config import apply_settings
        apply_settings(pygame._app_ref, self.settings)  # type: ignore[attr-defined]

    def _save(self):
        save_settings(self.settings)

    def _reset_defaults(self):
        self.settings = json_clone(DEFAULT_SETTINGS)
        self.on_enter()  # rebuild widgets with fresh values

    def _back(self):
        # apply before leaving? up to you; here we just go back
        pygame._app_ref.pop_state()  # type: ignore[attr-defined]

    # ----- UIState impl -----
    def handle_event(self, event: pygame.event.Event):
        for b in self.buttons: b.handle_event(event)
        for w in self.widgets:
            w.handle_event(event)  # type: ignore[attr-defined]

    def update(self, dt: float): pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((18,18,22))
        draw_text(surface, "Settings", (24, 24), font=BIG)
        for b in self.buttons: b.draw(surface)

        # labels
        draw_text(surface, "Video", (24, 80), font=BIG)
        draw_text(surface, "Resolution", (24+220, 80), font=FONT)
        fps_cap = int(self.settings["video"]["fps_cap"])
        draw_text(surface, f"FPS Cap: {fps_cap}", (24+480, 80), font=FONT)

        draw_text(surface, "Audio", (24, 160), font=BIG)
        mv = int(self.settings["audio"]["master"]*100)
        muv = int(self.settings["audio"]["music"]*100)
        sv = int(self.settings["audio"]["sfx"]*100)
        draw_text(surface, f"Master {mv}%", (24+220, 160), font=FONT)
        draw_text(surface, f"Music {muv}%", (24+480, 160), font=FONT)
        draw_text(surface, f"SFX {sv}%", (24+740, 160), font=FONT)

        for w in self.widgets:
            w.draw(surface)  # type: ignore[attr-defined]

def json_clone(obj: dict) -> dict:
    import json
    return json.loads(json.dumps(obj))
