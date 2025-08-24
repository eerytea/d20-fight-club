# main.py — D20 Fight Club Manager (clean build)

import os, json, time, pygame, pygame_gui
from typing import List, Dict, Tuple, Optional

# --------- Paths / basic IO ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVES_DIR = os.path.join(BASE_DIR, "saves")
SETTINGS_PATH = os.path.join(BASE_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "volume_master": 0.8,
    "resolution": [1280, 720],
    "last_save": ""
}

def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path: str, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)

# --------- Core / Engine imports ----------
from core.save_system import Career, save_career, load_career, simulate_week_ai
from engine import Team, fighter_from_dict, layout_teams_tiles, TBCombat

# --------- Globals / Colors / Fonts ----------
FPS = 60
WHITE = (230, 230, 230)
LIGHT = (200, 200, 200)
DARK  = (20, 22, 26)
ACCENT = (120, 180, 255)

# ---------- Helpers ----------
def team_average_ovr(team_dict: Dict) -> int:
    fs = team_dict.get("fighters", [])
    if not fs: return 0
    vals = [int(f.get("ovr", 50)) for f in fs]
    return int(round(sum(vals)/max(1, len(vals))))

def make_default_career() -> Optional[Career]:
    """
    Try multiple factory names on Career to build a default league.
    Fall back to bare Career() if factories are missing.
    """
    factories = [
        ("new_default_league", {}),
        ("new_default", {}),
        ("new_league", {"num_teams": 20}),
        ("create_default_league", {}),
        ("build_default_league", {}),
        ("generate_default_league", {}),
    ]
    for name, kwargs in factories:
        meth = getattr(Career, name, None)
        if callable(meth):
            try:
                return meth(**kwargs)
            except TypeError:
                # try calling without kwargs if signature differs
                try:
                    return meth()
                except Exception:
                    pass
            except Exception:
                pass
    # final fallback: maybe Career() auto-initializes a league internally
    try:
        return Career()
    except Exception:
        return None


# =====================================================================================
#                                         STATES
# =====================================================================================

