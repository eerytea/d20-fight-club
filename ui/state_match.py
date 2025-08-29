# ui/state_match.py
from __future__ import annotations
import pygame
from typing import Any, Dict, List, Optional, Tuple

from engine.tbcombat import TBCombat, Team
from engine.constants import GRID_COLS, GRID_ROWS
from engine.team_tactics import load_match_tactics, TacticsController

# Optional helpers if present in your project; all of these calls are guarded.
# They make it easier to place units and/or pull teams from a career fixture.
try:
    from engine.grid import layout_teams_tiles  # auto-lay outer bands
except Exception:  # pragma: no cover
    layout_teams_tiles = None

SHORT_LOG_ROWS = 18


def _short_name(name: str) -> str:
    if not name:
        return "?"
    parts = name.split()
    if len(parts) == 1:
        return parts[0][:10]
    first = parts[0][:1] + "."
    last = parts[-1]
    return f"{first} {last}"[:12]


def _get_color(team_like: Any, fallback=(180, 180, 180)):
    # Accept either Team dataclass, dict with 'color', or anything with .color
    try:
        c = getattr(team_like, "color", None)
        if isinstance(c, (tuple, list)) and len(c) == 3:
            return tuple(int(x) for x in c)
    except Exception:
        pass
    if isinstance(team_like, dict):
        c = team_like.get("color")
        if isinstance(c, (tuple, list)) and len(c) == 3:
            return tuple(int(x) for x in c)
    return fallback


def _team_name(team_like: Any, fallback: str) -> str:
    try:
        n = getattr(team_like, "name", None)
        if n:
            return str(n)
    except Exception:
        pass
    if isinstance(team_like, dict) and team_like.get("name"):
        return str(team_like["name"])
    return fallback


