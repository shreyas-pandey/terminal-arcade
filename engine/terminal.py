"""Terminal setup/teardown and raw keyboard input (Windows + POSIX).

Keys are reported as names: "UP", "DOWN", "LEFT", "RIGHT", "ENTER", "ESC",
"SPACE", "CTRL_C", or a lower-case character.
"""

import atexit
import os
import shutil
import sys

ENTER_SEQ = "\x1b[?1049h\x1b[?25l\x1b[0;32;40m\x1b[2J\x1b[H"
EXIT_SEQ = "\x1b[0m\x1b[2J\x1b[H\x1b[?25h\x1b[?1049l"

_SPECIAL = {"\r": "ENTER", "\n": "ENTER", " ": "SPACE", "\x1b": "ESC", "\x03": "CTRL_C"}

if os.name == "nt":
    import ctypes
    import msvcrt
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.GetStdHandle.restype = wintypes.HANDLE
    _kernel32.GetStdHandle.argtypes = (wintypes.DWORD,)
    _kernel32.GetConsoleMode.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    _kernel32.SetConsoleMode.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    _user32 = ctypes.WinDLL("user32")
    _user32.GetAsyncKeyState.restype = ctypes.c_short
    _user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)

    _STD_OUTPUT_HANDLE = wintypes.DWORD(-11 & 0xFFFFFFFF)
    _ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    _WIN_ARROWS = {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT"}
    _VK = {"UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
           "SPACE": 0x20, "ENTER": 0x0D, "ESC": 0x1B}
else:
    import select
    import termios
    import tty

    _ANSI_ARROWS = {"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT"}


def _key_name(ch):
    return _SPECIAL.get(ch, ch.lower())


class Terminal:
    def __init__(self, out=sys.stdout):
        self.out = out
        self._active = False
        self._saved = None
        self.is_down = self._win_is_down if os.name == "nt" else None

    def __enter__(self):
        if os.name == "nt":
            handle = _kernel32.GetStdHandle(_STD_OUTPUT_HANDLE)
            mode = wintypes.DWORD()
            if _kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                self._saved = (handle, mode.value)
                _kernel32.SetConsoleMode(handle, mode.value | _ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        else:
            fd = sys.stdin.fileno()
            self._saved = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        self._active = True
        atexit.register(self.restore)
        self.write(ENTER_SEQ)
        return self

    def __exit__(self, *exc):
        self.restore()
        return False

    def restore(self):
        if not self._active:
            return
        self._active = False
        self.write(EXIT_SEQ)
        if self._saved is None:
            return
        if os.name == "nt":
            _kernel32.SetConsoleMode(*self._saved)
        else:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._saved)

    def write(self, text):
        self.out.write(text)
        self.out.flush()

    def size(self):
        return shutil.get_terminal_size((80, 24))

    def read_keys(self):
        return self._read_windows() if os.name == "nt" else self._read_posix()

    # --- Windows ------------------------------------------------------

    @staticmethod
    def _read_windows():
        keys = []
        while msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):
                name = _WIN_ARROWS.get(msvcrt.getwch())
                if name:
                    keys.append(name)
            else:
                keys.append(_key_name(ch))
        return keys

    @staticmethod
    def _win_is_down(key):
        vk = _VK.get(key) or (ord(key.upper()) if len(key) == 1 else None)
        return vk is not None and bool(_user32.GetAsyncKeyState(vk) & 0x8000)

    # --- POSIX --------------------------------------------------------

    @staticmethod
    def _read_posix():
        fd = sys.stdin.fileno()
        data = b""
        while select.select([fd], [], [], 0)[0]:
            chunk = os.read(fd, 1024)
            if not chunk:
                break
            data += chunk
        text = data.decode(errors="ignore")
        keys = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "\x1b" and i + 2 < len(text) and text[i + 1] in "[O":
                name = _ANSI_ARROWS.get(text[i + 2])
                if name:
                    keys.append(name)
                i += 3
                continue
            keys.append(_key_name(ch))
            i += 1
        return keys
