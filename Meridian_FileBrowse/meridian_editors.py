"""
meridian_editors.py — Meridian Explorer's built-in Text Editor and Hex
Editor, opened from the Y options menu ("Edit" / "Hex Edit").

Layout contract (per the design spec): the screen is split into two
dedicated boxes that never overlap —
  * TOP: the editor viewport, which scrolls INTERNALLY (it follows the
    cursor), so document text can never be drawn under the keyboard;
  * BOTTOM: a prominent virtual keyboard in its own bordered box, with a
    wide VOICE input button on its bottom row.

The VOICE button triggers Windows voice typing (the native Win+H flow) by
synthesizing the Win+H chord; dictated characters arrive as ordinary text
input events, exactly as if typed. (Requires Windows' voice typing /
speech services; on systems where voice typing insists on a classic text
field it may decline to inject — the button is a convenience over the
native OS feature, not a bundled speech engine.)

Controls, both editors:
  D-pad / left stick .... move the virtual-keyboard cursor
  A ..................... press the highlighted key
  B ..................... Backspace (text) / Delete byte (hex)
  Y ..................... Shift (text editor)
  LB / RB ............... move the text/hex cursor left / right
  LT / RT ............... move the text/hex cursor up / down a line/row
  Start ................. Save
  Select ................ Voice input (same as the VOICE key)
  Physical keyboard ..... types directly; arrows move the cursor,
                          Ctrl+S saves, Esc exits
"""

import ctypes
import os
import sys
import time

import pygame

IS_WINDOWS = sys.platform == "win32"

MAX_TEXT_BYTES = 2 * 1024 * 1024   # editors are for configs/scripts/notes,
MAX_HEX_BYTES = 4 * 1024 * 1024    # not novels — refuse anything huge

# joystick button indices (matches Meridian Explorer's mapping)
BTN_A, BTN_B, BTN_X, BTN_Y = 0, 1, 2, 3
BTN_LB, BTN_RB = 4, 5
BTN_SELECT, BTN_START = 6, 7

REPEAT_DELAY = 0.35
REPEAT_RATE = 0.06