class MenuState:
    """Main Menu: New Game, Load Game, Play Match (exhibition), Settings, Quit"""

    def __init__(self, app):
        self.app = app
        self.ui = pygame_gui.UIManager(app.screen.get_size())
        self._build_ui()

    def _build_ui(self):
        w, h = self.app.screen.get_size()
        cx = w//2
        pad = 12
        btnw, btnh = 300, 48
        y = h//2 - (btnh*5 + pad*4)//2

        self.title = pygame_gui.elements.UILabel(
            pygame.Rect(cx-320, 64, 640, 48),
            "D20 Fight Club — Manager", self.ui
        )

        self.btn_new  = pygame_gui.elements.UIButton(pygame.Rect(cx-btnw//2, y, btnw, btnh), "New Game", self.ui); y+=btnh+pad
        self.btn_load = pygame_gui.elements.UIButton(pygame.Rect(cx-btnw//2, y, btnw, btnh), "Load Game", self.ui); y+=btnh+pad
        self.btn_play = pygame_gui.elements.UIButton(pygame.Rect(cx-btnw//2, y, btnw, btnh), "Play Match (Exhibition)", self.ui); y+=btnh+pad
        self.btn_set  = pygame_gui.elements.UIButton(pygame.Rect(cx-btnw//2, y, btnw, btnh), "Settings", self.ui); y+=btnh+pad
        self.btn_quit = pygame_gui.elements.UIButton(pygame.Rect(cx-btnw//2, y, btnw, btnh), "Quit", self.ui)

    def handle(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.ui.set_window_resolution(event.size); self._build_ui()

        # support old/new pygame_gui event styles
        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED) or \
           (event.type == pygame_gui.UI_BUTTON_PRESSED):
            if event.ui_element == self.btn_new:
    # start a fresh league (robust across save_system versions)
    car = make_default_career()
    if car is None:
        # graceful message instead of crashing
        pygame_gui.windows.UIMessageWindow(
            pygame.Rect(200, 200, 420, 200),
            "Could not create a default league.\n"
            "Please update core/save_system.py to expose a league factory."
            , self.ui
        )
    else:
        self.app.career = car
        self.app.set_state(TeamSelectState(self.app))
            elif event.ui_element == self.btn_load:
                # load dialog
                path = os.path.join(SAVES_DIR, "career.json")
                car = load_career(path)
                if car:
                    self.app.career = car
                    if self.app.chosen_tid:
                        self.app.set_state(ManagerMenuState(self.app))
                    else:
                        self.app.set_state(TeamSelectState(self.app))
            elif event.ui_element == self.btn_play:
                # exhibition: pick two teams then launch match selector
                self.app.exhibition_pair = None
                self.app.set_state(ExhibitionSelectState(self.app))
            elif event.ui_element == self.btn_set:
                self.app.set_state(SettingsState(self.app))
            elif event.ui_element == self.btn_quit:
                self.app.running = False

        self.ui.process_events(event)

    def update(self, dt):
        self.ui.update(dt)

    def draw(self, surf):
        surf.fill(DARK); self.ui.draw_ui(surf)

class SettingsState:
    """Simple settings: resolution + master volume."""
    RES_CHOICES = ["1280x720","1600x900","1920x1080"]

    def __init__(self, app):
        self.app = app
        self.ui = pygame_gui.UIManager(app.screen.get_size())
        self._build_ui()

    def _build_ui(self):
        w, h = self.app.screen.get_size()
        pad = 12
        self.lbl = pygame_gui.elements.UILabel(pygame.Rect(16,16,w-32,32),"Settings", self.ui)

        self.dd_res = pygame_gui.elements.UIDropDownMenu(
            options_list=self.RES_CHOICES, starting_option=f"{self.app.settings['resolution'][0]}x{self.app.settings['resolution'][1]}",
            relative_rect=pygame.Rect(16,64,240,36), manager=self.ui
        )
        self.slider = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(16, 120, 240, 24),
            start_value=float(self.app.settings.get("volume_master",0.8)), value_range=(0.0,1.0), manager=self.ui
        )
        self.lbl_vol = pygame_gui.elements.UILabel(pygame.Rect(270, 116, 160, 32), f"Volume: {int(self.slider.get_current_value()*100)}%", self.ui)

        self.btn_back = pygame_gui.elements.UIButton(pygame.Rect(w-16-160,16,160,36),"Back", self.ui)

    def handle(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.ui.set_window_resolution(event.size); self._build_ui()

        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED) or \
           (event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED):
            if event.ui_element == self.dd_res:
                try:
                    sx, sy = [int(x) for x in event.text.split("x")]
                    self.app.apply_resolution((sx, sy))
                    self.app.settings["resolution"] = [sx, sy]
                    save_json(SETTINGS_PATH, self.app.settings)
                except Exception:
                    pass

        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED) or \
           (event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED):
            if event.ui_element == self.slider:
                v = float(self.slider.get_current_value())
                self.lbl_vol.set_text(f"Volume: {int(v*100)}%")
                self.app.settings["volume_master"] = v
                try: pygame.mixer.music.set_volume(v)
                except Exception: pass
                save_json(SETTINGS_PATH, self.app.settings)

        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED) or \
           (event.type == pygame_gui.UI_BUTTON_PRESSED):
            if event.ui_element == self.btn_back:
                self.app.set_state(MenuState(self.app))

        self.ui.process_events(event)

    def update(self, dt): self.ui.update(dt)
    def draw(self, surf): surf.fill(DARK); self.ui.draw_ui(surf)

class TeamSelectState:
    """Two-pane: left teams with Avg OVR; right roster + fighter details; Manage/Back buttons."""
    def __init__(self, app):
        self.app = app
        self.ui = pygame_gui.UIManager(app.screen.get_size())
        self.selected_tid = None
        self._label_to_tid = {}
        self._current_team = None
        self._current_fighter = None
        self._build_ui()

    def _team_labels(self):
        labels = []
        self._label_to_tid.clear()
        for t in self.app.career.teams:
            avg = team_average_ovr(t)
            label = f"{t['name']} (Avg OVR {avg})"
            self._label_to_tid[label] = t["tid"]
            labels.append(label)
        return labels

    def _build_ui(self):
        w,h = self.app.screen.get_size()
        pad = 12
        left_w = int(w*0.38)
        right_x = pad*2 + left_w
        right_w = w - right_x - pad

        self.lbl_title = pygame_gui.elements.UILabel(pygame.Rect(pad,pad,w-2*pad,32),"Select Your Team",self.ui)

        self.list_teams = pygame_gui.elements.UISelectionList(
            pygame.Rect(pad, 48, left_w, h - 48 - pad),
            self._team_labels(), manager=self.ui
        )

        top_h = int((h - 48 - pad)*0.55)
        self.list_roster = pygame_gui.elements.UISelectionList(
            pygame.Rect(right_x, 48, right_w, top_h), [], manager=self.ui
        )
        self.box_details = pygame_gui.elements.UITextBox(
            pygame.Rect(right_x, 48+top_h+pad, right_w, h - (48+top_h+2*pad)),
            "<b>Fighter Details</b><br>Select a fighter to view.", manager=self.ui
        )

        btn_w, btn_h = 160, 36
        self.btn_manage = pygame_gui.elements.UIButton(pygame.Rect(w - pad - btn_w*2 - 8, pad, btn_w, btn_h),"Manage Team", self.ui)
        self.btn_back   = pygame_gui.elements.UIButton(pygame.Rect(w - pad - btn_w, pad, btn_w, btn_h),"Back", self.ui)

    def _populate_roster(self, team):
        items = []
        for f in team.get("fighters", []):
            items.append(f"{f.get('name','?')} — OVR {int(f.get('ovr',0))}")
        if hasattr(self.list_roster, "set_item_list"):
            self.list_roster.set_item_list(items)

    def _render_fighter_details(self, f: Dict):
        keys = ("class","level","age","ovr","peak_ovr","hp","ac","speed","str","dex","con","int","wis","cha","dev_trait")
        rows = [f"<b>{f.get('name','?')}</b>"]
        for k in keys:
            if k in f: rows.append(f"{k.upper()}: {f[k]}")
        self.box_details.set_text("<br>".join(rows))

    def handle(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.ui.set_window_resolution(event.size); self._build_ui(); return

        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION) or \
           (event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION):
            if event.ui_element == self.list_teams:
                label = event.text
                tid = self._label_to_tid.get(label)
                if tid is not None:
                    for t in self.app.career.teams:
                        if t["tid"] == tid:
                            self._current_team = t
                            self.selected_tid = tid
                            self._populate_roster(t)
                            self._current_fighter = None
                            self.box_details.set_text("<b>Fighter Details</b><br>Select a fighter to view.")
                            break
            elif event.ui_element == self.list_roster and self._current_team:
                label = event.text
                name = label.split(" — ", 1)[0]
                for f in self._current_team.get("fighters", []):
                    if f.get("name") == name:
                        self._current_fighter = f
                        self._render_fighter_details(f)
                        break

        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED) or \
           (event.type == pygame_gui.UI_BUTTON_PRESSED):
            if event.ui_element == self.btn_back:
                self.app.set_state(MenuState(self.app))
            elif event.ui_element == self.btn_manage:
                if self.selected_tid is not None:
                    self.app.chosen_tid = self.selected_tid
                    self.app.set_state(ManagerMenuState(self.app))

        self.ui.process_events(event)

    def update(self, dt): self.ui.update(dt)
    def draw(self, surf): surf.fill(DARK); self.ui.draw_ui(surf)

class ExhibitionSelectState:
    """Pick two teams for a quick exhibition match."""
    def __init__(self, app):
        self.app = app
        self.ui = pygame_gui.UIManager(app.screen.get_size())
        self._label_to_tid = {}
        self._selA = None
        self._selB = None
        self._build_ui()

    def _labels(self):
        labs = []
        self._label_to_tid.clear()
        for t in self.app.career.teams:
            lab = f"{t['name']} (Avg OVR {team_average_ovr(t)})"
            self._label_to_tid[lab] = t["tid"]; labs.append(lab)
        return labs

    def _build_ui(self):
        w,h = self.app.screen.get_size(); pad = 12
        self.lbl = pygame_gui.elements.UILabel(pygame.Rect(pad,pad,w-2*pad,32),"Exhibition — Pick Two Teams", self.ui)
        lw = (w - 3*pad)//2
        self.listA = pygame_gui.elements.UISelectionList(pygame.Rect(pad, 48, lw, h-48-64), self._labels(), self.ui)
        self.listB = pygame_gui.elements.UISelectionList(pygame.Rect(2*pad+lw, 48, lw, h-48-64), self._labels(), self.ui)
        self.btn_back = pygame_gui.elements.UIButton(pygame.Rect(w - pad - 160, h - 48, 160, 36), "Back", self.ui)
        self.btn_go   = pygame_gui.elements.UIButton(pygame.Rect(w - pad - 160*2 - 8, h - 48, 160, 36), "Start Match", self.ui)

    def handle(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.ui.set_window_resolution(event.size); self._build_ui()

        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION) or \
           (event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION):
            if event.ui_element in (self.listA, self.listB):
                lab = event.text; tid = self._label_to_tid.get(lab)
                if event.ui_element == self.listA: self._selA = tid
                else: self._selB = tid

        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED) or \
           (event.type == pygame_gui.UI_BUTTON_PRESSED):
            if event.ui_element == self.btn_back:
                self.app.set_state(MenuState(self.app))
            elif event.ui_element == self.btn_go:
                if self._selA is not None and self._selB is not None and self._selA != self._selB:
                    self.app.exhibition_pair = (self._selA, self._selB)
                    self.app.set_state(MatchState(self.app, scheduled=False))

        self.ui.process_events(event)

    def update(self, dt): self.ui.update(dt)
    def draw(self, surf): surf.fill(DARK); self.ui.draw_ui(surf)

class ManagerMenuState:
    """Post-selection main management menu."""
    def __init__(self, app):
        self.app = app
        self.ui = pygame_gui.UIManager(app.screen.get_size())
        self._build_ui()

    def _build_ui(self):
        w, h = self.app.screen.get_size()
        pad = 12; btnw, btnh = 220, 44
        y = 120
        self.title = pygame_gui.elements.UILabel(pygame.Rect(16,16,w-32,40),"Manager Menu", self.ui)
        self.btn_play  = pygame_gui.elements.UIButton(pygame.Rect(16,y,btnw,btnh),"Play Match", self.ui); y+=btnh+pad
        self.btn_adv   = pygame_gui.elements.UIButton(pygame.Rect(16,y,btnw,btnh),"Advance Week", self.ui); y+=btnh+pad
        self.btn_ros   = pygame_gui.elements.UIButton(pygame.Rect(16,y,btnw,btnh),"Roster", self.ui); y+=btnh+pad
        self.btn_sched = pygame_gui.elements.UIButton(pygame.Rect(16,y,btnw,btnh),"Schedule", self.ui); y+=btnh+pad
        self.btn_table = pygame_gui.elements.UIButton(pygame.Rect(16,y,btnw,btnh),"Table", self.ui); y+=btnh+pad
        self.btn_save  = pygame_gui.elements.UIButton(pygame.Rect(16,y,btnw,btnh),"Save Game", self.ui); y+=btnh+pad
        self.btn_menu  = pygame_gui.elements.UIButton(pygame.Rect(16,y,btnw,btnh),"Main Menu", self.ui); y+=btnh+pad
        self.btn_quit  = pygame_gui.elements.UIButton(pygame.Rect(16,y,btnw,btnh),"Quit", self.ui)

    def handle(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.ui.set_window_resolution(event.size); self._build_ui()

        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED) or \
           (event.type == pygame_gui.UI_BUTTON_PRESSED):
            if event.ui_element == self.btn_play:
                self.app.scheduled_fixture = True
                self.app.set_state(MatchState(self.app, scheduled=True))
            elif event.ui_element == self.btn_adv:
                simulate_week_ai(self.app.career)   # quick-sim AI + update table
                # auto-save after week
                ensure_dir(SAVES_DIR); save_career(os.path.join(SAVES_DIR, "career.json"), self.app.career)
            elif event.ui_element == self.btn_ros:
                self.app.set_state(RosterState(self.app))
            elif event.ui_element == self.btn_sched:
                self.app.set_state(ScheduleState(self.app))
            elif event.ui_element == self.btn_table:
                self.app.set_state(TableState(self.app))
            elif event.ui_element == self.btn_save:
                ensure_dir(SAVES_DIR); save_career(os.path.join(SAVES_DIR,"career.json"), self.app.career)
            elif event.ui_element == self.btn_menu:
                self.app.set_state(MenuState(self.app))
            elif event.ui_element == self.btn_quit:
                self.app.running = False

        self.ui.process_events(event)

    def update(self, dt): self.ui.update(dt)

    def draw(self, surf):
        surf.fill(DARK); self.ui.draw_ui(surf)
        # header info
        try:
            font = pygame.font.SysFont(None, 28)
            t = self.app.career.get_team(self.app.chosen_tid)
            avg = team_average_ovr(t)
            info = f"Week {self.app.career.week+1} / {self.app.career.total_weeks} — {t['name']}   |   Avg OVR {avg}"
            surf.blit(font.render(info, True, WHITE), (260, 24))
        except Exception:
            pass

class RosterState:
    """Simple roster list + details; small toolbar."""
    PAGE_SIZE = 12

    def __init__(self, app):
        self.app = app
        self.manager = pygame_gui.UIManager(app.screen.get_size())
        self._fighters = []
        self._page = 0
        self._desc = True
        self._build_ui()
        self._load_fighters()

    def _calc_boxes(self, w, h):
        left = pygame.Rect(16, 64, 360, h - 64 - 16)
        right = pygame.Rect(16+360+12, 64, w - (16+360+12) - 16, h - 64 - 16)
        return left, right

    def _build_ui(self):
        w,h = self.app.screen.get_size()
        self.lbl = pygame_gui.elements.UILabel(pygame.Rect(16, 16, w-32, 32), "Roster", self.manager)

        list_rect, card_rect = self._calc_boxes(w, h)
        self.list_fighters = pygame_gui.elements.UISelectionList(list_rect, [], self.manager)
        self.card_box = pygame_gui.elements.UITextBox(card_rect, "<b>Select a fighter</b>", self.manager)

        # toolbar
        self.dd_sort = pygame_gui.elements.UIDropDownMenu(
            ["OVR","AGE","LEVEL","CLASS","NAME"], "OVR",
            pygame.Rect(16, h-48, 120, 32), self.manager
        )
        self.btn_dir  = pygame_gui.elements.UIButton(pygame.Rect(144, h-48, 120, 32), "Descending", self.manager)
        self.btn_prev = pygame_gui.elements.UIButton(pygame.Rect(270, h-48, 80, 32), "Prev", self.manager)
        self.btn_next = pygame_gui.elements.UIButton(pygame.Rect(355, h-48, 80, 32), "Next", self.manager)
        self.btn_compare = pygame_gui.elements.UIButton(pygame.Rect(440, h-48, 120, 32), "Compare", self.manager)
        self.btn_back = pygame_gui.elements.UIButton(pygame.Rect(w-16-140, 16, 140, 32), "Back", self.manager)

    def _load_fighters(self):
        t = self.app.career.get_team(self.app.chosen_tid)
        self._fighters = list(t.get("fighters", []))
        self._apply_sort_and_page()

    def _apply_sort_and_page(self):
        key = self.dd_sort.selected_option
        rev = self._desc
        def sort_key(f):
            if key == "OVR": return int(f.get("ovr",0))
            if key == "AGE": return int(f.get("age",0))
            if key == "LEVEL": return int(f.get("level",1))
            if key == "CLASS": return str(f.get("class",""))
            if key == "NAME": return str(f.get("name",""))
            return 0
        s = sorted(self._fighters, key=sort_key, reverse=rev)
        # page
        start = self._page * self.PAGE_SIZE
        chunk = s[start:start+self.PAGE_SIZE]
        items = [f"{f.get('name','?')} — OVR {int(f.get('ovr',0))}" for f in chunk]
        if hasattr(self.list_fighters, "set_item_list"):
            self.list_fighters.set_item_list(items)

    def _update_card_from_selection(self):
        if not self.list_fighters.item_list: return
        sel = self.list_fighters.get_single_selection()
        if not sel: return
        name = sel.split(" — ",1)[0]
        for f in self._fighters:
            if f.get("name")==name:
                info = []
                for k in ("class","level","age","ovr","peak_ovr","hp","ac","speed","str","dex","con","int","wis","cha","dev_trait"):
                    if k in f: info.append(f"{k.upper()}: {f[k]}")
                self.card_box.set_text(f"<b>{f.get('name','?')}</b><br>" + "<br>".join(info))
                return

    def _compare_popup(self):
        # placeholder: you can expand later
        pygame_gui.windows.UIMessageWindow(pygame.Rect(200,200,360,200),"Compare coming soon", self.manager)

    def handle(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.manager.set_window_resolution(event.size)
            w, h = event.size
            list_rect, card_rect = self._calc_boxes(w, h)
            self.list_fighters.set_relative_rect(list_rect)
            self.card_box.set_relative_rect(card_rect)
            # reposition toolbar
            self.dd_sort.set_relative_rect(pygame.Rect(16, h-48, 120, 32))
            self.btn_dir.set_relative_rect(pygame.Rect(144, h-48, 120, 32))
            self.btn_prev.set_relative_rect(pygame.Rect(270, h-48, 80, 32))
            self.btn_next.set_relative_rect(pygame.Rect(355, h-48, 80, 32))
            self.btn_compare.set_relative_rect(pygame.Rect(440, h-48, 120, 32))
            self.btn_back.set_relative_rect(pygame.Rect(w-16-140, 16, 140, 32))

        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED) or \
           (event.type == pygame_gui.UI_BUTTON_PRESSED):
            if event.ui_element == self.btn_back:
                self.app.set_state(ManagerMenuState(self.app))
            elif event.ui_element == self.btn_prev:
                if self._page > 0: self._page -= 1; self._apply_sort_and_page()
            elif event.ui_element == self.btn_next:
                total = max(1, (len(self._fighters)+self.PAGE_SIZE-1)//self.PAGE_SIZE)
                if self._page < total-1: self._page += 1; self._apply_sort_and_page()
            elif event.ui_element == self.btn_dir:
                self._desc = not self._desc; self.btn_dir.set_text("Descending" if self._desc else "Ascending")
                self._apply_sort_and_page()
            elif event.ui_element == self.btn_compare:
                self._compare_popup()

        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED) or \
           (event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED):
            if event.ui_element == self.dd_sort:
                self._page = 0; self._apply_sort_and_page()

        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION) or \
           (event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION):
            if event.ui_element == self.list_fighters:
                self._update_card_from_selection()

        self.manager.process_events(event)

    def update(self, dt): self.manager.update(dt)
    def draw(self, surf): surf.fill(DARK); self.manager.draw_ui(surf)

class ScheduleState:
    def __init__(self, app):
        self.app = app; self.ui = pygame_gui.UIManager(app.screen.get_size()); self._build_ui()

    def _build_ui(self):
        w,h = self.app.screen.get_size()
        self.lbl = pygame_gui.elements.UILabel(pygame.Rect(16,16,w-32,32), "Schedule", self.ui)
        self.btn_back = pygame_gui.elements.UIButton(pygame.Rect(w-16-120,16,120,32),"Back", self.ui)
        # simple list
        self.box = pygame_gui.elements.UITextBox(pygame.Rect(16,64,w-32,h-80), self._html_schedule(), self.ui)

    def _html_schedule(self):
        # simple HTML: show current week fixtures and previous/next
        try:
            html = []
            wk = self.app.career.week
            html.append(f"<b>Week {wk+1}</b><br>")
            for fx in self.app.career.weeks[wk]:
                a = self.app.career.get_team(fx["home"])["name"]
                b = self.app.career.get_team(fx["away"])["name"]
                res = fx.get("result","vs")
                html.append(f"{a} — {b} : {res}")
            return "<br>".join(html)
        except Exception:
            return "No schedule."

    def handle(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.ui.set_window_resolution(event.size); self._build_ui()
        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED) or \
           (event.type == pygame_gui.UI_BUTTON_PRESSED):
            if event.ui_element == self.btn_back:
                self.app.set_state(ManagerMenuState(self.app))
        self.ui.process_events(event)

    def update(self, dt): self.ui.update(dt)
    def draw(self, surf): surf.fill(DARK); self.ui.draw_ui(surf)

class TableState:
    def __init__(self, app):
        self.app = app; self.ui = pygame_gui.UIManager(app.screen.get_size()); self._build_ui()

    def _build_ui(self):
        w,h = self.app.screen.get_size()
        self.lbl = pygame_gui.elements.UILabel(pygame.Rect(16,16,w-32,32), "Table", self.ui)
        self.btn_back = pygame_gui.elements.UIButton(pygame.Rect(w-16-120,16,120,32),"Back", self.ui)
        self.box = pygame_gui.elements.UITextBox(pygame.Rect(16,64,w-32,h-80), self._html_table(), self.ui)

    def _html_table(self):
        try:
            rows = ["<b>Pos  Team                      Pts  W-D-L</b>"]
            tab = self.app.career.table  # list of {tid, pts, w,d,l}
            sortd = sorted(tab, key=lambda r: (-r["pts"], -(r["w"]), r["l"]))
            for i, row in enumerate(sortd, start=1):
                name = self.app.career.get_team(row["tid"])["name"]
                rows.append(f"{i:>2}. {name:24}  {row['pts']:>3}  {row['w']}-{row['d']}-{row['l']}")
            return "<br>".join(rows)
        except Exception:
            return "No table."

    def handle(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.ui.set_window_resolution(event.size); self._build_ui()
        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED) or \
           (event.type == pygame_gui.UI_BUTTON_PRESSED):
            if event.ui_element == self.btn_back:
                self.app.set_state(ManagerMenuState(self.app))
        self.ui.process_events(event)

    def update(self, dt): self.ui.update(dt)
    def draw(self, surf): surf.fill(DARK); self.ui.draw_ui(surf)

class MatchState:
    """Watchable match. Sidebar shows live turn log."""
    GRID_W, GRID_H = 18, 12

    def __init__(self, app, scheduled: bool):
        self.app = app
        self.scheduled = scheduled
        self.ui = pygame_gui.UIManager(app.screen.get_size())
        self.font = pygame.font.SysFont(None, 20)
        self.font_big = pygame.font.SysFont(None, 28)
        self._build_ui()

        # Build fighters for this match
        if scheduled:
            # Your team vs scheduled opponent this week
            fx = self.app.career.get_fixture_for_team(self.app.chosen_tid)
            self.home_tid = fx["home"]; self.away_tid = fx["away"]
        else:
            # exhibition pair chosen previously
            self.home_tid, self.away_tid = self.app.exhibition_pair

        tH = self.app.career.get_team(self.home_tid)
        tA = self.app.career.get_team(self.away_tid)

        teamA = Team(0, tH["name"], tuple(tH.get("color",[120,180,255])))
        teamB = Team(1, tA["name"], tuple(tA.get("color",[255,140,140])))

        # pick top 4 by OVR for now
        home_fs = sorted(tH["fighters"], key=lambda f: int(f.get("ovr",0)), reverse=True)[:4]
        away_fs = sorted(tA["fighters"], key=lambda f: int(f.get("ovr",0)), reverse=True)[:4]

        fighters = [fighter_from_dict({**fd, "team_id":0}) for fd in home_fs] + \
                   [fighter_from_dict({**fd, "team_id":1}) for fd in away_fs]

        layout_teams_tiles(fighters, self.GRID_W, self.GRID_H)
        self.combat = TBCombat(teamA, teamB, fighters, self.GRID_W, self.GRID_H, seed=int(time.time()) & 0xFFFF)

        # turn stepping
        self.auto = False
        self.auto_timer = 0.0
        self.log_lines: List[str] = []
        self._drain_idx = 0

    def _build_ui(self):
        w,h = self.app.screen.get_size()
        pad = 8
        self.btn_back = pygame_gui.elements.UIButton(pygame.Rect(w-16-120, 16, 120, 32),"Back", self.ui)
        self.btn_next = pygame_gui.elements.UIButton(pygame.Rect(w-16-120, 56, 120, 32),"Step Turn", self.ui)
        self.btn_auto = pygame_gui.elements.UIButton(pygame.Rect(w-16-120, 96, 120, 32),"Auto: OFF", self.ui)

    def _push_log(self, text: str):
        self.log_lines.append(text)
        if len(self.log_lines) > 400:
            self.log_lines = self.log_lines[-400:]

    def _drain_events(self):
        evs = self.combat.events
        while self._drain_idx < len(evs):
            e = evs[self._drain_idx]; self._drain_idx += 1
            k = e.kind; p = e.payload
            if k == "init": self._push_log(f"Init: {p.get('name')} (init {p.get('init')})")
            elif k == "round_start": self._push_log(f"— Round {p.get('round')} —")
            elif k == "move_step": self._push_log(f"{p.get('name')} moves to {p.get('to')}")
            elif k == "attack":
                a,d,nat,tac,crit,hit = p.get('attacker'),p.get('defender'),p.get('nat'),p.get('target_ac'),p.get('critical'),p.get('hit')
                if hit: self._push_log(f"{a} attacks {d} (d20={nat} vs AC {tac}) — HIT{' (CRIT!)' if crit else ''}")
                else:   self._push_log(f"{a} attacks {d} (d20={nat} vs AC {tac}) — miss")
            elif k == "damage":
                a,d,amt,hp = p.get('attacker'),p.get('defender'),p.get('amount'),p.get('hp_after')
                self._push_log(f"… {a} deals {amt} to {d} (HP now {hp})")
            elif k == "down":
                self._push_log(f"*** {p.get('name')} is DOWN! ***")
            elif k == "level_up":
                self._push_log(f"↑ {p.get('name')} reached level {p.get('level')}!")
            elif k == "end":
                self._push_log(f"== {p.get('winner') or p.get('reason','Match ended')} ==")

    def handle(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.ui.set_window_resolution(event.size); self._build_ui()

        if (event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED) or \
           (event.type == pygame_gui.UI_BUTTON_PRESSED):
            if event.ui_element == self.btn_back:
                # if scheduled match, we could write result to career here (you might already do it in save_system)
                self.app.set_state(ManagerMenuState(self.app))
            elif event.ui_element == self.btn_next:
                if self.combat.winner is None: self._step_one_turn()
            elif event.ui_element == self.btn_auto:
                self.auto = not self.auto
                self.btn_auto.set_text("Auto: ON" if self.auto else "Auto: OFF")

        self.ui.process_events(event)

    def _step_one_turn(self):
        before = len(self.combat.events)
        self.combat.take_turn()
        if len(self.combat.events) > before:
            self._drain_events()

    def update(self, dt):
        self.ui.update(dt)
        if self.auto and self.combat.winner is None:
            self.auto_timer -= dt
            if self.auto_timer <= 0.0:
                self._step_one_turn()
                self.auto_timer = 0.25

    def draw(self, surf):
        surf.fill((18,18,20))
        # grid area
        grid_w_px = self.app.screen.get_width() - 280
        grid_h_px = self.app.screen.get_height()
        cell_w = grid_w_px // self.GRID_W
        cell_h = grid_h_px // self.GRID_H
        # draw grid
        for gx in range(self.GRID_W):
            for gy in range(self.GRID_H):
                rect = pygame.Rect(gx*cell_w, gy*cell_h, cell_w-1, cell_h-1)
                pygame.draw.rect(surf, (32,34,40), rect, 1)

        # draw fighters
        for f in self.combat.fighters:
            if not getattr(f, "alive", True): col = (100,100,100)
            else:
                col = (255,140,140) if f.team_id==1 else (120,180,255)
            rect = pygame.Rect(f.tx*cell_w+2, f.ty*cell_h+2, cell_w-4, cell_h-4)
            pygame.draw.rect(surf, col, rect)
            # name/HP
            name = getattr(f, "name", "?")
            hp = getattr(f, "hp", 0)
            txt = self.font.render(f"{name} ({hp})", True, WHITE)
            surf.blit(txt, (rect.x+4, rect.y+2))

        # sidebar log
        x0 = grid_w_px + 8
        pygame.draw.rect(surf, (28,30,36), pygame.Rect(grid_w_px, 0, 280, self.app.screen.get_height()))
        hdr = self.font_big.render("Turn Log", True, WHITE); surf.blit(hdr, (x0+8, 12))
        y = 44
        for line in self.log_lines[-28:]:
            ln = self.font.render(line, True, WHITE)
            surf.blit(ln, (x0+8, y))
            y += ln.get_height()+2

        self.ui.draw_ui(surf)

# =====================================================================================
#                                         APP
# =====================================================================================

class App:
    def __init__(self):
        ensure_dir(SAVES_DIR)
        self.settings = load_json(SETTINGS_PATH, DEFAULT_SETTINGS.copy())
        pygame.init()
        try: pygame.mixer.init()
        except Exception: pass

        self.apply_resolution(tuple(self.settings.get("resolution",[1280,720])))
        pygame.display.set_caption("D20 Fight Club — Manager")
        try: pygame.mixer.music.set_volume(float(self.settings.get("volume_master",0.8)))
        except Exception: pass

        self.clock = pygame.time.Clock()
        self.running = True

        # game state (career will be created on "New Game")
        self.career: Optional[Career] = None
        self.current_save_path: Optional[str] = None
        self.chosen_tid: Optional[int] = None
        self.exhibition_pair: Optional[Tuple[int,int]] = None
        self.scheduled_fixture: Optional[bool] = None

        self.state = MenuState(self)

    def apply_resolution(self, res_xy):
        flags = pygame.RESIZABLE | pygame.SCALED
        try:
            self.screen = pygame.display.set_mode(res_xy, flags)
        except Exception:
            self.screen = pygame.display.set_mode(res_xy, pygame.RESIZABLE)

    def set_state(self, state):
        self.state = state

    def run(self):
        try:
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
        except Exception:
            import traceback, datetime
            with open("crash.log", "a", encoding="utf-8") as f:
                f.write(f"\n=== {datetime.datetime.now()} ===\n")
                f.write("".join(traceback.format_exc()))
            raise
        finally:
            pygame.quit()

# =====================================================================================
#                                        ENTRY
# =====================================================================================

def main():
    App().run()

if __name__ == "__main__":
    main()
