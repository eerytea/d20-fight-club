def _draw_player_stats(self, screen: pygame.Surface):
    rect = self.rect_stats
    if not rect: return

    p = self._selected_player()
    if not p:
        # intentionally blank when no player selected
        self.stats_content_h = 0
        return

    # unified getter
    def G(key, default=None): return p.get(key, p.get(key.upper(), default))

    name = G("name","Unknown"); num = int(G("num",0))
    race = G("race","-"); origin = G("origin", self._country().get("name","-"))
    ovr = int(G("ovr", G("OVR", 60))); pot = int(G("potential",70))
    cls = G("class","Fighter"); hp = int(G("hp",10)); max_hp = int(G("max_hp", hp)); ac = int(G("ac",12))
    STR = int(G("str",G("STR",10))); DEX = int(G("dex",G("DEX",10))); CON = int(G("con",G("CON",10)))
    INT = int(G("int",G("INT",10))); WIS = int(G("wis",G("WIS",10))); CHA = int(G("cha",G("CHA",10)))
    wpn = G("weapon",{})
    weapon_name = (wpn.get("name") if isinstance(wpn,dict) else (wpn if isinstance(wpn,str) else "-"))
    equipped_armor = (
        G("equipped_armor", None)
        or (G("armor",{}).get("name") if isinstance(G("armor",None),dict) else (G("armor") if isinstance(G("armor",None),str) else None))
        or G("armor_name", None) or "-"
    )

    # Clip region for scrolling
    clip = rect.inflate(-12, -16)
    prev = screen.get_clip(); screen.set_clip(clip)

    x0 = rect.x + 12
    # moved up one line: was +36; now +12
    y = rect.y + 12 + self.scroll_stats
    line_h = self.font.get_height() + 6

    def line(text: str):
        nonlocal y
        surf = self.font.render(text, True, (220,220,225))
        screen.blit(surf, (x0, y)); y += line_h

    # --- Top lines (labels removed for name/race/origin)
    line(f"{name}    #{num:02d}")
    line(f"{race}    {origin}    OVR: {ovr}    Potential: {pot}")
    line(f"Class: {cls}    HP: {hp}/{max_hp}    AC: {ac}")

    # Attributes grid
    y += 4
    labels = ("STR","DEX","CON","INT","WIS","CHA"); vals = (STR,DEX,CON,INT,WIS,CHA)
    col_w = (rect.w - 24) // 6; top_y = y
    for i, lab in enumerate(labels):
        lx = x0 + i*col_w + col_w//2
        surf = self.small.render(lab, True, (210,210,215))
        screen.blit(surf, (lx - surf.get_width()//2, top_y))
    y = top_y + self.small.get_height() + 4
    for i, v in enumerate(vals):
        lx = x0 + i*col_w + col_w//2
        surf = self.h2.render(str(v), True, (235,235,240))
        screen.blit(surf, (lx - surf.get_width()//2, y))
    y += self.h2.get_height() + 10

    line(f"Equipped Armor: {equipped_armor}    Weapon: {weapon_name}")

    # Update content height for scroll clamp (base moved from +36 to +12)
    self.stats_content_h = max(0, (y - (rect.y + 12)))

    screen.set_clip(prev)