class MatchState:
    """
    Match viewer:
      - Grid board with colored unit dots, inline HP bars, short names.
      - Scrollable log (last N rows shown).
      - Controls: Space=Play/Pause, N=Next Turn, R=Next Round, Esc/Backspace=Back.
      - Resizes with window; the board expands to fill remaining space.
      - Patch G: reads fixture['tactics'] and attaches TacticsControllers.
    """
    def __init__(self, app):
        self.app = app
        self.context: Dict[str, Any] = {}
        self.font: Optional[pygame.font.Font] = None
        self.small: Optional[pygame.font.Font] = None

        self.career = None
        self.fixture: Dict[str, Any] = {}
        self.teamA_info: Any = None
        self.teamB_info: Any = None

        self.combat: Optional[TBCombat] = None
        self.playing: bool = False
        self.tps: float = 8.0  # "turns per second" while playing
        self._accum: float = 0.0

        # layout rects (computed in draw based on window size)
        self.board_rect = pygame.Rect(0, 0, 0, 0)
        self.log_rect = pygame.Rect(0, 0, 0, 0)
        self.ctrl_rect = pygame.Rect(0, 0, 0, 0)

    # ---------- lifecycle ----------
    def enter(self, ctx: Dict[str, Any]):
        # Expected input:
        #  ctx["career"]: career object (optional but preferred)
        #  ctx["fixture"]: fixture dict for this match
        #  ctx["teamA"], ctx["teamB"]: optional visual/team info
        #  ctx["fighters"]: optional fully prepared fighters list
        #  OR ctx["lineup_home"], ctx["lineup_away"]: lists of fighter objs
        self.context = dict(ctx or {})
        self.career = self.context.get("career")
        self.fixture = dict(self.context.get("fixture", {}))

        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.SysFont("consolas", 18)
            self.small = pygame.font.SysFont("consolas", 14)

        # Build teams & fighters
        teamA_name = "Home"
        teamB_name = "Away"
        if self.career:
            # Try to use names/colors from career teams
            home_tid = self._get_fixture_tid(self.fixture, home=True)
            away_tid = self._get_fixture_tid(self.fixture, home=False)
            if isinstance(getattr(self.career, "teams", None), list):
                if 0 <= home_tid < len(self.career.teams):
                    self.teamA_info = self.career.teams[home_tid]
                    teamA_name = _team_name(self.teamA_info, "Home")
                if 0 <= away_tid < len(self.career.teams):
                    self.teamB_info = self.career.teams[away_tid]
                    teamB_name = _team_name(self.teamB_info, "Away")

        teamA = Team(0, teamA_name, _get_color(self.teamA_info, (60, 160, 230)))
        teamB = Team(1, teamB_name, _get_color(self.teamB_info, (220, 80, 80)))

        fighters = self.context.get("fighters")
        if not fighters:
            lh = list(self.context.get("lineup_home", []))
            la = list(self.context.get("lineup_away", []))
            fighters = self._blend_lineups(lh, la)

        # Ensure positions exist; if not, try to auto-layout
        missing_pos = [f for f in fighters if not hasattr(f, "tx") or not hasattr(f, "ty")]
        if missing_pos and layout_teams_tiles:
            try:
                layout_teams_tiles(fighters, GRID_COLS, GRID_ROWS)
            except Exception:
                pass

        # Seed if your career offers it
        seed = None
        if self.career:
            seed = getattr(self.career, "match_seed", None)
            if callable(seed):
                try:
                    home_tid = self._get_fixture_tid(self.fixture, True)
                    away_tid = self._get_fixture_tid(self.fixture, False)
                    week = int(self.fixture.get("week", getattr(self.career, "week", 1)))
                    season = getattr(self.career, "season", 1)
                    seed = self.career.match_seed(season, week, home_tid, away_tid)
                except Exception:
                    seed = None
            else:
                seed = None

        self.combat = TBCombat(teamA, teamB, fighters, GRID_COLS, GRID_ROWS, seed=seed)

        # ---- Patch G: tactics -> controllers wiring ----
        mt = load_match_tactics(self.fixture)
        tt_home = mt.by_team.get(0)
        tt_away = mt.by_team.get(1)
        if tt_home:
            self.combat.controllers[0] = TacticsController(tt_home)
        if tt_away:
            self.combat.controllers[1] = TacticsController(tt_away)
        # -----------------------------------------------

        self.playing = False
        self._accum = 0.0

    def _get_fixture_tid(self, fixture: Dict[str, Any], home: bool) -> int:
        # Try flexible keys: home_id/home_tid/A vs away_id/...
        if home:
            for k in ("home_id", "home_tid", "A", "home"):
                if k in fixture:
                    try:
                        return int(fixture[k])
                    except Exception:
                        pass
        else:
            for k in ("away_id", "away_tid", "B", "away"):
                if k in fixture:
                    try:
                        return int(fixture[k])
                    except Exception:
                        pass
        # Fallbacks
        return 0 if home else 1

    def _blend_lineups(self, home_fighters: List[Any], away_fighters: List[Any]) -> List[Any]:
        # Ensure team_id and 5v5 (if you passed more, we'll just accept them)
        out: List[Any] = []
        for f in home_fighters:
            try: setattr(f, "team_id", 0)
            except Exception: pass
            out.append(f)
        for f in away_fighters:
            try: setattr(f, "team_id", 1)
            except Exception: pass
            out.append(f)
        return out

    def exit(self):
        pass

    # ---------- input ----------
    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.app.pop_state()
                return
            if event.key == pygame.K_SPACE:
                # toggle play/pause
                if self.combat and self.combat.winner is None:
                    self.playing = not self.playing
            if event.key == pygame.K_n:
                # next turn
                self._step_turns(1)
            if event.key == pygame.K_r:
                # next round (advance until round increments or battle ends)
                if self.combat:
                    start_round = self.combat.round
                    while self.combat.winner is None and self.combat.round == start_round:
                        self.combat.take_turn()

    # ---------- update/draw ----------
    def update(self, dt: float):
        if not self.combat or self.combat.winner is not None:
            self.playing = False
            return
        if self.playing:
            self._accum += dt
            step = 1.0 / max(1e-3, self.tps)
            while self._accum >= step and self.combat and self.combat.winner is None:
                self._accum -= step
                self.combat.take_turn()

    def draw(self, screen):
        screen.fill((10, 10, 12))
        w, h = screen.get_size()

        # Layout: board on left, event log on right, controls below log
        log_w = max(360, int(w * 0.32))
        self.board_rect = pygame.Rect(12, 12, w - log_w - 24, h - 24)
        self.log_rect = pygame.Rect(w - log_w + 12, 12, log_w - 24, h - 86)
        self.ctrl_rect = pygame.Rect(w - log_w + 12, h - 68, log_w - 24, 56)

        self._draw_board(screen, self.board_rect)
        self._draw_log(screen, self.log_rect)
        self._draw_controls(screen, self.ctrl_rect)

    # ---------- helpers ----------
    def _draw_board(self, surf, rect: pygame.Rect):
        pygame.draw.rect(surf, (20, 22, 28), rect, border_radius=8)
        pygame.draw.rect(surf, (55, 58, 65), rect, width=2, border_radius=8)

        # grid
        cols, rows = GRID_COLS, GRID_ROWS
        cell_w = max(8, (rect.w - 16) // cols)
        cell_h = max(8, (rect.h - 16) // rows)
        ox = rect.x + (rect.w - cell_w * cols) // 2
        oy = rect.y + (rect.h - cell_h * rows) // 2

        # faint grid lines
        for c in range(cols + 1):
            x = ox + c * cell_w
            pygame.draw.line(surf, (30, 32, 38), (x, oy), (x, oy + rows * cell_h))
        for r in range(rows + 1):
            y = oy + r * cell_h
            pygame.draw.line(surf, (30, 32, 38), (ox, y), (ox + cols * cell_w, y))

        if not self.combat:
            return

        # draw fighters
        for f in self.combat.fighters:
            if not getattr(f, "alive", True) or getattr(f, "hp", 0) <= 0:
                continue
            try:
                x = int(getattr(f, "tx", getattr(f, "x", 0)))
                y = int(getattr(f, "ty", getattr(f, "y", 0)))
            except Exception:
                x, y = 0, 0
            cx = ox + x * cell_w + cell_w // 2
            cy = oy + y * cell_h + cell_h // 2

            tid = int(getattr(f, "team_id", getattr(f, "tid", 0)))
            col = (60, 160, 230) if tid == 0 else (220, 80, 80)
            pygame.draw.circle(surf, col, (cx, cy), max(5, min(cell_w, cell_h) // 3))

            # HP microbar inline (underneath)
            mhp = int(getattr(f, "max_hp", max(1, int(getattr(f, "hp", 1)))))
            hp = max(0, min(mhp, int(getattr(f, "hp", mhp))))
            bar_w = max(18, int(cell_w * 0.9))
            bar_h = 6
            bx = cx - bar_w // 2
            by = cy + max(10, (cell_h // 2) - 6)
            pygame.draw.rect(surf, (25, 27, 32), (bx, by, bar_w, bar_h), border_radius=3)
            fill = int((hp / max(1, mhp)) * bar_w)
            pygame.draw.rect(surf, (60, 200, 90), (bx, by, fill, bar_h), border_radius=3)

            # short name scaled to hp bar width
            nm = getattr(f, "name", f"F{getattr(f, 'pid', getattr(f, 'id', '?'))}")
            lbl = _short_name(str(nm))
            text = self.small.render(lbl, True, (230, 230, 236))
            tw = text.get_width()
            if tw > bar_w:
                # scale down via alpha blit; simplest: just clip
                clip = pygame.Rect(0, 0, bar_w, text.get_height())
                surf.blit(text, (bx, by - 16), area=clip)
            else:
                surf.blit(text, (cx - tw // 2, by - 16))

    def _draw_log(self, surf, rect: pygame.Rect):
        pygame.draw.rect(surf, (18, 18, 22), rect, border_radius=8)
        pygame.draw.rect(surf, (55, 58, 65), rect, width=2, border_radius=8)
        if not self.combat:
            return
        events = self.combat.events[-SHORT_LOG_ROWS:]
        y = rect.y + 8
        for e in events:
            s = self._format_event_line(e)
            txt = self.small.render(s, True, (220, 220, 230))
            surf.blit(txt, (rect.x + 8, y))
            y += 20

    def _format_event_line(self, e: Dict[str, Any]) -> str:
        t = e.get("type")
        if t == "round_start":
            return f"— Round {e.get('round', '?')} —"
        if t == "turn_start":
            return f"{e.get('actor', '?')} starts turn"
        if t == "move_step":
            x, y = e.get("to", (0, 0))
            return f"{e.get('actor', '?')} moved to ({x},{y})"
        if t == "attack":
            tags = []
            if e.get("critical"): tags.append("CRIT")
            if e.get("opportunity"): tags.append("OA")
            if e.get("ranged"): tags.append("RNG")
            if e.get("advantage"): tags.append("ADV")
            if e.get("disadvantage"): tags.append("DIS")
            tag = f" ({'/'.join(tags)})" if tags else ""
            if e.get("reason") == "out_of_range":
                return f"{e.get('actor','?')} shot at {e.get('target','?')} (out of range){tag}"
            return f"{e.get('actor','?')} hit {e.get('target','?')}{tag}" if e.get("hit") else f"{e.get('actor','?')} missed {e.get('target','?')}{tag}"
        if t == "spell_attack":
            return f"{e.get('actor','?')} cast at {e.get('target','?')} — {'HIT' if e.get('hit') else 'MISS'}"
        if t == "spell_aoe":
            return f"{e.get('source','?')} casts line AoE over {len(e.get('cells', []))} tiles"
        if t == "save":
            ok = "PASS" if e.get("success") else "FAIL"
            return f"{e.get('target','?')} {e.get('ability','?')} save vs {e.get('dc','?')}: {ok}"
        if t == "condition_applied":
            return f"{e.get('target','?')} is {e.get('condition','?')} ({e.get('duration',1)}r)"
        if t == "condition_ended":
            return f"{e.get('target','?')}: {e.get('condition','?')} ended"
        if t == "heal":
            return f"{e.get('source','?')} healed {e.get('target','?')} {e.get('amount',0)}"
        if t == "damage":
            return f"{e.get('actor','?')} dealt {e.get('amount',0)} to {e.get('target','?')}"
        if t == "down":
            return f"{e.get('name','?')} is down!"
        if t == "concentration_broken":
            return f"{e.get('target','?')}'s concentration broke!"
        if t == "end":
            w = e.get("winner")
            if w in (0, 1):
                side = "Home" if w == 0 else "Away"
                return f"— Match over. Winner: {side} —"
            return "— Match over. Draw —"
        return str(e)

    def _draw_controls(self, surf, rect: pygame.Rect):
        pygame.draw.rect(surf, (18, 18, 22), rect, border_radius=8)
        pygame.draw.rect(surf, (55, 58, 65), rect, width=2, border_radius=8)
        tips = [
            "[Space] Play/Pause",
            "[N] Next Turn",
            "[R] Next Round",
            "[Esc/Backspace] Back",
        ]
        x = rect.x + 10
        y = rect.y + 14
        for s in tips:
            surf.blit(self.small.render(s, True, (220, 220, 230)), (x, y))
            y += 18

    # ---------- stepping helpers ----------
    def _step_turns(self, n: int):
        if not self.combat or self.combat.winner is not None:
            return
        for _ in range(max(1, int(n))):
            if self.combat.winner is not None:
                break
            self.combat.take_turn()
