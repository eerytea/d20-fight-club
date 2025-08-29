# ui/state_match.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import random
import traceback

# --- pull the turn-based engine / factories ---
try:
    from engine import TBCombat, Team, fighter_from_dict, layout_teams_tiles
except Exception as e:
    TBCombat = None  # type: ignore
    Team = None      # type: ignore
    fighter_from_dict = None  # type: ignore
    layout_teams_tiles = None  # type: ignore
    _ENGINE_IMPORT_ERROR = e
else:
    _ENGINE_IMPORT_ERROR = None

# ----------------- constants & styles -----------------
GRID_COLS = 11
GRID_ROWS = 11

PAD = 16
HEADER_H = 48
FOOTER_H = 60
LOG_MIN_W = 360

BG = (16, 16, 20)
CARD = (42, 44, 52)
BORDER = (24, 24, 28)
TEXT = (235, 235, 240)
TEXT_MID = (215, 215, 220)
GRID_BG = (34, 36, 44)
GRID_LINE = (26, 28, 34)

# ----------------- Button -----------------
@dataclass
class Button:
    rect: pygame.Rect
    text: str
    action: callable
    hover: bool = False
    disabled: bool = False
    def draw(self, surf: pygame.Surface, font: pygame.font.Font):
        bg = (58,60,70) if not self.hover else (76,78,90)
        if self.disabled: bg = (48,48,54)
        pygame.draw.rect(surf, bg, self.rect, border_radius=10)
        pygame.draw.rect(surf, BORDER, self.rect, 2, border_radius=10)
        color = TEXT if not self.disabled else (165,165,170)
        label = font.render(self.text, True, color)
        surf.blit(label, (self.rect.x + 14, self.rect.y + (self.rect.h - label.get_height()) // 2))
    def handle(self, ev: pygame.event.Event):
        if self.disabled: return
        if ev.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self.action()

# ----------------- helpers -----------------
def _team_name(career, tid: int) -> str:
    try:
        if hasattr(career, "team_name") and callable(career.team_name):
            return career.team_name(int(tid))
        for t in getattr(career, "teams", []):
            if int(t.get("tid", -1)) == int(tid):
                return t.get("name", f"Team {tid}")
        # alt structure (dict indexed by id)
        teams = getattr(career, "teams", {})
        if isinstance(teams, dict) and tid in teams:
            return teams[tid].get("name", f"Team {tid}")
    except Exception:
        pass
    return f"Team {tid}"

def _find_fixture_object(career, week: int, home_tid: int, away_tid: int):
    """Return the raw fixture object in career storage if possible."""
    try:
        # format A: fixtures_by_week: List[List[dict]]
        weeks = getattr(career, "fixtures_by_week", None)
        if weeks and 0 <= week-1 < len(weeks):
            for f in weeks[week-1]:
                if isinstance(f, dict):
                    h = int(f.get("home_id", f.get("home_tid", f.get("A", -1))))
                    a = int(f.get("away_id", f.get("away_tid", f.get("B", -1))))
                    if h == home_tid and a == away_tid:
                        return f
        # format B: dict keyed by "S{season}W{week}"
        if hasattr(career, "fixtures") and isinstance(career.fixtures, dict):
            cur_season = getattr(getattr(career, "date", {}), "get", lambda *_: None)("season") if hasattr(career, "date") else None
            if cur_season is None and isinstance(career.date, dict):
                cur_season = career.date.get("season")
            key = f"S{cur_season}W{week}"
            for f in career.fixtures.get(key, []):
                if isinstance(f, dict) and int(f.get("home", f.get("home_id", -1))) == home_tid and int(f.get("away", f.get("away_id", -1))) == away_tid:
                    return f
        # format C: flat list of dicts with 'week'
        for f in getattr(career, "fixtures", []):
            if not isinstance(f, dict): continue
            if int(f.get("week", -1)) != week: continue
            h = int(f.get("home_id", f.get("home_tid", f.get("A", -1))))
            a = int(f.get("away_id", f.get("away_tid", f.get("B", -1))))
            if h == home_tid and a == away_tid:
                return f
    except Exception:
        traceback.print_exc()
    return None

def _record_result_best_effort(career, week: int, home_tid: int, away_tid: int, winner: Optional[str], sh: int, sa: int):
    """Try several career write paths; don’t crash if structure differs."""
    # new-style API
    try:
        if hasattr(career, "record_result") and callable(career.record_result):
            season = career.date["season"] if isinstance(career.date, dict) else getattr(career, "season", 1)
            career.record_result(season, week, home_tid, away_tid, {"winner": winner or "draw", "home_hp": sh, "away_hp": sa})
            return
    except Exception:
        pass
    # legacy inline edit
    raw = _find_fixture_object(career, week, home_tid, away_tid)
    if raw is None: return
    try:
        raw["played"] = True; raw["is_played"] = True
        raw["score_home"] = sh; raw["score_away"] = sa
        if winner:
            raw["winner"] = winner
    except Exception:
        pass

def _fighters_for_team(career, tid: int) -> List[Dict[str,Any]]:
    # career.teams could be list[dict] or dict[int->dict]
    ts = getattr(career, "teams", {})
    if isinstance(ts, dict):
        t = ts.get(tid, {})
        return list(t.get("fighters", []))
    for t in ts or []:
        if int(t.get("tid", -1)) == tid:
            return list(t.get("fighters", []))
    return []

def _top5(lst: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    try:
        return sorted(lst, key=lambda p: int(p.get("ovr", p.get("OVR", 60))), reverse=True)[:5]
    except Exception:
        return lst[:5]

# ----------------- Match State -----------------
class MatchState:
    """
    Turn-based viewer using engine.TBCombat on an 11×11 board.

    Controls (bottom bar):
      • Back  • Play/Pause  • Next Turn  • Next Round

    Right side: scrollable turn log.
    Tactics preset: honors fixture["preset_lineup"] with 'side' ('home'/'away') and list of {pid,cx,cy}.
    """
    def __init__(self, *args, **kwargs):
        if _ENGINE_IMPORT_ERROR is not None:
            raise RuntimeError(f"engine import failed: {_ENGINE_IMPORT_ERROR}")

        # Accept permutations:
        # (app, career, fixture) | (app, fixture, career) | (app, fixture)
        # (app, home_tid, away_tid, career)               | (app, home_tid, away_tid)
        self.app = None
        self.career = None
        self.fixture: Dict[str,Any] = {}
        if len(args) >= 3 and hasattr(args[0], "screen"):
            self.app = args[0]
            if isinstance(args[1], dict) and not isinstance(args[2], dict):
                self.fixture = dict(args[1]); self.career = args[2]
            elif not isinstance(args[1], dict) and isinstance(args[2], dict):
                self.career = args[1]; self.fixture = dict(args[2])
            else:
                self.fixture = dict(args[1])
        elif len(args) >= 4 and hasattr(args[0], "screen"):
            self.app = args[0]; home = int(args[1]); away = int(args[2]); self.career = args[3] if len(args) >= 4 else None
            self.fixture = {"home_id": home, "away_id": away, "week": getattr(self.career, "week", 1)}
        elif len(args) >= 3 and hasattr(args[0], "screen"):
            self.app = args[0]; home = int(args[1]); away = int(args[2])
            self.fixture = {"home_id": home, "away_id": away, "week": 1}
        else:
            raise TypeError("Unsupported MatchState constructor signature")

        if self.career is None:
            self.career = type("MiniCareer", (), {})()
            self.career.teams = []
            self.career.date = {"week": self.fixture.get("week", 1), "season": 1}

        # resolve ids/names/week
        self.home_tid = int(self.fixture.get("home_id", self.fixture.get("home_tid", self.fixture.get("A", 0))))
        self.away_tid = int(self.fixture.get("away_id", self.fixture.get("away_tid", self.fixture.get("B", 0))))
        self.week     = int(self.fixture.get("week", getattr(self.career, "week", 1)))
        self.home_name = _team_name(self.career, self.home_tid)
        self.away_name = _team_name(self.career, self.away_tid)

        # fonts/UI
        self.font  = pygame.font.SysFont(None, 22)
        self.h1    = pygame.font.SysFont(None, 34)
        self.h2    = pygame.font.SysFont(None, 20)

        # layout rects
        self.rect_header: Optional[pygame.Rect] = None
        self.rect_board:  Optional[pygame.Rect] = None
        self.rect_log:    Optional[pygame.Rect] = None
        self.rect_footer: Optional[pygame.Rect] = None
        self.tile = 48

        # buttons
        self.btns: List[Button] = []
        self.running = False
        self.auto_timer = 0.0
        self._auto_interval = 0.35

        # log
        self.lines: List[str] = []
        self._event_idx = 0
        self.log_scroll = 0  # pixels
        self._line_h = self.font.get_height() + 4

        # combat
        self.combat: Optional[TBCombat] = None
        self._result_recorded = False

    # -------------- lifecycle --------------
    def enter(self):
        self._layout()
        self._build_combat()
        self._push_log(f"— Match Start: {self.home_name} vs {self.away_name} (Week {self.week}) —")

    def _layout(self):
        w, h = self.app.screen.get_size()
        # compute tile to fit 11×11 + right log + footer + header
        avail_w = w - PAD*3 - LOG_MIN_W
        avail_h = h - PAD*3 - HEADER_H - FOOTER_H
        self.tile = max(30, min(avail_w // GRID_COLS, avail_h // GRID_ROWS))
        board_w = GRID_COLS * self.tile
        board_h = GRID_ROWS * self.tile

        self.rect_header = pygame.Rect(PAD, PAD, w - PAD*2, HEADER_H)
        by = self.rect_header.bottom + PAD
        self.rect_board = pygame.Rect(PAD + 4, by, board_w, board_h)
        self.rect_log   = pygame.Rect(self.rect_board.right + PAD, by, w - (self.rect_board.right + PAD*2), board_h)
        if self.rect_log.w < LOG_MIN_W:
            # shrink tile if needed
            avail_w = w - PAD*3 - LOG_MIN_W
            self.tile = max(28, min(avail_w // GRID_COLS, avail_h // GRID_ROWS))
            board_w = GRID_COLS * self.tile
            board_h = GRID_ROWS * self.tile
            self.rect_board.size = (board_w, board_h)
            self.rect_log.x = self.rect_board.right + PAD
            self.rect_log.w = LOG_MIN_W

        self.rect_footer = pygame.Rect(PAD, self.rect_board.bottom + PAD, w - PAD*2, FOOTER_H)

        # footer buttons
        self.btns.clear()
        bw, bh, gap = 150, 44, 10
        x = self.rect_footer.x + 10
        def add(label, cb):
            nonlocal x
            r = pygame.Rect(x, self.rect_footer.y + (self.rect_footer.h - bh)//2, bw, bh)
            self.btns.append(Button(r, label, cb)); x += bw + gap
        add("Back", self._back_to_hub)
        add("Play / Pause", self._toggle_play)
        add("Next Turn", self._next_turn)
        add("Next Round", self._next_round)

    def _build_combat(self):
        # gather teams (top-5 each), convert to engine fighters
        home_roster = _top5(_fighters_for_team(self.career, self.home_tid))
        away_roster = _top5(_fighters_for_team(self.career, self.away_tid))

        # convert dict -> engine Fighter
        f_home = [fighter_from_dict({**fd, "team_id": 0}) for fd in home_roster]
        f_away = [fighter_from_dict({**fd, "team_id": 1}) for fd in away_roster]
        fighters = f_home + f_away

        # attach pid/ovr if present so XP award / logs can reference
        pid_map = {}
        for src, dst in zip(home_roster + away_roster, fighters):
            try:
                setattr(dst, "pid", src.get("pid"))
                setattr(dst, "ovr", src.get("ovr", src.get("OVR", 60)))
                pid_map[src.get("pid")] = dst
            except Exception:
                pass

        # default layout: left/right lines
        layout_teams_tiles(fighters, GRID_COLS, GRID_ROWS)

        # apply preset lineup (from tactics), overriding tiles for user's side only
        preset = self.fixture.get("preset_lineup")
        if isinstance(preset, dict):
            try:
                side = preset.get("side", "home")
                slots = preset.get("slots", [])
                tid = self.home_tid if side == "home" else self.away_tid
                for s in slots:
                    pid = s.get("pid"); cx = int(s.get("cx", 0)); cy = int(s.get("cy", 0))
                    f = pid_map.get(pid)
                    if f and ((side == "home" and f.team_id == 0) or (side == "away" and f.team_id == 1)):
                        f.tx, f.ty = cx, cy
            except Exception:
                traceback.print_exc()

        # seed (stable per match if possible)
        try:
            if hasattr(self.career, "match_seed"):
                season = self.career.date["season"]
                seed = self.career.match_seed(season, self.week, self.home_tid, self.away_tid)
            else:
                seed = random.randint(0, 10_000_000)
        except Exception:
            seed = random.randint(0, 10_000_000)

        # teams & combat
        tA = Team(0, self.home_name, (120,180,255))
        tB = Team(1, self.away_name, (255,140,140))
        self.combat = TBCombat(tA, tB, fighters, GRID_COLS, GRID_ROWS, seed=seed)

        # prime initial events in log
        self._flush_events_to_log()

    # -------------- controls --------------
    def _toggle_play(self):
        if self.combat and self.combat.winner is None:
            self.running = not self.running

    def _next_turn(self):
        if not self.combat or self.combat.winner is not None: return
        self._step_one_turn()

    def _next_round(self):
        if not self.combat or self.combat.winner is not None: return
        target_round = self.combat.round
        # advance until round increments (or match ends)
        guard = 0
        while self.combat.winner is None and self.combat.round == target_round and guard < 200:
            self._step_one_turn()
            guard += 1

    def _back_to_hub(self):
        # Pop this state; if the next is tactics, pop it too (return to Season Hub)
        try:
            self.app.pop_state()
            stack = getattr(self.app, "states", getattr(self.app, "stack", None))
            if isinstance(stack, list) and stack:
                st = stack[-1]
                nm = type(st).__name__.lower()
                md = getattr(type(st), "__module__", "").lower()
                if "tactics" in nm or "tactics" in md:
                    self.app.pop_state()
        except Exception:
            pass

    # -------------- event loop --------------
    def handle(self, ev: pygame.event.Event):
        if ev.type == pygame.VIDEORESIZE:
            self._layout()

        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._back_to_hub()
            elif ev.key in (pygame.K_SPACE, pygame.K_p):
                self._toggle_play()
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._next_turn()
            elif ev.key == pygame.K_r:
                self._next_round()

        # log scrolling (mouse wheel over log box)
        if ev.type == pygame.MOUSEWHEEL and self.rect_log and self.rect_log.collidepoint(pygame.mouse.get_pos()):
            content_h = max(0, len(self.lines) * self._line_h)
            vis_h = self.rect_log.h - 24
            max_scroll = max(0, content_h - vis_h)
            self.log_scroll -= ev.y * 22
            self.log_scroll = max(0, min(self.log_scroll, max_scroll))

        for b in self.btns:
            b.handle(ev)

    def update(self, dt: float):
        # auto-play
        if self.running and self.combat and self.combat.winner is None:
            self.auto_timer -= dt
            if self.auto_timer <= 0:
                self._step_one_turn()
                self.auto_timer = self._auto_interval

        # record scheduled result if applicable (best-effort)
        if self.combat and self.combat.winner is not None and not self._result_recorded:
            # compute KO scores (how many enemies are down)
            home_kos = len([f for f in self.combat.fighters if f.team_id == 1 and not f.alive])
            away_kos = len([f for f in self.combat.fighters if f.team_id == 0 and not f.alive])
            if self.combat.winner == 0:
                winner = "home"
            elif self.combat.winner == 1:
                winner = "away"
            else:
                winner = "draw"
            _record_result_best_effort(self.career, self.week, self.home_tid, self.away_tid, winner, home_kos, away_kos)
            self._result_recorded = True

    def draw(self, screen: pygame.Surface):
        screen.fill(BG)

        # header
        pygame.draw.rect(screen, CARD, self.rect_header, border_radius=12)
        pygame.draw.rect(screen, BORDER, self.rect_header, 2, border_radius=12)
        t1 = self.h1.render(f"{self.home_name} vs {self.away_name}", True, TEXT)
        t2 = self.h1.render(f"Week {self.week}", True, TEXT_MID)
        screen.blit(t1, (self.rect_header.x + 12, self.rect_header.y + (self.rect_header.h - t1.get_height())//2))
        screen.blit(t2, (self.rect_header.right - t2.get_width() - 12, self.rect_header.y + (self.rect_header.h - t2.get_height())//2))

        # board frame
        pygame.draw.rect(screen, CARD, self.rect_board, border_radius=10)
        pygame.draw.rect(screen, BORDER, self.rect_board, 2, border_radius=10)

        # grid
        for c in range(GRID_COLS):
            for r in range(GRID_ROWS):
                cell = pygame.Rect(self.rect_board.x + c*self.tile, self.rect_board.y + r*self.tile, self.tile, self.tile)
                pygame.draw.rect(screen, GRID_BG, cell)
                pygame.draw.rect(screen, GRID_LINE, cell, 1)

        # units
        if self.combat:
            for f in self.combat.fighters:
                if not getattr(f, "alive", True): continue
                rect = pygame.Rect(self.rect_board.x + f.tx*self.tile, self.rect_board.y + f.ty*self.tile, self.tile, self.tile)
                col = (120,180,255) if f.team_id == 0 else (255,140,140)
                pygame.draw.rect(screen, col, rect.inflate(-8, -8), border_radius=6)
                pygame.draw.rect(screen, BORDER, rect.inflate(-8, -8), 2, border_radius=6)

                # HP bar
                hp = getattr(f, "hp", 1); mx = getattr(f, "max_hp", max(1, hp))
                frac = max(0.0, min(1.0, hp / mx))
                bw = rect.w - 10; bh = 6; bx = rect.x + 5; by = rect.bottom - bh - 4
                pygame.draw.rect(screen, (60,62,70), pygame.Rect(bx, by, bw, bh), border_radius=3)
                c = (90,220,140) if frac>0.5 else (240,210,120) if frac>0.25 else (240,120,120)
                pygame.draw.rect(screen, c, pygame.Rect(bx+1, by+1, int((bw-2)*frac), bh-2), border_radius=3)

                nm = self.font.render(getattr(f, "name", "F"), True, TEXT)
                screen.blit(nm, (rect.centerx - nm.get_width()//2, rect.y + 4))

        # right log panel
        pygame.draw.rect(screen, CARD, self.rect_log, border_radius=10)
        pygame.draw.rect(screen, BORDER, self.rect_log, 2, border_radius=10)
        title = self.h2.render("Turn Log", True, TEXT_MID)
        screen.blit(title, (self.rect_log.x + 10, self.rect_log.y + 8))
        inner = self.rect_log.inflate(-12, -30)
        inner.y = self.rect_log.y + 26

        # clip & scroll
        clip = screen.get_clip()
        screen.set_clip(inner)
        y = inner.y - int(self.log_scroll)
        for line in self.lines:
            txt = self.font.render(line, True, TEXT)
            screen.blit(txt, (inner.x, y))
            y += self._line_h
        screen.set_clip(clip)

        # scrollbar (simple)
        content_h = max(1, len(self.lines) * self._line_h)
        vis_h = inner.h
        if content_h > vis_h:
            bar_h = max(24, int(vis_h * (vis_h / content_h)))
            max_scroll = content_h - vis_h
            frac = (self.log_scroll / max_scroll) if max_scroll > 0 else 0.0
            bar_y = inner.y + int((vis_h - bar_h) * frac)
            sb_rect = pygame.Rect(self.rect_log.right - 10, bar_y, 6, bar_h)
            pygame.draw.rect(screen, (80,82,90), sb_rect, border_radius=3)

        # footer bar & buttons
        pygame.draw.rect(screen, CARD, self.rect_footer, border_radius=10)
        pygame.draw.rect(screen, BORDER, self.rect_footer, 2, border_radius=10)
        for b in self.btns:
            b.draw(screen, self.font)

        # if finished, hint
        if self.combat and self.combat.winner is not None:
            msg = self.h2.render("Match complete — press Back to return.", True, TEXT_MID)
            screen.blit(msg, (self.rect_footer.right - msg.get_width() - 12, self.rect_footer.y + (self.rect_footer.h - msg.get_height())//2))

    # -------------- internal --------------
    def _push_log(self, s: str):
        self.lines.append(s)

        # autoscroll to bottom if we were near bottom
        inner_h = (self.rect_log.h - 24) if self.rect_log else 0
        content_h = len(self.lines) * self._line_h
        at_bottom = (self.log_scroll + inner_h + 2*self._line_h) >= (content_h - 1)
        if at_bottom:
            self.log_scroll = max(0, content_h - inner_h)

    def _flush_events_to_log(self):
        if not self.combat: return
        evs = self.combat.events
        for i in range(self._event_idx, len(evs)):
            e = evs[i]
            k = getattr(e, "kind", None) or getattr(e, "t", None)
            p = getattr(e, "payload", {})
            if k == "init":          self._push_log(f"Init {p.get('name','?')} = {p.get('init','?')}")
            elif k == "round_start": self._push_log(f"— Round {p.get('round','?')} —")
            elif k == "turn_start":  self._push_log(f"{p.get('actor','?')}'s turn")
            elif k == "move_step":   self._push_log(f"  moves to {p.get('to',(0,0))}")
            elif k == "attack":
                nat = p.get("nat", 0); ac = p.get("target_ac", 0); crit = p.get("critical", False); hit = p.get("hit", False)
                line = f"  attacks {p.get('defender','?')} (d20={nat} vs AC {ac})"
                if crit: line += " — CRIT!"
                if not hit: line += " — MISS"
                self._push_log(line)
            elif k == "damage":
                self._push_log(f"    → {p.get('defender','?')} takes {p.get('amount',0)} (HP {p.get('hp_after',0)})")
            elif k == "down":        self._push_log(f"    ✖ {p.get('name','?')} is down")
            elif k == "round_end":   self._push_log(f"— End Round {p.get('round','?')} —")
            elif k == "end":
                w = p.get("winner"); r = p.get("reason","")
                if w: self._push_log(f"Match ends — Winner: {w} ({r})")
                else: self._push_log(f"Match ends — {r}")
        self._event_idx = len(evs)

    def _step_one_turn(self):
        try:
            before = len(self.combat.events)
            self.combat.take_turn()
            # flush new events
            if len(self.combat.events) > before:
                self._flush_events_to_log()
        except Exception:
            traceback.print_exc()
