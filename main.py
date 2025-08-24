# main.py — Menus + Exhibition + Scheduled Match + Schedule/Table
# Roster: sorting, paging, compare popup, scouting card
import os, json, time, pygame
if not hasattr(pygame, "DIRECTION_LTR"): pygame.DIRECTION_LTR = 0
if not hasattr(pygame, "DIRECTION_RTL"): pygame.DIRECTION_RTL = 1
import pygame_gui

from engine import TBCombat, Team, fighter_from_dict, layout_teams_tiles
from core.save_system import Career, save_career, load_career, simulate_week_ai

HERE = os.path.dirname(__file__)
SAVES_DIR = os.path.join(HERE, "saves")
SETTINGS_PATH = os.path.join(HERE, "settings.json")

DEFAULT_SETTINGS = {"resolution": [1280, 720], "volume_master": 0.8}

BG = (16, 18, 24)
GRID = (28, 30, 36)
WHITE = (235, 238, 240)
SIDEBAR_W = 360
FPS = 60
GRID_W = 18
GRID_H = 12

def draw_bg_grid(screen):
    w, h = screen.get_size()
    for x in range(0, w, 40): pygame.draw.line(screen, GRID, (x, 0), (x, h))
    for y in range(0, h, 40): pygame.draw.line(screen, GRID, (0, y), (w, y))

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def save_json(path, obj):
    try:
        with open(path, "w", encoding="utf-8") as f: json.dump(obj, f, indent=2)
    except Exception: pass

def ensure_dir(p): os.makedirs(p, exist_ok=True)

# -------- Settings --------
class SettingsWindow(pygame_gui.elements.UIWindow):
    def __init__(self, manager, rect, app):
        super().__init__(rect=rect, manager=manager, window_display_title="Settings")
        self.app = app
        pygame_gui.elements.UILabel(pygame.Rect(16, 16, 140, 24), "Master Volume", manager, container=self)
        self.vol_slider = pygame_gui.elements.UIHorizontalSlider(
            pygame.Rect(16, 44, 260, 24),
            start_value=int(self.app.settings.get("volume_master", 0.8)*100),
            value_range=(0, 100), manager=manager, container=self
        )
        pygame_gui.elements.UILabel(pygame.Rect(16, 80, 140, 24), "Resolution", manager, container=self)
        res_choices = [(1280,720),(1366,768),(1600,900),(1920,1080)]
        opts = [f"{w} x {h}" for (w,h) in res_choices]
        cur = tuple(self.app.settings.get("resolution", [1280,720]))
        start = f"{cur[0]} x {cur[1]}" if cur in res_choices else opts[0]
        self.res_dd = pygame_gui.elements.UIDropDownMenu(opts, start, pygame.Rect(16, 108, 200, 28), manager, self)
        self.btn_apply = pygame_gui.elements.UIButton(pygame.Rect(16, 150, 100, 32), "Apply", manager, self)
        self.btn_close = pygame_gui.elements.UIButton(pygame.Rect(140, 150, 100, 32), "Close", manager, self)
    def process_event(self, event):
        handled = super().process_event(event)
        if handled: return handled
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_apply:
                vol = max(0, min(100, int(self.vol_slider.get_current_value()))) / 100.0
                self.app.settings["volume_master"] = vol
                try: pygame.mixer.music.set_volume(vol)
                except Exception: pass
                w, h = [int(s.strip()) for s in self.res_dd.selected_option.split("x")]
                if tuple(self.app.settings.get("resolution", [0,0])) != (w, h):
                    self.app.settings["resolution"] = [w, h]
                    self.app.apply_resolution((w, h))
                save_json(SETTINGS_PATH, self.app.settings)
            elif event.ui_element == self.btn_close:
                self.kill()
        return False

