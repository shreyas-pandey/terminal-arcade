"""Key-to-action mapping with auto-repeat (DAS/ARR) and held keys.

Terminals don't report key releases. When the platform can tell us whether a
key is physically down (`is_down`, Windows), we ignore the OS auto-repeat and
run our own timing. Otherwise every key event is one action and the OS
keyboard repeat drives held keys.

Each game declares three kinds of action:
- repeat: fires on press, then every `arr` seconds after `das` while held.
- held:   no event; query `held(action)` each frame (soft drop, auto-fire).
- other:  fires once per press (rotate, pause, ...).
"""

OPPOSITE = {"left": "right", "right": "left", "up": "down", "down": "up"}
DAS = 0.170
ARR = 0.050


class Controls:
    def __init__(self, keymap, is_down=None, repeat=(), held=(), das=DAS, arr=ARR):
        self.keymap = keymap
        self.is_down = is_down
        self.repeat_actions = set(repeat)
        self.held_actions = set(held)
        self.das = das
        self.arr = arr
        self.reset()

    def reset(self):
        self._repeat = {}  # action -> [key, next_repeat_time]
        self._held = {}  # action -> key
        self._latched = set()

    def held(self, action):
        return action in self._held

    def update(self, keys, now):
        """Turn this frame's key events into a list of actions."""
        if self.is_down is None:
            return [self.keymap[key] for key in keys if key in self.keymap]

        actions = []
        self._tick(now, actions)
        for key in keys:
            action = self.keymap.get(key)
            if action is None:
                continue
            if action in self.repeat_actions:
                current = self._repeat.get(action)
                if current and current[0] == key:
                    continue  # OS auto-repeat of a key we're already handling
                actions.append(action)
                self._repeat.pop(OPPOSITE.get(action), None)
                self._repeat[action] = [key, now + self.das]
            elif action in self.held_actions:
                self._held[action] = key
            elif key not in self._latched:
                actions.append(action)
                self._latched.add(key)
        return actions

    def _tick(self, now, actions):
        for action, state in list(self._repeat.items()):
            key, next_time = state
            if not self.is_down(key):
                del self._repeat[action]
                continue
            while now >= next_time:
                actions.append(action)
                next_time += self.arr
            state[1] = next_time
        self._held = {a: k for a, k in self._held.items() if self.is_down(k)}
        self._latched = {k for k in self._latched if self.is_down(k)}
