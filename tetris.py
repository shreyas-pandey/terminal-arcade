"""ASCII Tetris. Run with: python tetris.py"""

from src.app import App
from src.terminal import Terminal


def main():
    try:
        with Terminal() as term:
            App(term).run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
