"""Key-to-action mapping and auto-repeat (DAS/ARR).

Terminals don't report key releases. When the platform can tell us whether a
key is physically down (`is_down`, Windows), we ignore the OS auto-repeat and
run our own DAS/ARR timing. Otherwise every key event is one action and the
OS keyboard repeat drives held keys.
"""

KEYMAP = {
    "LEFT": "left", "a": "left",
    "RIGHT": "right", "d": "right",
    "DOWN": "soft_drop", "s": "soft_drop",
    "SPACE": "hard_drop", "w": "hard_drop",
    "UP": "rotate_cw", "x": "rotate_cw",
    "z": "rotate_ccw",
    "c": "hold",
    "p": "pause", "ESC": "pause",
}

SHIFT_ACTIONS = ("left", "right")
DAS = 0.170
ARR = 0.050


class Controls:
    def __init__(self, is_down=None, das=DAS, arr=ARR):
        self.is_down = is_down
        self.das = das
        self.arr = arr
        self.reset()

    def reset(self):
        self._shift = None  # [action, key, next_repeat_time]
        self._soft_key = None
        self._latched = set()

    @property
    def soft_drop(self):
        return self._soft_key is not None

    def update(self, keys, now):
        """Turn this frame's key events into a list of actions."""
        if self.is_down is None:
            actions = [KEYMAP.get(key) for key in keys]
            return ["soft_step" if a == "soft_drop" else a for a in actions if a]

        actions = []
        self._tick(now, actions)
        for key in keys:
            action = KEYMAP.get(key)
            if action is None:
                continue
            if action in SHIFT_ACTIONS:
                if self._shift and self._shift[1] == key:
                    continue  # OS auto-repeat of a key we're already handling
                actions.append(action)
                self._shift = [action, key, now + self.das]
            elif action == "soft_drop":
                self._soft_key = key
            elif key not in self._latched:
                actions.append(action)
                self._latched.add(key)
        return actions

    def _tick(self, now, actions):
        if self._shift:
            action, key, next_time = self._shift
            if not self.is_down(key):
                self._shift = None
            else:
                while now >= next_time:
                    actions.append(action)
                    next_time += self.arr
                self._shift[2] = next_time
        if self._soft_key and not self.is_down(self._soft_key):
            self._soft_key = None
        self._latched = {key for key in self._latched if self.is_down(key)}
