# ui/state_match_tactics.py
import pygame
from typing import Dict, Any, Tuple, Optional

from engine.team_tactics import (
    RoleSpec, TeamTactics, MatchTactics,
    dump_match_tactics, load_match_tactics
)
from engine.constants import GRID_COLS, GRID_ROWS

# Expected app/state interfaces:
# - app.push_state(state), app.pop_state()
# - states provide enter(context), handle(event), update(dt), draw(screen)

STANCE_OPTIONS = ["aggressive", "balanced", "defensive", "hold"]

class TacticsEditor:
    """
    Minimal keyboard-driven tactics editor:
      - Arrows / WASD: move selection cursor on grid
      - TAB: switch selected team (home/away)
      - Q/E: cycle stance (prev/next)
      - [ / ]: desired_range -/+ (1..24)
      - O: toggle avoid_oa
      - H: toggle one-shot attack_advantage
      - J: toggle one-shot attack_disadvantage
      - K: set/unset anchor at cursor for selected scope (fighter or default)
      - 1..5: choose scope -> 0 = default team, 1..5 = fighter slot index (by lineup list order)
      - ENTER: Start Match (commit lineup + tactics)
      - ESC/BACKSPACE: Back
    """
    def __init__(self, career, fixture, lineup_home, lineup_away):
        self.career = career
        self.fixture = fixture
        self.lineup = {0: lineup_home, 1: lineup_away}  # list of fighter objects
        # selection state
        self.sel_team = 0  # 0 home / 1 away
        self.cursor = [GRID_COLS // 2, GRID_ROWS // 2]
        self.scope = ("default", None)  # ("default", None) or ("pid", pid)
        # load existing or create fresh tactics
        mt = load_match_tactics(fixture)
        if 0 not in mt.by_team: mt.by_team[0] = TeamTactics()
        if 1 not in mt.by_team: mt.by_team[1] = TeamTactics()
        self.mt = mt

        # ensure per-pid RoleSpec containers are ready for lineup pids
        for tid in (0, 1):
            tt = self.mt.by_team[tid]
            for f in self.lineup[tid]:
                pid = getattr(f, "pid", getattr(f, "id", None))
                if pid is None:
                    continue
                tt.roles.setdefault(pid, RoleSpec())

    # ---- helpers to get/set current RoleSpec ----
    def _current_rolespec(self) -> RoleSpec:
        tt = self.mt.by_team[self.sel_team]
        if self.scope[0] == "default":
            return tt.default
        pid = self.scope[1]
        return tt.roles.setdefault(pid, RoleSpec())

    def _apply_anchor_at_cursor(self):
        rs = self._current_rolespec()
        x, y = int(self.cursor[0]), int(self.cursor[1])
        if rs.anchor == (x, y):
            rs.anchor = None
        else:
            rs.anchor = (x, y)

    def _cycle_stance(self, dir: int):
        rs = self._current_rolespec()
        try:
            i = STANCE_OPTIONS.index(rs.stance) if rs.stance in STANCE_OPTIONS else 1
        except Exception:
            i = 1
        i = (i + dir) % len(STANCE_OPTIONS)
        rs.stance = STANCE_OPTIONS[i]

    # ---- keyboard handling ----
    def handle_key(self, key):
        # movement
        if key in (pygame.K_LEFT, pygame.K_a):
            self.cursor[0] = max(0, self.cursor[0] - 1)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.cursor[0] = min(GRID_COLS - 1, self.cursor[0] + 1)
        elif key in (pygame.K_UP, pygame.K_w):
            self.cursor[1] = max(0, self.cursor[1] - 1)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.cursor[1] = min(GRID_ROWS - 1, self.cursor[1] + 1)

        # stance
        elif key == pygame.K_q:
            self._cycle_stance(-1)
        elif key == pygame.K_e:
            self._cycle_stance(1)

        # desired_range
        elif key == pygame.K_LEFTBRACKET:
            rs = self._current_rolespec(); rs.desired_range = max(1, rs.desired_range - 1)
        elif key == pygame.K_RIGHTBRACKET:
            rs = self._current_rolespec(); rs.desired_range = min(24, rs.desired_range + 1)

        # avoid OA
        elif key == pygame.K_o:
            rs = self._current_rolespec(); rs.avoid_oa = not rs.avoid_oa

        # one-shot ADV/DIS
        elif key == pygame.K_h:
            rs = self._current_rolespec(); rs.attack_advantage = not rs.attack_advantage
            if rs.attack_advantage: rs.attack_disadvantage = False
        elif key == pygame.K_j:
            rs = self._current_rolespec(); rs.attack_disadvantage = not rs.attack_disadvantage
            if rs.attack_disadvantage: rs.attack_advantage = False

        # anchor
        elif key == pygame.K_k:
            self._apply_anchor_at_cursor()

        # scope selection: 0 -> default; 1..5 -> nth lineup fighter (by visible order)
        elif key in (pygame.K_0, pygame.K_KP0):
            self.scope = ("default", None)
        elif key in (pygame.K_1, pygame.K_KP1, pygame.K_2, pygame.K_KP2, pygame.K_3, pygame.K_KP3, pygame.K_4, pygame.K_KP4, pygame.K_5, pygame.K_KP5):
            index = {pygame.K_1:0, pygame.K_KP1:0, pygame.K_2:1, pygame.K_KP2:1,
                     pygame.K_3:2, pygame.K_KP3:2, pygame.K_4:3, pygame.K_KP4:3,
                     pygame.K_5:4, pygame.K_KP5:4}[key]
            li = self.lineup[self.sel_team]
            if 0 <= index < len(li):
                pid = getattr(li[index], "pid", getattr(li[index], "id", None))
                if pid is not None:
                    self.scope = ("pid", pid)

        # switch team
        elif key == pygame.K_TAB:
            self.sel_team = 1 - self.sel_team
            # when switching teams, reset scope to default to avoid stale pids
            self.scope = ("default", None)

    def commit_into_fixture(self):
        blob = dump_match_tactics(self.mt)
        # ensure we have a container
        self.fixture.setdefault("tactics", {})
        self.fixture["tactics"].update(blob)

    # ---- drawing overlay ----
    def draw_panel(self, surf, font):
        # very simple panel on the right side
        w, h = surf.get_size()
        panel_w = max(260, w // 4)
        x0 = w - panel_w
        pygame.draw.rect(surf, (18, 18, 22), pygame.Rect(x0, 0, panel_w, h))
        pygame.draw.line(surf, (60, 60, 70), (x0, 0), (x0, h), 2)

        tt = self.mt.by_team[self.sel_team]
        scope_label = "Team Default" if self.scope[0] == "default" else f"Fighter {self.scope[1]}"
        rs = self._current_rolespec()

        lines = [
            f"Team: {'HOME' if self.sel_team == 0 else 'AWAY'}",
            f"Scope: {scope_label}",
            "",
            f"Stance (Q/E): {rs.stance}",
            f"Desired Range ([/]): {rs.desired_range}",
            f"Avoid OA (O): {rs.avoid_oa}",
            f"One-shot ADV (H): {rs.attack_advantage}",
            f"One-shot DIS (J): {rs.attack_disadvantage}",
            f"Anchor (K): {rs.anchor if rs.anchor else 'None'}",
            "",
            "Scope select: 0=Default, 1..5 = lineup slot",
            "Cursor: Arrows/WASD",
            "Switch team: TAB",
            "Start Match: ENTER",
            "Back: ESC/BACKSPACE",
        ]
        y = 12
        for s in lines:
            surf.blit(font.render(s, True, (220, 220, 230)), (x0 + 12, y))
            y += 20

        # cursor crosshair on grid
        gx = int(self.cursor[0]) * (w - panel_w) // GRID_COLS
        gy = int(self.cursor[1]) * h // GRID_ROWS
        pygame.draw.rect(surf, (255, 255, 0), pygame.Rect(gx, gy, 3, 3))

class MatchTacticsState:
    """
    Extends your existing pre-match tactics state:
      - keeps drag+drop lineup code you already wrote,
      - adds a TacticsEditor for keyboard adjustments,
      - writes fixture['tactics'] on start.
    """
    def __init__(self, app):
        self.app = app
        self.context = {}
        self.font = None
        self.editor: Optional[TacticsEditor] = None

        # your existing members, e.g. lineup lists, board rects, were kept generic here.
        self.lineup_home = []
        self.lineup_away = []
        self.fixture = None
        self.career = None

    def enter(self, ctx: Dict[str, Any]):
        # Expect: ctx has career, fixture, precomputed lineup_home/away (list of fighters)
        self.context = dict(ctx or {})
        self.career = self.context.get("career")
        self.fixture = self.context.get("fixture", {})
        self.lineup_home = list(self.context.get("lineup_home", []))
        self.lineup_away = list(self.context.get("lineup_away", []))

        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.SysFont("consolas", 16)

        self.editor = TacticsEditor(self.career, self.fixture, self.lineup_home, self.lineup_away)

        # (Optional) you likely already store preset_lineup here – keep that behavior.
        # This file focuses only on tactics panel wiring.

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.app.pop_state()
                return
            if event.key == pygame.K_RETURN:
                # Commit tactics to fixture and start the match viewer state.
                self.editor.commit_into_fixture()
                # Caller (SeasonHub or TeamSelect flow) should push the MatchState after this.
                # We provide a signal in context so parent knows we’re ready.
                self.context["tactics_committed"] = True
                self.app.pop_state()
                return
            # pass to editor
            if self.editor:
                self.editor.handle_key(event.key)

        # TODO: keep your existing drag & drop mouse handlers here if they live in this file.
        # ...

    def update(self, dt: float):
        pass

    def draw(self, screen):
        screen.fill((12, 12, 16))
        # Your existing board + lineup rendering goes here...
        # e.g., draw grid, fighters, hp bars, names, etc.

        # Overlay the tactics panel + crosshair
        if self.editor and self.font:
            self.editor.draw_panel(screen, self.font)
