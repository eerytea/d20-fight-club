from __future__ import annotations

import pygame
from pygame import Rect
from typing import Any, Dict, List, Optional

# Engine
try:
    from engine.tbcombat import TBCombat
except Exception:
    TBCombat = None

# Fighter/roster helpers
try:
    from core.adapters import as_fighter_dict, roster_for_team
except Exception:
    def as_fighter_dict(p, default_team_id=0, default_pid=0):
        d = dict(p) if isinstance(p, dict) else p.__dict__.copy()
        d.setdefault("pid", d.get("id", default_pid))
        d.setdefault("name", d.get("n", f"P{d['pid']}"))
        d.setdefault("team_id", d.get("tid", default_team_id))
        d.setdefault("hp", d.get("HP", 10))
        d.setdefault("max_hp", d.get("max_hp", d.get("HP_max", d.get("hp", 10))))
        d.setdefault("ac", d.get("AC", 10))
        d.setdefault("alive", d.get("alive", True))
        return d
    def roster_for_team(career, tid, team_slot):
        team = next((t for t in getattr(career, "teams", []) if str(t.get("tid", t.get("id"))) == str(tid)), {"fighters": []})
        return [as_fighter_dict(p, default_team_id=team_slot, default_pid=i) for i,p in enumerate(team.get("fighters", []))]

# Tiny UI kit fallback
try:
    from ui.uiutil import Theme, Button, draw_text, panel
except Exception:
    Theme = None
    class Button:
        def __init__(self, rect, label, cb, enabled=True):
            self.rect, self.label, self.cb, self.enabled = rect, label, cb, enabled
        def draw(self, screen):
            pygame.draw.rect(screen, (60,60,70) if self.enabled else (40,40,48), self.rect, border_radius=6)
            font = pygame.font.SysFont("arial", 18)
            screen.blit(font.render(self.label, True, (255,255,255) if self.enabled else (180,180,180)),
                        (self.rect.x+8, self.rect.y+6))
        def handle(self, ev):
            if self.enabled and ev.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(ev.pos):
                self.cb()
    def draw_text(surface, text, x, y, color=(230,230,235), size=20):
        font = pygame.font.SysFont("arial", size)
        surface.blit(font.render(str(text), True, color), (x, y))
    def panel(surface, rect, color=(30,30,38)):
        pygame.draw.rect(surface, color, rect, border_radius=8)

def _team_by_tid(career, tid):
    for t in getattr(career, "teams", []):
        if str(t.get("tid", t.get("id"))) == str(tid):
            return t
    return None