# -------- Team Select --------
class TeamSelectState:
    def __init__(self, app):
        self.app = app
        self.manager = pygame_gui.UIManager(self.app.screen.get_size())
        self.title = pygame.font.SysFont("consolas", 34).render("Select Your Team", True, WHITE)
        self.btn_back = pygame_gui.elements.UIButton(pygame.Rect((16, 16), (110, 36)), "Back", self.manager)
        self.btn_manage = pygame_gui.elements.UIButton(pygame.Rect((140, 16), (190, 36)), "Manage This Team", self.manager)
        items, self.tid_by_label = [], {}
        if self.app.career:
            for tid in self.app.career.team_ids:
                t = self.app.career.teams[tid]
                lab = f"{t['name']}  (TID {tid})"
                items.append(lab); self.tid_by_label[lab] = tid
        r = pygame.Rect(40, 80, self.app.screen.get_width() - 80, self.app.screen.get_height() - 140)
        self.sel = pygame_gui.elements.UISelectionList(relative_rect=r, item_list=items, manager=self.manager)
    def handle(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_back: self.app.set_state(MenuState(self.app))
            elif event.ui_element == self.btn_manage:
                s = self.sel.get_single_selection()
                if s: self.app.chosen_tid = self.tid_by_label[s]; self.app.set_state(ManagerMenuState(self.app))
        self.manager.process_events(event)
    def update(self, dt): self.manager.update(dt)
    def draw(self, screen):
        screen.fill(BG); draw_bg_grid(screen)
        screen.blit(self.title, (screen.get_width()//2 - self.title.get_width()//2, 22))
        self.manager.draw_ui(screen)

# -------- Roster (sorting, paging, compare, scouting card) --------
class RosterState:
    TOP_MARGIN   = 72    # space for the big title
    TOOLBAR_H    = 40
    PAGE_SIZE    = 10
    SORT_KEYS    = ["OVR","Name","Class","Age","Value","Wage","STR","DEX","CON"]

    def __init__(self, app):
        self.app = app
        self.manager = pygame_gui.UIManager(self.app.screen.get_size())
        self.title_surf = pygame.font.SysFont("consolas", 32).render("Roster", True, WHITE)

        # Toolbar controls (appear under the title)
        self.btn_back   = pygame_gui.elements.UIButton(pygame.Rect(0,0,110,32), "Back", self.manager)
        pygame_gui.elements.UILabel(pygame.Rect(0,0,50,28), "Sort:", self.manager)
        self.dd_sort    = pygame_gui.elements.UIDropDownMenu(self.SORT_KEYS, "OVR", pygame.Rect(0,0,130,28), self.manager)
        self.btn_dir    = pygame_gui.elements.UIButton(pygame.Rect(0,0,120,28), "Descending", self.manager)
        self.btn_prev   = pygame_gui.elements.UIButton(pygame.Rect(0,0,90,28), "Prev", self.manager)
        self.lbl_page   = pygame_gui.elements.UILabel(pygame.Rect(0,0,80,28), "1/1", self.manager)
        self.btn_next   = pygame_gui.elements.UIButton(pygame.Rect(0,0,90,28), "Next", self.manager)
        self.btn_compare= pygame_gui.elements.UIButton(pygame.Rect(0,0,160,28), "Compare (select 2)", self.manager)

        # Lists/card (sit below the toolbar)
        w, h = self.app.screen.get_size()
        list_rect, card_rect = self._calc_boxes(w, h)
        self.list_fighters = pygame_gui.elements.UISelectionList(list_rect, [], self.manager, allow_multi_select=True)
        self.card_box      = pygame_gui.elements.UITextBox("Select a fighter to view details.", card_rect, manager=self.manager)

        # Data state
        self._fighters = []
        self._sorted = []
        self._page = 0
        self._desc = True
        self._label_to_f = {}
        self._last_card_key = None

        self._layout_toolbar(w)  # position buttons
        self._load_team()
        self._apply_sort_and_page()

    # ---------- layout helpers ----------
    def _layout_toolbar(self, w):
        """Place toolbar controls on one row under the title."""
        x = 16; y = self.TOP_MARGIN
        def place(el, w_el): 
            nonlocal x
            el.set_relative_position((x, y)); el.set_dimensions((w_el, el.relative_rect.h))
            x += w_el + 10

        place(self.btn_back, 110)
        x += 10  # small spacer
        # "Sort:" label is next in UI elements order; find it by text
        # Safer: we’ll just place by querying manager's UI elements in creation order
        # but since we created label right before dd_sort, we can rely on dd_sort’s x to align following items.

        # Reposition the label directly via relative_rect adjust:
        # (Find the label by scanning elements in the container)
        for el in self.manager.ui_group.elements:
            if isinstance(el, pygame_gui.elements.UILabel) and el.text == "Sort:":
                el.set_relative_position((x, y+2)); el.set_dimensions((46, 28))
                break
        x += 46 + 10

        place(self.dd_sort, 130)
        place(self.btn_dir, 120)
        place(self.btn_prev, 90)
        place(self.lbl_page, 80)
        place(self.btn_next, 90)
        place(self.btn_compare, 180)

    def _calc_boxes(self, w, h):
        list_y = self.TOP_MARGIN + self.TOOLBAR_H + 8
        list_h = max(140, h - list_y - 16)  # leave bottom margin
        left_w = w//2 - 24
        right_x = w//2 + 8
        right_w = w - right_x - 16
        list_rect = pygame.Rect(16, list_y, left_w, list_h)
        card_rect = pygame.Rect(right_x, list_y, right_w, list_h)
        return list_rect, card_rect

    # ---------- data & sorting ----------
    def _load_team(self):
        self._fighters = []
        c = self.app.career
        if c and self.app.chosen_tid:
            t = c.get_team(self.app.chosen_tid)
            self._fighters = list(t["fighters"])

    def _sort_key_fn(self, f):
        k = self.dd_sort.selected_option
        return {
            "OVR": f.get("ovr",0), "Name": f.get("name",""), "Class": f.get("class",""),
            "Age": f.get("age",0), "Value": f.get("value",0), "Wage": f.get("wage",0),
            "STR": f.get("str",0), "DEX": f.get("dex",0), "CON": f.get("con",0)
        }.get(k, 0)

    def _apply_sort_and_page(self):
        self._sorted = sorted(self._fighters, key=self._sort_key_fn, reverse=self._desc)
        total = max(1, (len(self._sorted) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self._page = max(0, min(self._page, total-1))
        self.lbl_page.set_text(f"{self._page+1}/{total}")
        start = self._page * self.PAGE_SIZE; end = start + self.PAGE_SIZE
        subset = self._sorted[start:end]
        items = []; self._label_to_f = {}
        for f in subset:
            lab = f"{f.get('pid','')} — {f.get('name','')}  ({f.get('class','?')}, OVR {f.get('ovr',0)})"
            items.append(lab); self._label_to_f[lab] = f
        self.list_fighters.set_item_list(items)

    # ---------- UI interactions ----------
    def _update_card_from_selection(self):
        sels = self.list_fighters.get_multi_selection() or []
        focus = sels[-1] if sels else None
        if focus == self._last_card_key: return
        self._last_card_key = focus
        if not focus or focus not in self._label_to_f:
            self.card_box.set_text("Select a fighter to view details."); return
        f = self._label_to_f[focus]
        val = f.get("value",0); wage=f.get("wage",0); w=f.get("weapon",{})
        html = []
        html.append(f"<b><font size=4>{f.get('name','')}</font></b><br>")
        html.append(f"<b>Class:</b> {f.get('class','?')}  &nbsp; <b>OVR:</b> {f.get('ovr',0)}<br>")
        html.append(f"<b>Age:</b> {f.get('age',0)} &nbsp; <b>Potential:</b> {f.get('potential',0)}<br>")
        html.append(f"<b>Value:</b> {val:,} &nbsp; <b>Wage:</b> {wage:,}/wk<br><br>")
        html.append("<u><b>Abilities</b></u><br>")
        html.append(f"STR {f.get('str',0)}  |  DEX {f.get('dex',0)}  |  CON {f.get('con',0)}<br>")
        html.append(f"INT {f.get('int',0)}  |  WIS {f.get('wis',0)}  |  CHA {f.get('cha',0)}<br><br>")
        html.append("<u><b>Combat</b></u><br>")
        html.append(f"HP {f.get('hp',0)}  |  AC {f.get('ac',0)}  |  SPD {f.get('speed',0)}<br>")
        html.append(f"Weapon: {w.get('name','?')} ({w.get('damage','1d6')})<br>")
        self.card_box.set_text("".join(html))

    def _compare_popup(self):
        try:
            sels = self.list_fighters.get_multi_selection() or []
            if len(sels) != 2:
                pygame_gui.windows.UIMessageWindow(pygame.Rect(0,0,420,180), "Select exactly two fighters to compare.", self.manager, "Compare")
                return
            if sels[0] not in self._label_to_f or sels[1] not in self._label_to_f:
                pygame_gui.windows.UIMessageWindow(pygame.Rect(0,0,420,180), "Please reselect both fighters and try again.", self.manager, "Compare")
                return
            f1 = self._label_to_f[sels[0]]; f2 = self._label_to_f[sels[1]]
            def row(k,a,b): return f"<tr><td><b>{k}</b></td><td>{a}</td><td>{b}</td></tr>"
            w1=f1.get("weapon",{}); w2=f2.get("weapon",{})
            html = "<b>Compare Fighters</b><br><br><table border=0 cellpadding=4>"
            html += row("Name", f1.get("name",""), f2.get("name",""))
            html += row("Class", f1.get("class",""), f2.get("class",""))
            html += row("OVR", f1.get("ovr",0), f2.get("ovr",0))
            html += row("Age", f1.get("age",0), f2.get("age",0))
            html += row("Potential", f1.get("potential",0), f2.get("potential",0))
            html += row("Value", f"{f1.get('value',0):,}", f"{f2.get('value',0):,}")
            html += row("Wage", f"{f1.get('wage',0):,}", f"{f2.get('wage',0):,}")
            for k in ["str","dex","con","int","wis","cha"]:
                html += row(k.upper(), f1.get(k,0), f2.get(k,0))
            html += row("Weapon", f"{w1.get('name','?')} ({w1.get('damage','1d6')})", f"{w2.get('name','?')} ({w2.get('damage','1d6')})")
            html += row("HP/AC/SPD", f"{f1.get('hp',0)}/{f1.get('ac',0)}/{f1.get('speed',0)}", f"{f2.get('hp',0)}/{f2.get('ac',0)}/{f2.get('speed',0)}")
            html += "</table>"
            pygame_gui.windows.UIMessageWindow(pygame.Rect(0,0,560,380), html, self.manager, "Compare")
        except Exception as e:
            pygame_gui.windows.UIMessageWindow(pygame.Rect(0,0,520,220), f"Compare failed: {e}", self.manager, "Error")

    # ---------- event loop ----------
    def handle(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.manager.set_window_resolution(event.size)
            w, h = event.size
            list_rect, card_rect = self._calc_boxes(w, h)
            self.list_fighters.set_relative_rect(list_rect)
            self.card_box.set_relative_rect(card_rect)
            self._layout_toolbar(w)

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_back:
                self.app.set_state(ManagerMenuState(self.app))
            elif event.ui_element == self.btn_prev:
                if self._page > 0: self._page -= 1; self._apply_sort_and_page()
            elif event.ui_element == self.btn_next:
                total = max(1, (len(self._fighters) + self.PAGE_SIZE - 1)//self.PAGE_SIZE)
                if self._page < total-1: self._page += 1; self._apply_sort_and_page()
            elif event.ui_element == self.btn_dir:
                self._desc = not self._desc
                self.btn_dir.set_text("Descending" if self._desc else "Ascending")
                self._apply_sort_and_page()
            elif event.ui_element == self.btn_compare:
                self._compare_popup()

        if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED and event.ui_element == self.dd_sort:
            self._apply_sort_and_page()

        if event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION and event.ui_element == self.list_fighters:
            self._update_card_from_selection()
        if event.type == pygame_gui.UI_SELECTION_LIST_DROPPED_SELECTION and event.ui_element == self.list_fighters:
            self._update_card_from_selection()

        self.manager.process_events(event)

    def update(self, dt):
        self.manager.update(dt)
        self._update_card_from_selection()

    def draw(self, screen):
        screen.fill(BG); draw_bg_grid(screen)
        # Title at the very top
        screen.blit(self.title_surf, (screen.get_width()//2 - self.title_surf.get_width()//2, 18))
        self.manager.draw_ui(screen)

# -------- Schedule (browse weeks) --------
class ScheduleState:
    def __init__(self, app):
        self.app = app
        self.manager = pygame_gui.UIManager(self.app.screen.get_size())
        self.title = pygame.font.SysFont("consolas", 32).render("Schedule — Browse Weeks", True, WHITE)
        self.btn_back  = pygame_gui.elements.UIButton(pygame.Rect((16, 16), (110, 36)), "Back", self.manager)
        self.btn_prev  = pygame_gui.elements.UIButton(pygame.Rect((140, 16), (120, 36)), "Prev Week", self.manager)
        self.btn_curr  = pygame_gui.elements.UIButton(pygame.Rect((270, 16), (160, 36)), "Current Week", self.manager)
        self.btn_next  = pygame_gui.elements.UIButton(pygame.Rect((440, 16), (120, 36)), "Next Week", self.manager)
        c = self.app.career; c.ensure_schedule()
        self.view_week = c.date["week"]; self.total_weeks = max(1, int(c.season_meta.get("total_weeks", 38)))
        self.text = pygame_gui.elements.UITextBox("Loading…", pygame.Rect(16, 70, self.app.screen.get_width()-32, self.app.screen.get_height()-86), manager=self.manager)
        self._rebuild()
    def _rebuild(self):
        c = self.app.career
        season = c.date["season"]; week = max(1, min(self.view_week, self.total_weeks))
        wk_key = f"S{season}W{week}"; fixtures = c.fixtures.get(wk_key, []); my_tid = self.app.chosen_tid
        lines = [f"Season {season}, Week {week}/{self.total_weeks} • Fixtures", "------------------------------------------------------------"]
        if not fixtures: lines.append("No fixtures.")
        else:
            for fx in fixtures:
                tH = c.get_team(fx["home"])["name"]; tA = c.get_team(fx["away"])["name"]; tag = "  ← (YOU)" if my_tid in (fx["home"], fx["away"]) else ""
                res = fx["result"]
                if res is None: lines.append(f"{tH} vs {tA}{tag} — Not played")
                else:
                    hh, aa = res.get("home_hp",0), res.get("away_hp",0); outcome = res.get("winner","draw")
                    if outcome == "home": res_str = f"{tH} win {hh}-{aa}"
                    elif outcome == "away": res_str = f"{tA} win {aa}-{hh}"
                    else: res_str = f"Draw {hh}-{aa}"
                    lines.append(f"{tH} vs {tA}{tag} — {res_str}")
        self.text.set_text("<br>".join(lines).replace(" ", "&nbsp;"))
    def handle(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.manager.set_window_resolution(event.size)
            self.text.set_relative_rect(pygame.Rect(16, 70, self.app.screen.get_width()-32, self.app.screen.get_height()-86))
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_back: self.app.set_state(ManagerMenuState(self.app))
            elif event.ui_element == self.btn_prev:
                if self.view_week > 1: self.view_week -= 1; self._rebuild()
            elif event.ui_element == self.btn_curr:
                self.view_week = self.app.career.date["week"]; self._rebuild()
            elif event.ui_element == self.btn_next:
                if self.view_week < self.total_weeks: self.view_week += 1; self._rebuild()
        self.manager.process_events(event)
    def update(self, dt): self.manager.update(dt)
    def draw(self, screen):
        screen.fill(BG); draw_bg_grid(screen)
        screen.blit(self.title, (screen.get_width()//2 - self.title.get_width()//2, 18))
        self.manager.draw_ui(screen)

# -------- Table (standings) --------
class TableState:
    def __init__(self, app):
        self.app = app
        self.manager = pygame_gui.UIManager(self.app.screen.get_size())
        self.title = pygame.font.SysFont("consolas", 32).render("League Table", True, WHITE)
        self.btn_back = pygame_gui.elements.UIButton(pygame.Rect((16, 16), (110, 36)), "Back", self.manager)
        c = self.app.career
        def row_for(tid):
            r = c.table.get(tid, {"P":0,"W":0,"D":0,"L":0,"PF":0,"PA":0,"PTS":0}); gd = r["PF"] - r["PA"]; return r, gd
        sorted_tids = sorted(
            c.team_ids,
            key=lambda tid: (c.table.get(tid,{"PTS":0})["PTS"], c.table.get(tid,{"PF":0})["PF"] - c.table.get(tid,{"PA":0})["PA"], c.table.get(tid,{"PF":0})["PF"], -ord(c.teams[tid]["name"][0])),
            reverse=True
        )
        lines = [" Pos  Team                           P   W   D   L   PF   PA   GD   PTS", " ----------------------------------------------------------------------"]
        pos = 1
        for tid in sorted_tids:
            name = c.teams[tid]["name"]; r, gd = row_for(tid); mark = " ← YOU" if self.app.chosen_tid == tid else ""
            lines.append(f" {pos:>2}.  {name:<28}  {r['P']:>2}  {r['W']:>2}  {r['D']:>2}  {r['L']:>2}  {r['PF']:>3}  {r['PA']:>3}  {gd:>3}  {r['PTS']:>3}{mark}")
            pos += 1
        self.text = pygame_gui.elements.UITextBox("<br>".join(lines).replace(" ", "&nbsp;"), pygame.Rect(16, 70, self.app.screen.get_width()-32, self.app.screen.get_height()-86), manager=self.manager)
    def handle(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.btn_back:
            self.app.set_state(ManagerMenuState(self.app))
        self.manager.process_events(event)
    def update(self, dt): self.manager.update(dt)
    def draw(self, screen):
        screen.fill(BG); draw_bg_grid(screen)
        screen.blit(self.title, (screen.get_width()//2 - self.title.get_width()//2, 18)); self.manager.draw_ui(screen)

# -------- Main Menu --------
class MenuState:
    def __init__(self, app):
        self.app = app
        self.manager = pygame_gui.UIManager(self.app.screen.get_size())
        self.title = pygame.font.SysFont("consolas", 44).render("D20 Fight Club — Manager", True, WHITE)
        self.btn_new  = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 360, 48), "New Game",   self.manager)
        self.btn_load = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 360, 48), "Load Game",  self.manager)
        self.btn_play = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 360, 48), "Play Match (Exhibition)", self.manager)
        self.btn_sett = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 360, 48), "Settings",   self.manager)
        self.btn_quit = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 360, 48), "Quit",       self.manager)
        self.file_dialog = None; self._layout()
    def _layout(self):
        w, _ = self.app.screen.get_size(); cx = w // 2; y0 = 240; bw, bh, gap = 360, 48, 14
        for idx, btn in enumerate([self.btn_new, self.btn_load, self.btn_play, self.btn_sett, self.btn_quit]):
            btn.set_dimensions((bw, bh)); btn.set_relative_position((cx - bw//2, y0 + idx*(bh+gap)))
    def handle(self, event):
        if event.type == pygame.VIDEORESIZE: self.manager.set_window_resolution(event.size); self._layout()
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_new:
                ensure_dir(SAVES_DIR)
                career = Career.create_random_league(20, 4, seed=None); career.ensure_schedule()
                path = os.path.join(SAVES_DIR, f"career_{int(time.time())}.json")
                save_career(path, career); self.app.career = career; self.app.current_save_path = path; self.app.chosen_tid = None
                self.app.set_state(TeamSelectState(self.app))
            elif event.ui_element == self.btn_load: self.open_load_dialog()
            elif event.ui_element == self.btn_play:
                if not self.app.career:
                    self.app.career = Career.create_random_league(20, 4, seed=None); self.app.career.ensure_schedule()
                self.app.set_state(PlayMatchPickerState(self.app))
            elif event.ui_element == self.btn_sett: SettingsWindow(self.manager, pygame.Rect(0, 0, 320, 220), self.app)
            elif event.ui_element == self.btn_quit: self.app.running = False
        if event.type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED and self.file_dialog is not None and event.ui_element == self.file_dialog:
            path = event.text; self.file_dialog = None
            try:
                career = load_career(path); career.ensure_schedule()
                self.app.career = career; self.app.current_save_path = path; self.app.chosen_tid = None
            except Exception: pass
        self.manager.process_events(event)
    def open_load_dialog(self):
        ensure_dir(SAVES_DIR)
        self.file_dialog = pygame_gui.windows.UIFileDialog(pygame.Rect(140, 80, 720, 480), self.manager, "Load Career", initial_file_path=SAVES_DIR, allow_existing_files_only=True)
    def update(self, dt): self.manager.update(dt)
    def draw(self, screen):
        screen.fill(BG); draw_bg_grid(screen)
        screen.blit(self.title, (screen.get_width()//2 - self.title.get_width()//2, 120))
        hint = "No career loaded"
        if self.app.career: d = self.app.career.date; hint = f"Season {d['season']}, Week {d['week']}"
        small = pygame.font.SysFont("consolas", 22).render(hint, True, WHITE)
        screen.blit(small, (screen.get_width()//2 - small.get_width()//2, 190))
        self.manager.draw_ui(screen)

# -------- Playing Menu --------
class ManagerMenuState:
    def __init__(self, app):
        self.app = app
        self.manager = pygame_gui.UIManager(self.app.screen.get_size())
        self.title = pygame.font.SysFont("consolas", 40).render("Playing Menu", True, WHITE)
        self.msg = None
        self.btn_play  = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 420, 48), "Play Match (Your Fixture)", self.manager)
        self.btn_adv   = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 420, 48), "Advance Week (AI Sims)",     self.manager)
        self.btn_ros   = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 420, 48), "Roster", self.manager)
        self.btn_sched = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 420, 48), "View Schedule (This Week)", self.manager)
        self.btn_table = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 420, 48), "View Table (Standings)", self.manager)
        self.btn_save  = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 420, 48), "Save Game", self.manager)
        self.btn_main  = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 420, 48), "Main Menu", self.manager)
        self.btn_quit  = pygame_gui.elements.UIButton(pygame.Rect(0, 0, 420, 48), "Quit", self.manager)
        self._layout()
    def _layout(self):
        w, _ = self.app.screen.get_size(); cx = w // 2; y0 = 220; bw, bh, gap = 420, 48, 14
        for idx, btn in enumerate([self.btn_play, self.btn_adv, self.btn_ros, self.btn_sched, self.btn_table, self.btn_save, self.btn_main, self.btn_quit]):
            btn.set_dimensions((bw, bh)); btn.set_relative_position((cx - bw//2, y0 + idx*(bh+gap)))
    def _info(self, text: str):
        if self.msg: self.msg.kill()
        self.msg = pygame_gui.windows.UIMessageWindow(pygame.Rect(0, 0, 440, 220), html_message=text, manager=self.manager, window_title="Info")
    def handle(self, event):
        if event.type == pygame.VIDEORESIZE: self.manager.set_window_resolution(event.size); self._layout()
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            c = self.app.career
            if event.ui_element == self.btn_play:
                if not c or not self.app.chosen_tid: self._info("No career or team selected.")
                else:
                    c.ensure_schedule(); fx = c.next_fixture_for_team(self.app.chosen_tid)
                    if not fx: self._info("No fixture scheduled this week.")
                    elif fx["result"] is not None: self._info("Your fixture is already played this week.")
                    else:
                        self.app.scheduled_fixture = (c.date["season"], c.date["week"], fx["home"], fx["away"])
                        self.app.set_state(MatchState(self.app, exhibition=False, scheduled=True))
            elif event.ui_element == self.btn_adv:
                if not c or not self.app.chosen_tid: self._info("No career or team selected.")
                else:
                    c.ensure_schedule(); fx = c.next_fixture_for_team(self.app.chosen_tid)
                    if fx and fx["result"] is None: self._info("Play your match first (use 'Play Match').")
                    else:
                        simulate_week_ai(c); c.tick_week()
                        if self.app.current_save_path: save_career(self.app.current_save_path, c)
                        self._info("Week advanced. Other fixtures simulated.")
            elif event.ui_element == self.btn_ros: self.app.set_state(RosterState(self.app))
            elif event.ui_element == self.btn_sched:
                if not self.app.career: self._info("No career loaded.")
                else: self.app.set_state(ScheduleState(self.app))
            elif event.ui_element == self.btn_table:
                if not self.app.career: self._info("No career loaded.")
                else: self.app.set_state(TableState(self.app))
            elif event.ui_element == self.btn_save:
                if not self.app.current_save_path:
                    ensure_dir(SAVES_DIR); self.app.current_save_path = os.path.join(SAVES_DIR, f"career_{int(time.time())}.json")
                save_career(self.app.current_save_path, self.app.career); self._info("Game saved.")
            elif event.ui_element == self.btn_main: self.app.set_state(MenuState(self.app))
            elif event.ui_element == self.btn_quit: self.app.running = False
        self.manager.process_events(event)
    def update(self, dt): self.manager.update(dt)
    def draw(self, screen):
        screen.fill(BG); draw_bg_grid(screen)
        screen.blit(self.title, (screen.get_width()//2 - self.title.get_width()//2, 120))
        status = "No career loaded"
        if self.app.career:
            d = self.app.career.date
            team_name = "(no team)"
            if self.app.chosen_tid and self.app.chosen_tid in self.app.career.team_ids:
                team_name = self.app.career.get_team(self.app.chosen_tid)["name"]
            status = f"Season {d['season']}, Week {d['week']}    |    Managing: {team_name}"
        small = pygame.font.SysFont("consolas", 22).render(status, True, WHITE)
        screen.blit(small, (screen.get_width()//2 - small.get_width()//2, 180))
        self.manager.draw_ui(screen)

# -------- Exhibition picker --------
class PlayMatchPickerState:
    def __init__(self, app):
        self.app = app
        self.manager = pygame_gui.UIManager(self.app.screen.get_size())
        self.title = pygame.font.SysFont("consolas", 32).render("Exhibition: Pick Two Teams", True, WHITE)
        self.btn_back = pygame_gui.elements.UIButton(pygame.Rect((16, 16), (110, 36)), "Back", self.manager)
        self.btn_play = pygame_gui.elements.UIButton(pygame.Rect((140, 16), (140, 36)), "Start Match", self.manager)
        items, self.tid_by_label = [], {}
        if self.app.career:
            for tid in self.app.career.team_ids:
                t = self.app.career.teams[tid]; lab = f"{t['name']}  (TID {tid})"
                items.append(lab); self.tid_by_label[lab] = tid
        w = self.app.screen.get_width(); h = self.app.screen.get_height()
        self.selA = pygame_gui.elements.UISelectionList(pygame.Rect(40, 80, (w-120)//2, h-140), items, self.manager)
        self.selB = pygame_gui.elements.UISelectionList(pygame.Rect(60 + (w-120)//2, 80, (w-120)//2, h-140), items, self.manager)
    def handle(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_back: self.app.set_state(MenuState(self.app))
            elif event.ui_element == self.btn_play:
                a = self.selA.get_single_selection(); b = self.selB.get_single_selection()
                if a and b and a != b:
                    self.app.exhibition_pair = (self.tid_by_label[a], self.tid_by_label[b]); self.app.set_state(MatchState(self.app, exhibition=True))
        self.manager.process_events(event)
    def update(self, dt): self.manager.update(dt)
    def draw(self, screen):
        screen.fill(BG); draw_bg_grid(screen)
        screen.blit(self.title, (screen.get_width()//2 - self.title.get_width()//2, 22)); self.manager.draw_ui(screen)

# -------- Match --------
class MatchState:
    def __init__(self, app, exhibition: bool = False, scheduled: bool = False):
        self.app = app; self.exhibition = exhibition; self.scheduled = scheduled
        self.manager = pygame_gui.UIManager(self.app.screen.get_size())
        self.font = pygame.font.SysFont("consolas", 18); self.font_big = pygame.font.SysFont("consolas", 28)
        self.btn_back  = pygame_gui.elements.UIButton(pygame.Rect((16, 16), (110, 36)), "Back", self.manager)
        self.btn_reset = pygame_gui.elements.UIButton(pygame.Rect((136, 16), (110, 36)), "Reset", self.manager)
        self.btn_next  = pygame_gui.elements.UIButton(pygame.Rect((256, 16), (130, 36)), "Next Turn", self.manager)
        self.btn_auto  = pygame_gui.elements.UIButton(pygame.Rect((396, 16), (130, 36)), "Auto: OFF", self.manager)
        if not self.app.career:
            self.app.career = Career.create_random_league(20, 4, seed=None); self.app.career.ensure_schedule()
        c = self.app.career; tids = c.team_ids
        if self.exhibition and getattr(self.app, "exhibition_pair", None):
            tidA, tidB = self.app.exhibition_pair; season, week = c.date["season"], c.date["week"]; self._sched_key = (season, week, tidA, tidB)
        elif self.scheduled and getattr(self.app, "scheduled_fixture", None):
            season, week, tidA, tidB = self.app.scheduled_fixture; self._sched_key = (season, week, tidA, tidB)
        else:
            tidA, tidB = tids[0], tids[1]; season, week = c.date["season"], c.date["week"]; self._sched_key = (season, week, tidA, tidB)
        tA, tB = c.get_team(tidA), c.get_team(tidB)
        self.teamA = Team(0, tA["name"], tuple(tA.get("color",[120,180,255]))); self.teamB = Team(1, tB["name"], tuple(tB.get("color",[255,140,140])))
        fighters = [fighter_from_dict({**fd, "team_id":0}) for fd in tA["fighters"]] + [fighter_from_dict({**fd, "team_id":1}) for fd in tB["fighters"]]
        layout_teams_tiles(fighters, GRID_W, GRID_H)
        season, week, tidA, tidB = self._sched_key
        per_match_seed = c.match_seed(season, week, tidA, tidB)
        self.combat = TBCombat(self.teamA, self.teamB, fighters, GRID_W, GRID_H, seed=per_match_seed)
        self.log_lines = []; self.auto_play, self.auto_timer, self._result_recorded = False, 0.0, False
    def _push_log(self, s: str):
        self.log_lines.append(s); self.log_lines = self.log_lines[-22:]
    def handle(self, event):
        if event.type == pygame.VIDEORESIZE: self.manager.set_window_resolution(event.size)
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_back: self.app.set_state(MenuState(self.app) if self.exhibition else ManagerMenuState(self.app))
            elif event.ui_element == self.btn_reset: self.__init__(self.app, exhibition=self.exhibition, scheduled=self.scheduled)
            elif event.ui_element == self.btn_next: self.step_one_turn()
            elif event.ui_element == self.btn_auto:
                self.auto_play = not self.auto_play; self.btn_auto.set_text(f"Auto: {'ON' if self.auto_play else 'OFF'}")
        self.manager.process_events(event)
    def step_one_turn(self):
        if self.combat.winner is not None: return
        before = len(self.combat.events); self.combat.take_turn()
        for e in self.combat.events[before:]:
            k = e.kind; p = e.payload
            if k == "init":           self._push_log(f"Init: {p['name']} = {p['init']}")
            elif k == "round_start":  self._push_log(f"— Round {p['round']} —")
            elif k == "turn_start":   self._push_log(f"{p['actor']}'s turn")
            elif k == "move_step":    self._push_log(f"  moves to {p['to']}")
            elif k == "attack":
                txt = f"  attacks {p['defender']} (d20={p['nat']} vs AC {p['target_ac']})"
                if p.get("critical"): txt += " — CRIT!"
                if not p['hit']:      txt += " — MISS"
                self._push_log(txt)
            elif k == "damage":       self._push_log(f"    → {p['defender']} takes {p['amount']} (HP {p['hp_after']})")
            elif k == "down":         self._push_log(f"    ✖ {p['name']} is down")
            elif k == "end":
                if "winner" in p:     self._push_log(f"Match ends — Winner: {p['winner']} ({p['reason']})")
                else:                 self._push_log(f"Match ends — Draw ({p['reason']})")
            elif k == "round_end":    self._push_log(f"— End Round {p['round']} —")
    def _maybe_record_scheduled(self):
        if not self.scheduled or self._result_recorded or self.combat.winner is None: return
        if self.combat.winner == 0: winner = "home"
        elif self.combat.winner == 1: winner = "away"
        else: winner = "draw"
        home_hp = sum(max(0, f.hp) for f in self.combat.fighters if f.team_id == 0 and f.alive)
        away_hp = sum(max(0, f.hp) for f in self.combat.fighters if f.team_id == 1 and f.alive)
        season, week, tidA, tidB = self._sched_key
        self.app.career.record_result(season, week, tidA, tidB, {"winner": winner, "home_hp": home_hp, "away_hp": away_hp})
        self._result_recorded = True
    def update(self, dt):
        if self.auto_play and self.combat.winner is None:
            self.auto_timer -= dt
            if self.auto_timer <= 0: self.step_one_turn(); self.auto_timer = 0.3
        self._maybe_record_scheduled()
        if self._result_recorded and self.scheduled: self.app.set_state(ManagerMenuState(self.app)); return
        self.manager.update(dt)
    def draw(self, screen):
        screen.fill(BG); draw_bg_grid(screen)
        arena_w = screen.get_width() - SIDEBAR_W; arena_h = screen.get_height()
        cell_w = max(24, arena_w // GRID_W); cell_h = max(24, arena_h // GRID_H)
        for gx in range(GRID_W): pygame.draw.line(screen, (34,36,44), (gx*cell_w, 0), (gx*cell_w, arena_h))
        for gy in range(GRID_H): pygame.draw.line(screen, (34,36,44), (0, gy*cell_h), (arena_w, gy*cell_h))
        for f in self.combat.fighters:
            if not f.alive: continue
            cx = f.tx * cell_w + cell_w//2; cy = f.ty * cell_h + cell_h//2
            col = (120,180,255) if f.team_id == 0 else (255,140,140)
            pygame.draw.circle(screen, col, (cx, cy), min(cell_w, cell_h)//3)
            frac = f.hp / f.max_hp; bw, bh = int(cell_w*0.8), 6; bx, by = cx - bw//2, cy - (cell_h//2) + 4
            pygame.draw.rect(screen, (60,62,70), pygame.Rect(bx, by, bw, bh), border_radius=4)
            c = (90,220,140) if frac>0.5 else (240,210,120) if frac>0.25 else (240,120,120)
            pygame.draw.rect(screen, c, pygame.Rect(bx+1, by+1, int((bw-2)*max(0,min(1,frac))), bh-2), border_radius=4)
            name = self.font.render(f.name, True, WHITE); screen.blit(name, (cx - name.get_width()//2, cy + 6))
        x0 = arena_w; pygame.draw.rect(screen, (20,22,30), pygame.Rect(x0, 0, SIDEBAR_W, screen.get_height()))
        hdr = self.font_big.render("Turn Log", True, WHITE); screen.blit(hdr, (x0 + 16, 16))
        self.manager.draw_ui(screen)

# -------- App --------
class App:
    def __init__(self):
        ensure_dir(SAVES_DIR)
        self.settings = load_json(SETTINGS_PATH, DEFAULT_SETTINGS.copy())
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass
        # this calls the method we’re adding below:
        self.apply_resolution(tuple(self.settings.get("resolution", [1280, 720])))
        pygame.display.set_caption("D20 Fight Club — Manager")
        try:
            pygame.mixer.music.set_volume(float(self.settings.get("volume_master", 0.8)))
        except Exception:
            pass

        self.clock = pygame.time.Clock()
        self.running = True

        self.career = None
        self.current_save_path = None
        self.chosen_tid = None
        self.exhibition_pair = None
        self.scheduled_fixture = None

        self.state = MenuState(self)

    # >>> MAKE SURE THIS METHOD IS **INDENTED INSIDE THE CLASS** <<<
    def apply_resolution(self, res_xy):
        flags = pygame.RESIZABLE | pygame.SCALED
        try:
            # SCALED looks nice on desktop, but fails under headless/dummy driver.
            self.screen = pygame.display.set_mode(res_xy, flags)
        except Exception:
            # Fallback for headless/CI: no SCALED, still resizable.
            self.screen = pygame.display.set_mode(res_xy, pygame.RESIZABLE)

    def set_state(self, state):
        self.state = state

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.state.handle(event)
            self.state.update(dt)
            self.state.draw(self.screen)
            pygame.display.flip()
        pygame.quit()


def main(): App().run()
if __name__ == "__main__": main()
