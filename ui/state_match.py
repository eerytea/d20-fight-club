from __future__ import annotations

import pygame
from pygame import Rect
from typing import Any, Dict, List, Optional, Tuple

from engine.tbcombat import TBCombat

# Reputation hook
try:
    from core.usecases.integration_points import on_match_finalized
except Exception:
    def on_match_finalized(*a, **k):  # graceful no-op
        pass

# UI helpers
try:
    from ui.uiutil import Theme, Button, draw_text, panel
except Exception:
    Theme = None
    class Button:
        def __init__(self, rect, label, cb, enabled=True):
            self.rect = rect
            self.label = label
            self.cb = cb
            self.enabled = enabled
        def draw(self, screen):
            pygame.draw.rect(screen, (60,60,70), self.rect, border_radius=6)
            font = pygame.font.SysFont("arial", 18)
            surf = font.render(self.label, True, (255,255,255))
            screen.blit(surf, (self.rect.x+8, self.rect.y+6))
        def handle(self, ev):
            if ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos) and self.enabled:
                self.cb()
    def draw_text(surface, text, x, y, color=(255,255,255), size=20):
        font = pygame.font.SysFont("arial", size)
        surf = font.render(text, True, color)
        surface.blit(surf, (x, y))
    def panel(surface, rect, color=(40,40,40)):
        pygame.draw.rect(surface, color, rect, border_radius=6)

def _fmt_name(s: str) -> str:
    if not s:
        return "?"
    parts = s.split()
    if len(parts) == 1:
        return parts[0][:12]
    return f"{parts[0][0]}. {parts[-1]}"[:14]