class MatchState:
    """
    League match viewer:
      - Builds rosters from the career + fixture
      - Controls: Next Turn / Next Round / Auto / Finish
      - On Finish: saves result back to career.record_result(...)
    """
    def __init__(self, app, career, fixture: Optional[Dict[str, Any]] = None, grid_w=11, grid_h=11, on_finish=None):
        self.app = app
        self.career = career
        self.fixture = fixture  # expected canonical keys: home_id, away_id, ...
        self.auto = False
        self.on_finish = on_finish

        if fixture is None:
            # Try to find user's fixture this week as a fallback
            fx_list = career.fixtures_for_week(getattr(career, "week", 1))
            user_tid = getattr(career, "user_tid", None)
            cand = None
            for fx in fx_list:
                if not fx.get("played"):
                    if user_tid is None or str(fx.get("home_id")) == str(user_tid) or str(fx.get("away_id")) == str(user_tid):
                        cand = fx; break
            self.fixture = cand

        if self.fixture is None:
            raise RuntimeError("No playable fixture found for MatchState.")

        self.home_tid = int(self.fixture.get("home_id", self.fixture.get("home_tid", self.fixture.get("A", 0))))
        self.away_tid = int(self.fixture.get("away_id", self.fixture.get("away_tid", self.fixture.get("B", 1))))
        self.home_name = career.team_name(self.home_tid)
        self.away_name = career.team_name(self.away_tid)

        # Build fighters (normalize) for engine: home team_id=0, away=1
        home_roster = roster_for_team(career, self.home_tid, team_slot=0)
        away_roster = roster_for_team(career, self.away_tid, team_slot=1)
        fighters = [as_fighter_dict(p, default_team_id=0, default_pid=i) for i,p in enumerate(home_roster)]
        fighters += [as_fighter_dict(p, default_team_id=1, default_pid=i) for i,p in enumerate(away_roster)]

        seed = getattr(career, "seed", 12345)
        if TBCombat is None:
            raise RuntimeError("TBCombat not available")
        # Accept kw aliases GRID_W/GRID_H via tbcombat
        self.combat = TBCombat(self.home_name, self.away_name, fighters, grid_w=grid_w, grid_h=grid_h, seed=seed)

        # Layout & state
        self._log_scroll = 0
        self.rc_hdr = Rect(20, 20, 860, 40)
        self.rc_grid = Rect(20, 70, 480, 480)
        self.rc_log  = Rect(520, 70, 360, 480)
        self.rc_btns = Rect(20, 560, 860, 40)
        self._build_buttons()

    def _build_buttons(self):
        bx, by, bw, bh, gap = self.rc_btns.x, self.rc_btns.y, 140, 36, 10
        self.btn_turn = Button(Rect(bx, by, bw, bh), "Next Turn", self._next_turn)
        self.btn_round = Button(Rect(bx + (bw+gap), by, bw, bh), "Next Round", self._next_round)
        self.btn_auto = Button(Rect(bx + 2*(bw+gap), by, bw, bh), "Auto", self._toggle_auto)
        self.btn_finish = Button(Rect(bx + 3*(bw+gap), by, bw, bh), "Finish", self._finish)
        self._buttons = [self.btn_turn, self.btn_round, self.btn_auto, self.btn_finish]

    # --- events ---
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self._finish(); return
        if ev.type == pygame.MOUSEWHEEL and self.rc_log.collidepoint(ev.pos):
            self._log_scroll = max(0, self._log_scroll - ev.y)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            for b in self._buttons:
                b.handle(ev)

    def update(self, dt):
        if self.auto and self.combat.winner is None:
            # modest speed so UI stays responsive
            for _ in range(6):
                self.combat.take_turn()

    def draw(self, screen):
        screen.fill((12,12,16))
        panel(screen, self.rc_hdr)
        title = f"{self.home_name} vs {self.away_name}   (Round {self.combat.round})"
        if self.combat.winner is not None:
            title += f" — Winner: {'Home' if self.combat.winner==0 else 'Away' if self.combat.winner==1 else 'None'}"
        draw_text(screen, title, self.rc_hdr.x+10, self.rc_hdr.y+8, size=22)

        panel(screen, self.rc_grid, color=(24,24,28))
        self._draw_grid(screen, self.rc_grid)

        panel(screen, self.rc_log, color=(24,24,28))
        self._draw_log(screen, self.rc_log)

        for b in self._buttons:
            b.draw(screen)

    # --- draw helpers ---
    def _draw_grid(self, screen, rect: Rect):
        W, H = self.combat.W, self.combat.H
        tile = max(8, min(rect.w // W, rect.h // H))
        ox = rect.x + (rect.w - tile*W) // 2
        oy = rect.y + (rect.h - tile*H) // 2

        for gx in range(W + 1):
            x = ox + gx*tile
            pygame.draw.line(screen, (40,40,48), (x, oy), (x, oy + tile*H))
        for gy in range(H + 1):
            y = oy + gy*tile
            pygame.draw.line(screen, (40,40,48), (ox, y), (ox + tile*W, y))

        # units
        for f in self.combat.fighters_all:
            if not getattr(f, "alive", True) or getattr(f, "hp", 0) <= 0:
                continue
            color = (200,60,60) if f.team_id == 0 else (70,120,220)
            x = ox + f.x*tile; y = oy + f.y*tile
            r = max(4, tile//3)
            pygame.draw.circle(screen, color, (x + tile//2, y + tile//2), r)
            # hp bar
            hpw = int(tile * max(0.2, min(1.0, f.hp / max(1, f.max_hp))))
            pygame.draw.rect(screen, (20,20,24), Rect(x, y + tile - 6, tile, 5))
            pygame.draw.rect(screen, (60,220,80), Rect(x, y + tile - 6, hpw, 5))
            # name
            self._txt(screen, f.name[:12], x + 2, y + 2, 16)

    def _draw_log(self, screen, rect: Rect):
        self._txt(screen, "Event Log", rect.x+8, rect.y+6, 18, (210,210,220))
        y = rect.y + 30
        line_h = 20
        evs = getattr(self.combat, "typed_events", [])
        start = self._log_scroll
        end = min(len(evs), start + (rect.h - 40)//line_h)
        for i in range(start, end):
            e = evs[i]
            t = e.get("type")
            if t == "round":
                msg = f"— Round {e['round']} —"; col = (240,210,120)
            elif t == "move":
                msg = f"{e['name']} → {e['to']}"; col = (210,210,220)
            elif t == "hit":
                msg = f"{e['name']} hit {e['target']} ({e['dmg']})"; col = (240,120,120)
            elif t == "miss":
                msg = f"{e['name']} missed {e['target']}"; col = (180,180,190)
            elif t == "down":
                msg = f"{e['name']} is down!"; col = (255,170,60)
            elif t == "blocked":
                msg = f"{e['name']} blocked at {e['at']}"; col = (160,160,180)
            elif t == "end":
                w = e.get("winner")
                msg = f"Match End — Winner: {'Home' if w == 0 else ('Away' if w == 1 else 'None')}"; col = (120,220,160)
            else:
                msg = str(e); col = (200,200,200)
            self._txt(screen, msg, rect.x+8, y, 16, col); y += line_h

    def _txt(self, screen, text, x, y, size=16, color=(230,230,235)):
        draw_text(screen, text, x, y, color, size)

    # --- actions ---
    def _next_turn(self):
        if self.combat.winner is None:
            self.combat.take_turn()

    def _next_round(self):
        if self.combat.winner is not None:
            return
        curr = self.combat.round
        while self.combat.winner is None and self.combat.round == curr:
            self.combat.take_turn()

    def _toggle_auto(self):
        self.auto = not self.auto
        self.btn_auto.label = "Auto (on)" if self.auto else "Auto"

    def _finish(self):
        # Derive K_home/K_away from downed units
        k_home, k_away = self._kills_by_side()
        winner = 0 if k_home > k_away else (1 if k_away > k_home else None)

        result = {
            "home_id": self.home_tid,
            "away_id": self.away_tid,
            "k_home": int(k_home),
            "k_away": int(k_away),
            "winner": winner,
        }

        try:
            # Save to career
            self.career.record_result(result)
        except Exception:
            # If saving fails, we still exit the match
            pass

        # Optional external callback
        if callable(self.on_finish):
            try:
                self.on_finish(result)
            except Exception:
                pass

        # Back to previous screen
        self.app.pop_state()

    def _kills_by_side(self) -> (int, int):
        """Home kills = away fighters down; Away kills = home fighters down."""
        # Prefer counting from final fighter states; fall back to events if needed
        home_down = sum(1 for f in self.combat.fighters_all if f.team_id == 0 and (not f.alive or f.hp <= 0))
        away_down = sum(1 for f in self.combat.fighters_all if f.team_id == 1 and (not f.alive or f.hp <= 0))
        # K_home = away downed; K_away = home downed
        return int(away_down), int(home_down)
