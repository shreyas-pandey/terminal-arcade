"""A grid of characters, each tagged with a theme role."""


class Canvas:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.chars = [[" "] * width for _ in range(height)]
        self.roles = [["text"] * width for _ in range(height)]

    def put(self, x, y, text, role="text"):
        """Write text (spaces included) starting at (x, y), clipped to the canvas."""
        if not 0 <= y < self.height:
            return
        for i, ch in enumerate(text):
            col = x + i
            if 0 <= col < self.width:
                self.chars[y][col] = ch
                self.roles[y][col] = role

    def sprite(self, x, y, rows, role="text"):
        """Write multi-row art; spaces are transparent."""
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch != " ":
                    self.put(x + dx, y + dy, ch, role)

    def center(self, y, text, role="text"):
        self.put((self.width - len(text)) // 2, y, text, role)

    def lines(self, theme):
        out = []
        for chars, roles in zip(self.chars, self.roles):
            parts, current = [], None
            for ch, role in zip(chars, roles):
                if ch != " " and role != current:  # spaces look the same in any role
                    parts.append(theme.sgr(role))
                    current = role
                parts.append(ch)
            out.append("".join(parts))
        return out
