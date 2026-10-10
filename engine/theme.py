"""Display modes.

Games draw with *roles* ("frame", "player", "piece_T", ...), never raw colours.
A theme turns a role into an ANSI SGR sequence (always on a black background):

- PHOSPHOR: a green monochrome CRT. Things you control are bright green,
  everything else normal green, background detail faint green.
- CGA: the 16-colour graphics adapter. Every kind of thing gets its own colour.
"""

_MONO_BRIGHT = {
    "bright", "title", "select", "bulb_on", "warn",
    "snake_head", "food", "player", "bullet", "explosion", "rainbow0", "car_player",
}
_MONO_DIM = {"dim", "star", "star_bright", "bulb_off", "road_line", "grass", "tree"}

_CGA = {
    "text": "37", "bright": "97", "dim": "90", "title": "96", "frame": "37",
    "select": "93", "warn": "91", "bulb_on": "93", "bulb_off": "90",
    "piece": "37", "piece_I": "96", "piece_O": "93", "piece_T": "95",
    "piece_S": "92", "piece_Z": "91", "piece_J": "94", "piece_L": "33",
    "snake_head": "93", "snake_body": "92", "food": "91",
    "player": "96", "bullet": "93", "enemy_bullet": "91", "explosion": "93",
    "enemy_grunt": "92", "enemy_wing": "95", "enemy_boss": "91",
    "star": "90", "star_bright": "37",
    "car_player": "96", "car_oncoming": "91", "car_same": "94", "truck": "95",
    "pothole": "33", "blockade": "93", "road_edge": "97", "road_line": "37",
    "road_center": "93", "grass": "32", "tree": "92",
    "rainbow0": "91", "rainbow1": "93", "rainbow2": "92",
    "rainbow3": "96", "rainbow4": "94", "rainbow5": "95",
}


def _mono(role):
    if role in _MONO_BRIGHT or role.startswith(("active_", "logo")):
        return "92"
    if role in _MONO_DIM:
        return "2;32"
    return "32"


def _cga(role):
    if role.startswith("active_"):
        role = "piece_" + role[len("active_"):]
    elif role.startswith("logo"):
        role = "rainbow" + role[len("logo"):]
    return _CGA.get(role, "37")


class Theme:
    def __init__(self, key, name, blurb, lookup):
        self.key = key
        self.name = name
        self.blurb = blurb
        self._lookup = lookup
        self._cache = {}

    def sgr(self, role):
        code = self._cache.get(role)
        if code is None:
            code = self._cache[role] = f"\x1b[0;{self._lookup(role)};40m"
        return code

    @property
    def base(self):
        return self.sgr("text")


PHOSPHOR = Theme("phosphor", "PHOSPHOR", "green monochrome monitor", _mono)
CGA = Theme("cga", "CGA", "16-colour graphics adapter", _cga)
THEMES = (PHOSPHOR, CGA)


def by_key(key, default=PHOSPHOR):
    return next((t for t in THEMES if t.key == key), default)


def next_theme(theme):
    return THEMES[(THEMES.index(theme) + 1) % len(THEMES)]