class MatchState:
    """
    Minimal match viewer:
      - Next Turn / Next Round / Auto / Finish
      - Grid draw + HP/name
      - Event log
    """
    def __init__(self, app, career, fixture: Any, fighters: List[Dict], grid_w=11, grid_h=11, seed: Optional[int]=None, on_finish=None):
        self.app = app
        self.career = career
        self.fixture = fixture
        self.on_finish = on_finish

        # Resolve teams & rosters
        self.home_tid, self.away_tid = self._resolve_fixture_ids(fixture)
        self.home_name = self._team_name(self.home_tid)
        self.away_name = self._team_name(self.away_tid)

        # Build engine
        self.combat = TBCombat(self.home_name, self.away_name, fighters, grid_w=grid_w, grid_h=grid_h, seed=seed)
        # If you attach OIs to a fixture/session, set them here:
        oi = getattr(fixture, "opposition_instructions", None)
        if oi is None and isinstance(fixture, dict):
            oi = fixture.get("opposition_instructions")
        if oi:
            self.combat.opposition_instructions = oi

        self.auto = False
        self.result: Dict[str, Any] = {}
        self._build_buttons()

        # Layout rects
        self.rc_grid = Rect(20, 60, 480, 480)
        self.rc_log  = Rect(520, 60, 360, 480)
        self.rc_hdr  = Rect(20, 20, 860, 30)

        self._log_scroll = 0

    # --- helpers -------------------------------------------------------------

    def _team_name(self, tid: Any) -> str:
        # Prefer career helper
        if hasattr(self.career, "team_name"):
            try:
                return str(self.career.team_name(tid))
            except Exception:
                pass
        # Try teams list/dict
        teams = getattr(self.career, "teams", None)
        if isinstance(teams, list):
            for t in teams:
                if str(t.get("tid", t.get("id", t.get("team_id")))) == str(tid):
                    return t.get("name", f"Team {tid}")
        if isinstance(teams, dict):
            t = teams.get(str(tid)) or teams.get(int(tid)) if str(tid).isdigit() else None
            if t: return t.get("name", f"Team {tid}")
        # Fallback
        return f"Team {tid}"

    def _resolve_fixture_ids(self, fx: Any) -> Tuple[Any, Any]:
        # Supports object or dict with varied keys
        if not isinstance(fx, dict):
            home = getattr(fx, "home_id", getattr(fx, "home_tid", getattr(fx, "home", getattr(fx, "A", None))))
            away = getattr(fx, "away_id", getattr(fx, "away_tid", getattr(fx, "away", getattr(fx, "B", None))))
            return home, away
        return (fx.get("home_id") or fx.get("home_tid") or fx.get("home") or fx.get("A"),
                fx.get("away_id") or fx.get("away_tid") or fx.get("away") or fx.get("B"))

    # --- buttons & actions ---------------------------------------------------

    def _build_buttons(self):
        w, h = self.app.screen.get_size()
        bx = 20
        by = 560
        bw = 140
        bh = 36
        gap = 12
        self.btn_next_turn = Button(Rect(bx, by, bw, bh), "Next Turn", self._on_next_turn)
        self.btn_next_round = Button(Rect(bx + (bw+gap), by, bw, bh), "Next Round", self._on_next_round)
        self.btn_auto = Button(Rect(bx + 2*(bw+gap), by, bw, bh), "Auto", self._on_auto)
        self.btn_finish = Button(Rect(bx + 3*(bw+gap), by, bw, bh), "Finish", self._on_finish_clicked)

        self._buttons = [self.btn_next_turn, self.btn_next_round, self.btn_auto, self.btn_finish]

    def _on_next_turn(self):
        if self.combat.winner is None:
            self.combat.take_turn()

    def _on_next_round(self):
        if self.combat.winner is not None:
            return
        # drain until next round header appears
        curr_r = self.combat.round
        while self.combat.winner is None and self.combat.round == curr_r:
            self.combat.take_turn()

    def _on_auto(self):
        self.auto = not self.auto
        self.btn_auto.label = "Auto (on)" if self.auto else "Auto"

    def _on_finish_clicked(self):
        # prepare a minimal result
        k_home = sum(1 for ev in self.combat.typed_events if ev.get("type") == "down" and self._was_enemy(ev["name"], team=1))
        k_away = sum(1 for ev in self.combat.typed_events if ev.get("type") == "down" and self._was_enemy(ev["name"], team=0))
        self.result = {
            "home_tid": self.home_tid, "away_tid": self.away_tid,
            "K_home": k_home, "K_away": k_away,
            "winner": self.combat.winner
        }

        # persist via external callback if provided
        if self.on_finish:
            try:
                self.on_finish(self.result)
            except Exception:
                pass

        # reputation hook
        try:
            on_match_finalized(self.career, str(self.home_tid), str(self.away_tid), int(k_home), int(k_away),
                               comp_kind=(getattr(self.fixture, "comp_kind", None) or (self.fixture.get("comp_kind") if isinstance(self.fixture, dict) else "league")) or "league",
                               home_advantage='a')
        except Exception:
            pass

        # back to hub
        self.app.pop_state()

    def _was_enemy(self, name: str, team: int) -> bool:
        # if team==1, we count downs on team1 as scored by team0 (home), etc.
        return True  # simple; you can refine by tracking who was downed by whom

    # --- pygame loop ---------------------------------------------------------

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.app.pop_state()
            return
        if ev.type == pygame.MOUSEWHEEL:
            self._log_scroll = max(0, self._log_scroll - ev.y)
        for b in self._buttons:
            if hasattr(b, "handle"):
                b.handle(ev)

    def update(self, dt):
        if self.auto and self.combat.winner is None:
            # run a few steps per frame to move things along
            for _ in range(6):
                if self.combat.winner is None:
                    self.combat.take_turn()

    def draw(self, screen):
        screen.fill((12, 12, 16))
        # header
        panel(screen, self.rc_hdr, color=(30,30,38))
        draw_text(screen, f"{self.home_name}  vs  {self.away_name}   (Round {self.combat.round})", self.rc_hdr.x+8, self.rc_hdr.y+6, (235,235,240), 22)

        # grid
        panel(screen, self.rc_grid, color=(24,24,28))
        self._draw_grid(screen, self.rc_grid)

        # log
        panel(screen, self.rc_log, color=(24,24,28))
        self._draw_log(screen, self.rc_log)

        for b in self._buttons:
            if hasattr(b, "draw"):
                b.draw(screen)

    # --- draw helpers --------------------------------------------------------

    def _draw_grid(self, screen, rect: Rect):
        W, H = self.combat.W, self.combat.H
        tile = min(rect.w // W, rect.h // H)
        ox = rect.x + (rect.w - tile*W) // 2
        oy = rect.y + (rect.h - tile*H) // 2
        # grid lines
        for gx in range(W + 1):
            x = ox + gx*tile
            pygame.draw.line(screen, (40,40,48), (x, oy), (x, oy + tile*H))
        for gy in range(H + 1):
            y = oy + gy*tile
            pygame.draw.line(screen, (40,40,48), (ox, y), (ox + tile*W, y))

        # draw units
        for f in self.combat.fighters_all:
            if not f.alive or f.hp <= 0:
                continue
            color = (200,60,60) if f.team_id == 0 else (70,120,220)
            x = ox + f.x*tile
            y = oy + f.y*tile
            r = max(4, tile//3)
            pygame.draw.circle(screen, color, (x + tile//2, y + tile//2), r)
            # hp bar
            hpw = int(tile * max(0.2, min(1.0, f.hp / max(1, f.max_hp))))
            pygame.draw.rect(screen, (20,20,24), Rect(x, y + tile - 6, tile, 5))
            pygame.draw.rect(screen, (60,220,80), Rect(x, y + tile - 6, hpw, 5))
            # name
            draw_text(screen, _fmt_name(f.name), x + 2, y + 2, (230,230,235), size=max(12, min(16, tile//2)))

    def _draw_log(self, screen, rect: Rect):
        draw_text(screen, "Event Log", rect.x+8, rect.y+6, (200,200,210), 18)
        y = rect.y + 30
        line_h = 20
        evs = self.combat.typed_events
        start = self._log_scroll
        end = min(len(evs), start + (rect.h - 40)//line_h)
        for i in range(start, end):
            e = evs[i]
            t = e.get("type")
            if t == "round":
                msg = f"— Round {e['round']} —"
                col = (240,210,120)
            elif t == "move":
                msg = f"{e['name']} → {e['to']}"
                col = (210,210,220)
            elif t == "hit":
                msg = f"{e['name']} hit {e['target']} ({e['dmg']})"
                col = (240,120,120)
            elif t == "miss":
                msg = f"{e['name']} missed {e['target']}"
                col = (180,180,190)
            elif t == "down":
                msg = f"{e['name']} is down!"
                col = (255,170,60)
            elif t == "blocked":
                msg = f"{e['name']} blocked at {e['at']}"
                col = (160,160,180)
            elif t == "end":
                w = e.get("winner")
                msg = f"Match End — Winner: {'Home' if w == 0 else ('Away' if w == 1 else 'None')}"
                col = (120,220,160)
            else:
                msg = str(e)
                col = (200,200,200)
            draw_text(screen, msg, rect.x+8, y, col, 16)
            y += line_h