def _send_win_h():
    """Synthesize Win+H — Windows' native voice-typing hotkey."""
    if not IS_WINDOWS:
        return
    try:
        KEYEVENTF_KEYUP = 0x0002
        VK_LWIN, VK_H = 0x5B, 0x48
        user32 = ctypes.windll.user32
        user32.keybd_event(VK_LWIN, 0, 0, 0)
        user32.keybd_event(VK_H, 0, 0, 0)
        user32.keybd_event(VK_H, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
    except Exception:
        pass


class _Repeater:
    """Hold-to-repeat for controller directions."""

    def __init__(self):
        self._held = {}

    def fire(self, key, held):
        now = time.time()
        if not held:
            self._held.pop(key, None)
            return False
        start, last = self._held.get(key, (None, None))
        if start is None:
            self._held[key] = (now, now)
            return True
        if now - start >= REPEAT_DELAY and now - last >= REPEAT_RATE:
            self._held[key] = (start, now)
            return True
        return False


class _Osk:
    """The shared virtual-keyboard box: a grid of labeled keys plus a
    bottom row whose VOICE / SAVE / EXIT keys are wide and prominent."""

    def __init__(self, rows, shift_rows=None):
        self.rows = rows
        self.shift_rows = shift_rows or rows
        self.shift = False
        self.r = 0
        self.c = 0

    def current_rows(self):
        return self.shift_rows if self.shift else self.rows

    def move(self, dr, dc):
        rows = self.current_rows()
        self.r = (self.r + dr) % len(rows)
        row = rows[self.r]
        if dc:
            self.c = (self.c + dc) % len(row)
        else:
            self.c = min(self.c, len(row) - 1)

    def key(self):
        row = self.current_rows()[self.r]
        return row[min(self.c, len(row) - 1)]

    def draw(self, screen, box, fonts, accent=(0, 255, 255)):
        pygame.draw.rect(screen, (10, 12, 24), box)
        pygame.draw.rect(screen, accent, box, 3)  # its own thick-bordered box
        rows = self.current_rows()
        pad = 8
        row_h = (box.height - pad * (len(rows) + 1)) // len(rows)
        y = box.y + pad
        for ri, row in enumerate(rows):
            weights = [k.get("w", 1) for k in row]
            total_w = sum(weights)
            unit = (box.width - pad * (len(row) + 1)) / total_w
            x = box.x + pad
            for ci, k in enumerate(row):
                w = int(unit * k.get("w", 1))
                rect = pygame.Rect(int(x), y, w, row_h)
                sel = ri == self.r and ci == min(self.c, len(row) - 1)
                special = k.get("special")
                bg = (26, 30, 52) if not special else (20, 40, 44)
                if k.get("prominent"):
                    bg = (16, 46, 40)
                if sel:
                    bg = (0, 90, 100)
                pygame.draw.rect(screen, bg, rect, border_radius=6)
                pygame.draw.rect(screen, accent if sel else (60, 70, 100),
                                 rect, 2 if sel else 1, border_radius=6)
                label = k["label"]
                font = fonts["key_big"] if k.get("prominent") else fonts["key"]
                surf = font.render(label, True,
                                   (180, 255, 240) if k.get("prominent") else (220, 230, 245))
                screen.blit(surf, surf.get_rect(center=rect.center))
                x += w + pad
            y += row_h + pad


def _k(ch, label=None, **kw):
    d = {"ch": ch, "label": label if label is not None else ch}
    d.update(kw)
    return d


def _text_osk():
    def row(chars):
        return [_k(c) for c in chars]
    base = [
        row("`1234567890-="),
        row("qwertyuiop[]\\"),
        row("asdfghjkl;'") + [_k("\n", "ENTER", special=True, w=2)],
        row("zxcvbnm,./") + [_k(None, "BKSP", special=True, action="bksp", w=2)],
        [_k(None, "SHIFT", special=True, action="shift", w=2),
         _k(" ", "SPACE", special=True, w=5),
         _k(None, "TAB", special=True, action="tab", w=1.5)],
        # bottom row: the prominent voice box front and center
        [_k(None, "\u266b VOICE INPUT (Win+H)", special=True, action="voice", prominent=True, w=4),
         _k(None, "SAVE", special=True, action="save", prominent=True, w=2),
         _k(None, "EXIT", special=True, action="exit", prominent=True, w=2)],
    ]
    shift_map = dict(zip("`1234567890-=[]\\;',./", "~!@#$%^&*()_+{}|:\"<>?"))
    shifted = []
    for r in base:
        out = []
        for k in r:
            if k.get("ch") and k["ch"] not in (" ", "\n"):
                ch = shift_map.get(k["ch"], k["ch"].upper())
                out.append(_k(ch, ch, **{kk: v for kk, v in k.items() if kk not in ("ch", "label")}))
            else:
                out.append(k)
        shifted.append(out)
    return _Osk(base, shifted)


def _hex_osk():
    return _Osk([
        [_k(c) for c in "0123456789"],
        [_k(c) for c in "ABCDEF"] + [_k(None, "DEL BYTE", special=True, action="bksp", w=2),
                                     _k(None, "INS 00", special=True, action="insert", w=2)],
        [_k(None, "\u266b VOICE INPUT (Win+H)", special=True, action="voice", prominent=True, w=4),
         _k(None, "SAVE", special=True, action="save", prominent=True, w=2),
         _k(None, "EXIT", special=True, action="exit", prominent=True, w=2)],
    ])


class _EditorBase:
    def __init__(self, app, path, title):
        self.app = app
        self.path = path
        self.title = title
        self.screen = app.screen
        self.clock = app.clock
        self.dirty = False
        self.status = ""
        self.status_until = 0
        self.confirm_exit = False
        self.repeat = _Repeater()
        h = self.screen.get_height()
        # dedicated, non-overlapping boxes: keyboard owns the bottom ~42%
        kb_h = int(h * 0.42)
        self.kb_box = pygame.Rect(20, h - kb_h - 16, self.screen.get_width() - 40, kb_h)
        self.doc_box = pygame.Rect(20, 70, self.screen.get_width() - 40,
                                   self.kb_box.y - 70 - 12)
        self.fonts = {
            "title": pygame.font.SysFont("consolas", 26, bold=True),
            "doc": pygame.font.SysFont("consolas", 20),
            "key": pygame.font.SysFont("consolas", 18, bold=True),
            "key_big": pygame.font.SysFont("consolas", 22, bold=True),
            "status": pygame.font.SysFont("consolas", 17),
        }
        self.line_h = self.fonts["doc"].get_height() + 4

    def flash(self, msg, secs=2.5):
        self.status = msg
        self.status_until = time.time() + secs

    # ---- shared run loop: events + controller + draw ----
    def run(self):
        pygame.key.set_repeat(350, 40)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.TEXTINPUT:
                    for ch in event.text:
                        self.insert_char(ch)
                elif event.type == pygame.KEYDOWN:
                    running = self.handle_key(event)
            if running:
                running = self.handle_controller()
            self.draw()
            self.clock.tick(60)
        pygame.key.set_repeat()  # restore no-repeat for the file browser

    def handle_controller(self):
        for j in self.app.joysticks:
            nb = j.get_numbuttons()
            btn = lambda i: i < nb and j.get_button(i)
            hats = j.get_hat(0) if j.get_numhats() > 0 else (0, 0)
            ax_x = j.get_axis(0) if j.get_numaxes() > 0 else 0
            ax_y = j.get_axis(1) if j.get_numaxes() > 1 else 0
            up = hats[1] > 0 or ax_y < -0.6
            down = hats[1] < 0 or ax_y > 0.6
            left = hats[0] < 0 or ax_x < -0.6
            right = hats[0] > 0 or ax_x > 0.6
            if self.repeat.fire("up", up):
                self.osk.move(-1, 0)
            if self.repeat.fire("down", down):
                self.osk.move(1, 0)
            if self.repeat.fire("left", left):
                self.osk.move(0, -1)
            if self.repeat.fire("right", right):
                self.osk.move(0, 1)
            if self.repeat.fire("A", btn(BTN_A)):
                if not self.press_osk_key():
                    return False
            if self.repeat.fire("B", btn(BTN_B)):
                self.backspace()
            if self.repeat.fire("Y", btn(BTN_Y)):
                self.osk.shift = not self.osk.shift
            if self.repeat.fire("LB", btn(BTN_LB)):
                self.move_cursor(0, -1)
            if self.repeat.fire("RB", btn(BTN_RB)):
                self.move_cursor(0, 1)
            lt = j.get_axis(4) if j.get_numaxes() > 4 else 0
            rt = j.get_axis(5) if j.get_numaxes() > 5 else 0
            if self.repeat.fire("LT", lt > 0.5):
                self.move_cursor(-1, 0)
            if self.repeat.fire("RT", rt > 0.5):
                self.move_cursor(1, 0)
            if self.repeat.fire("START", btn(BTN_START)):
                self.save()
            if self.repeat.fire("SELECT", btn(BTN_SELECT)):
                self.flash("Voice typing requested (Win+H)")
                _send_win_h()
        return True

    def press_osk_key(self):
        """Returns False when the key means 'leave the editor'."""
        k = self.osk.key()
        action = k.get("action")
        if action == "exit":
            return self.request_exit()
        if action == "save":
            self.save()
        elif action == "voice":
            self.flash("Voice typing requested (Win+H)")
            _send_win_h()
        elif action == "shift":
            self.osk.shift = not self.osk.shift
        elif action == "bksp":
            self.backspace()
        elif action == "tab":
            self.insert_char("\t")
        elif action == "insert":
            self.insert_byte_00()
        elif k.get("ch"):
            self.insert_char(k["ch"])
            if self.osk.shift and k["ch"].isalpha():
                self.osk.shift = False  # one-shot shift, like phone keyboards
        return True

    def request_exit(self):
        if self.dirty and not self.confirm_exit:
            self.confirm_exit = True
            self.flash("Unsaved changes! EXIT again to discard, SAVE to keep.", 4)
            return True
        return False

    def insert_byte_00(self):
        pass  # hex editor overrides

    def draw_chrome(self):
        self.screen.fill((4, 6, 14))
        title = f"{self.title} \u2014 {os.path.basename(self.path)}" + (" *" if self.dirty else "")
        self.screen.blit(self.fonts["title"].render(title, True, (0, 255, 255)), (24, 20))
        hint = "A: key   B: bksp   LB/RB LT/RT: move cursor   Start: save   Select: voice   Esc/EXIT: leave"
        self.screen.blit(self.fonts["status"].render(hint, True, (110, 130, 170)),
                         (24, self.kb_box.bottom + 0))
        if time.time() < self.status_until:
            s = self.fonts["status"].render(self.status, True, (255, 220, 120))
            self.screen.blit(s, (self.screen.get_width() - s.get_width() - 24, 26))
        pygame.draw.rect(self.screen, (8, 10, 20), self.doc_box)
        pygame.draw.rect(self.screen, (0, 180, 200), self.doc_box, 2)

    def draw(self):
        self.draw_chrome()
        self.draw_doc()
        self.osk.draw(self.screen, self.kb_box, self.fonts)
        pygame.display.flip()


class TextEditor(_EditorBase):
    def __init__(self, app, path):
        super().__init__(app, path, "TEXT EDIT")
        self.osk = _text_osk()
        raw = b""
        try:
            raw = open(path, "rb").read()
        except OSError:
            pass
        self.encoding = "utf-8"
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            self.encoding = "cp1252"
            text = raw.decode("cp1252", errors="replace")
        self.crlf = "\r\n" in text
        self.lines = text.replace("\r\n", "\n").split("\n") or [""]
        self.row, self.col = 0, 0
        self.scroll = 0

    def insert_char(self, ch):
        self.confirm_exit = False
        line = self.lines[self.row]
        if ch == "\n":
            self.lines[self.row] = line[:self.col]
            self.lines.insert(self.row + 1, line[self.col:])
            self.row += 1
            self.col = 0
        else:
            self.lines[self.row] = line[:self.col] + ch + line[self.col:]
            self.col += len(ch)
        self.dirty = True

    def backspace(self):
        self.confirm_exit = False
        if self.col > 0:
            line = self.lines[self.row]
            self.lines[self.row] = line[:self.col - 1] + line[self.col:]
            self.col -= 1
            self.dirty = True
        elif self.row > 0:
            prev = self.lines[self.row - 1]
            self.col = len(prev)
            self.lines[self.row - 1] = prev + self.lines.pop(self.row)
            self.row -= 1
            self.dirty = True

    def move_cursor(self, dr, dc):
        if dc:
            self.col += dc
            if self.col < 0:
                if self.row > 0:
                    self.row -= 1
                    self.col = len(self.lines[self.row])
                else:
                    self.col = 0
            elif self.col > len(self.lines[self.row]):
                if self.row < len(self.lines) - 1:
                    self.row += 1
                    self.col = 0
                else:
                    self.col = len(self.lines[self.row])
        if dr:
            self.row = max(0, min(len(self.lines) - 1, self.row + dr))
            self.col = min(self.col, len(self.lines[self.row]))

    def handle_key(self, e):
        mods = pygame.key.get_mods()
        if e.key == pygame.K_ESCAPE:
            return self.request_exit()
        if e.key == pygame.K_s and mods & pygame.KMOD_CTRL:
            self.save()
        elif e.key == pygame.K_RETURN:
            self.insert_char("\n")
        elif e.key == pygame.K_BACKSPACE:
            self.backspace()
        elif e.key == pygame.K_TAB:
            self.insert_char("\t")
        elif e.key == pygame.K_LEFT:
            self.move_cursor(0, -1)
        elif e.key == pygame.K_RIGHT:
            self.move_cursor(0, 1)
        elif e.key == pygame.K_UP:
            self.move_cursor(-1, 0)
        elif e.key == pygame.K_DOWN:
            self.move_cursor(1, 0)
        return True

    def save(self):
        try:
            eol = "\r\n" if self.crlf else "\n"
            data = eol.join(self.lines).encode(self.encoding, errors="replace")
            with open(self.path, "wb") as f:
                f.write(data)
            self.dirty = False
            self.confirm_exit = False
            self.flash("Saved.")
        except OSError as e:
            self.flash(f"Save failed: {e}", 4)

    def draw_doc(self):
        visible = self.doc_box.height // self.line_h
        # internal scroll follows the cursor — the keyboard box can never
        # cover the line being edited
        if self.row < self.scroll:
            self.scroll = self.row
        if self.row >= self.scroll + visible:
            self.scroll = self.row - visible + 1
        clip = self.screen.get_clip()
        self.screen.set_clip(self.doc_box)
        y = self.doc_box.y + 4
        for i in range(self.scroll, min(len(self.lines), self.scroll + visible)):
            line = self.lines[i].replace("\t", "    ")
            self.screen.blit(self.fonts["doc"].render(line[:300], True, (225, 235, 250)),
                             (self.doc_box.x + 10, y))
            if i == self.row:
                pre = self.lines[i][:self.col].replace("\t", "    ")
                cx = self.doc_box.x + 10 + self.fonts["doc"].size(pre)[0]
                pygame.draw.rect(self.screen, (0, 255, 255),
                                 (cx, y, 2, self.line_h - 4))
            y += self.line_h
        self.screen.set_clip(clip)


class HexEditor(_EditorBase):
    BYTES_PER_ROW = 16

    def __init__(self, app, path):
        super().__init__(app, path, "HEX EDIT")
        self.osk = _hex_osk()
        try:
            self.data = bytearray(open(path, "rb").read())
        except OSError:
            self.data = bytearray()
        self.pos = 0        # byte index
        self.nibble = 0     # 0 = high, 1 = low
        self.scroll = 0

    def insert_char(self, ch):
        ch = ch.upper()
        if ch not in "0123456789ABCDEF":
            return
        self.confirm_exit = False
        if not self.data:
            self.data = bytearray(b"\x00")
            self.pos = 0
            self.nibble = 0
        b = self.data[self.pos]
        v = int(ch, 16)
        self.data[self.pos] = (v << 4) | (b & 0x0F) if self.nibble == 0 else (b & 0xF0) | v
        self.dirty = True
        # advance nibble-wise
        if self.nibble == 0:
            self.nibble = 1
        else:
            self.nibble = 0
            self.pos = min(len(self.data) - 1, self.pos + 1)

    def insert_byte_00(self):
        self.confirm_exit = False
        self.data.insert(self.pos, 0)
        self.dirty = True
        self.flash("Inserted 00 at cursor.")

    def backspace(self):
        if not self.data:
            return
        self.confirm_exit = False
        del self.data[self.pos]
        self.pos = max(0, min(self.pos, len(self.data) - 1))
        self.nibble = 0
        self.dirty = True

    def move_cursor(self, dr, dc):
        if not self.data:
            return
        if dc:
            n = self.pos * 2 + self.nibble + dc
            n = max(0, min(len(self.data) * 2 - 1, n))
            self.pos, self.nibble = divmod(n, 2)
        if dr:
            self.pos = max(0, min(len(self.data) - 1, self.pos + dr * self.BYTES_PER_ROW))

    def handle_key(self, e):
        mods = pygame.key.get_mods()
        if e.key == pygame.K_ESCAPE:
            return self.request_exit()
        if e.key == pygame.K_s and mods & pygame.KMOD_CTRL:
            self.save()
        elif e.key == pygame.K_BACKSPACE or e.key == pygame.K_DELETE:
            self.backspace()
        elif e.key == pygame.K_LEFT:
            self.move_cursor(0, -1)
        elif e.key == pygame.K_RIGHT:
            self.move_cursor(0, 1)
        elif e.key == pygame.K_UP:
            self.move_cursor(-1, 0)
        elif e.key == pygame.K_DOWN:
            self.move_cursor(1, 0)
        return True

    def save(self):
        try:
            with open(self.path, "wb") as f:
                f.write(bytes(self.data))
            self.dirty = False
            self.confirm_exit = False
            self.flash("Saved.")
        except OSError as e:
            self.flash(f"Save failed: {e}", 4)

    def draw_doc(self):
        visible = self.doc_box.height // self.line_h
        row = self.pos // self.BYTES_PER_ROW
        if row < self.scroll:
            self.scroll = row
        if row >= self.scroll + visible:
            self.scroll = row - visible + 1
        clip = self.screen.get_clip()
        self.screen.set_clip(self.doc_box)
        mono = self.fonts["doc"]
        char_w = mono.size("0")[0]
        y = self.doc_box.y + 4
        total_rows = max(1, (len(self.data) + self.BYTES_PER_ROW - 1) // self.BYTES_PER_ROW)
        for r in range(self.scroll, min(total_rows, self.scroll + visible)):
            off = r * self.BYTES_PER_ROW
            chunk = self.data[off:off + self.BYTES_PER_ROW]
            self.screen.blit(mono.render(f"{off:08X}", True, (100, 130, 170)),
                             (self.doc_box.x + 10, y))
            hx = self.doc_box.x + 10 + char_w * 10
            for i, b in enumerate(chunk):
                idx = off + i
                sel = idx == self.pos
                col = (0, 255, 255) if sel else (225, 235, 250)
                s = mono.render(f"{b:02X}", True, col)
                x = hx + i * char_w * 3
                if sel:
                    nib_x = x + (0 if self.nibble == 0 else char_w)
                    pygame.draw.rect(self.screen, (0, 90, 100),
                                     (nib_x - 1, y - 1, char_w + 2, self.line_h - 2))
                self.screen.blit(s, (x, y))
            ax = hx + self.BYTES_PER_ROW * char_w * 3 + char_w * 2
            ascii_repr = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            self.screen.blit(mono.render(ascii_repr, True, (150, 170, 200)), (ax, y))
            y += self.line_h
        self.screen.set_clip(clip)


def run_text_editor(app, path):
    try:
        if os.path.getsize(path) > MAX_TEXT_BYTES:
            return False, "File too large for the built-in text editor (2 MB max)."
    except OSError:
        pass
    TextEditor(app, path).run()
    return True, None


def run_hex_editor(app, path):
    try:
        if os.path.getsize(path) > MAX_HEX_BYTES:
            return False, "File too large for the built-in hex editor (4 MB max)."
    except OSError:
        pass
    HexEditor(app, path).run()
    return True, None
