# ui/state_match.py
import pygame
from typing import Optional, List
from .app import UIState
from .uiutil import draw_text, BIG, FONT, Button
from core.career import new_career
from core.sim import GRID_W, GRID_H
from engine import TBCombat, Team, fighter_from_dict, layout_teams_tiles

SIDEBAR_W = 380

class MatchState(UIState):
    def __init__(self, app, exhibition: bool = True, teams: Optional[tuple[int,int]] = None):
        self.app = app
        self.exhibition = exhibition
        self.teams = teams
        self.buttons: List[Button] = []
        self.log: List[str] = []
        self.auto = False
        self._auto_timer = 0.0
        self.combat: Optional[TBCombat] = None

    def on_enter(self) -> None:
        W = self.app.WIDTH
        self.buttons = [
            Button(pygame.Rect(16, 16, 110, 36), "Back", on_click=self._back),
            Button(pygame.Rect(136, 16, 110, 36), "Reset", on_click=self._reset),
            Button(pygame.Rect(256, 16, 130, 36), "Next Turn", on_click=self._next),
            Button(pygame.Rect(396, 16, 130, 36), "Auto: OFF", on_click=self._toggle_auto),
        ]
        self._setup_match()

    def on_exit(self) -> None:
        self.buttons.clear()

    def _setup_match(self):
        # Create quick teams from a career to get rosters
        car = new_career(seed=424242, team_count=20)
        tidA, tidB = (0, 1) if not self.teams else self.teams
        tA = Team(0, car.team_names[tidA], tuple(car.team_colors[tidA]))
        tB = Team(1, car.team_names[tidB], tuple(car.team_colors[tidB]))
        # pick top 4 by OVR
        def top4(tid): 
            return sorted(car.rosters[tid], key=lambda f: f.get("ovr", 50), reverse=True)[:4]
        fighters = [fighter_from_dict({**fd, "team_id":0}) for fd in top4(tidA)] + \
                   [fighter_from_dict({**fd, "team_id":1}) for fd in top4(tidB)]
        layout_teams_tiles(fighters, GRID_W, GRID_H)
        self.combat = TBCombat(tA, tB, fighters, GRID_W, GRID_H, seed=999)
        self.log = []
        self._drain_log()  # print initial init/round events

    def _back(self):
        from .state_menu import MenuState
        self.app.replace_state(MenuState())

    def _reset(self):
        self._setup_match()

    def _toggle_auto(self):
        self.auto = not self.auto
        self.buttons[3].label = f"Auto: {'ON' if self.auto else 'OFF'}"

    def _next(self):
        if not self.combat or self.combat.winner is not None:
            return
        before = len(self.combat.events)
        self.combat.take_turn()
        self._drain_log(start=before)

    def _drain_log(self, start: int = 0):
        if not self.combat: return
        for e in self.combat.events[start:]:
            k = e.kind; p = e.payload
            if k == "init":           self._push(f"Init: {p['name']} = {p['init']}")
            elif k == "round_start":  self._push(f"— Round {p['round']} —")
            elif k == "turn_start":   self._push(f"{p['actor']}'s turn")
            elif k == "move_step":    self._push(f"  moves to {p['to']}")
            elif k == "attack":
                txt = f"  attacks {p['defender']} (d20={p['nat']} vs AC {p['target_ac']})"
                if p.get("critical"): txt += " — CRIT!"
                if not p['hit']:      txt += " — MISS"
                self._push(txt)
            elif k == "damage":       self._push(f"    → {p['defender']} takes {p['amount']} (HP {p['hp_after']})")
            elif k == "down":         self._push(f"    ✖ {p['name']} is down")
            elif k == "end":
                if "winner" in p:     self._push(f"Match ends — Winner: {p['winner']} ({p.get('reason','')})")
                else:                 self._push(f"Match ends — Draw ({p.get('reason','')})")
            elif k == "round_end":    self._push(f"— End Round {p['round']} —")

    def _push(self, s: str):
        self.log.append(s)
        self.log = self.log[-28:]  # cap

    def handle_event(self, event: pygame.event.Event) -> Optional["UIState"]:
        for b in self.buttons: b.handle_event(event)
        return None

    def update(self, dt: float) -> Optional["UIState"]:
        if self.auto and self.combat and self.combat.winner is None:
            self._auto_timer -= dt
            if self._auto_timer <= 0.0:
                self._next()
                self._auto_timer = 0.35
        return None

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((16, 18, 24))
        for b in self.buttons: b.draw(surface)

        # arena grid
        arena_w = surface.get_width() - SIDEBAR_W
        arena_h = surface.get_height()
        cell_w = max(24, arena_w // GRID_W)
        cell_h = max(24, arena_h // GRID_H)
        for gx in range(GRID_W):
            pygame.draw.line(surface, (34,36,44), (gx*cell_w, 0), (gx*cell_w, arena_h))
        for gy in range(GRID_H):
            pygame.draw.line(surface, (34,36,44), (0, gy*cell_h), (arena_w, gy*cell_h))

        # fighters
        if self.combat:
            for f in self.combat.fighters:
                if not f.alive: continue
                cx = f.tx * cell_w + cell_w//2
                cy = f.ty * cell_h + cell_h//2
                col = (120,180,255) if f.team_id == 0 else (255,140,140)
                pygame.draw.circle(surface, col, (cx, cy), min(cell_w, cell_h)//3)
                frac = max(0.0, min(1.0, f.hp / max(1, f.max_hp)))
                bw, bh = int(cell_w*0.8), 6
                bx, by = cx - bw//2, cy - (cell_h//2) + 4
                pygame.draw.rect(surface, (60,62,70), pygame.Rect(bx, by, bw, bh), border_radius=4)
                c = (90,220,140) if frac>0.5 else (240,210,120) if frac>0.25 else (240,120,120)
                pygame.draw.rect(surface, c, pygame.Rect(bx+1, by+1, int((bw-2)*frac), bh-2), border_radius=4)
                nm = FONT.render(f.name, True, (235,238,240))
                surface.blit(nm, (cx - nm.get_width()//2, cy + 6))

        # sidebar log
        x0 = arena_w
        pygame.draw.rect(surface, (20,22,30), pygame.Rect(x0, 0, SIDEBAR_W, surface.get_height()))
        draw_text(surface, "Turn Log", (x0 + 16, 16), font=BIG)
        y = 64
        for line in self.log:
            draw_text(surface, line, (x0 + 16, y), font=FONT)
            y += 22
