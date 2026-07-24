"""Meridian Paint — a simple, controller-friendly paint program.

Two drawing paths, both active at once:
  - MOUSE: click-and-drag draws freehand. Works with a real mouse, and
    for free with a controller too via onscreenmenu's system-wide fake
    cursor (see onscreenmenu/features/foreign_focus_watcher.py) - no
    special handling needed here for that case, it's just real mouse
    events by the time they reach this window.
  - CONTROLLER (direct): reads gameinput_api.py the same way every
    other Meridian app does, independent of onscreenmenu - moves its
    own on-canvas crosshair with the left stick/D-pad, A held draws.
    This covers running MeridianPaint on its own without onscreenmenu
    active at all.

Controls (controller): left stick moves the crosshair, A (held) draws,
LB/RB cycle the color palette, LT/RT shrink/grow the brush, Y clears the
canvas (press twice within CLEAR_CONFIRM_SECONDS to confirm), Start
saves, B/Back exits.

Controls (mouse/keyboard): left-click-drag draws, click a palette
swatch to pick a color, scroll wheel or [/] keys resize the brush,
Ctrl+S saves, Escape exits, the [X] box in the corner exits.

HONEST NOTE: this is a first pass, not tested on real hardware from
where it was written (no Windows/display environment available) -
treat the exact feel of the controller cursor speed/accel as a starting
point to tune, not a finished/verified value.
"""

import ctypes
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from crash_logger import install_crash_logging
    install_crash_logging("MeridianPaint")
except Exception:
    pass

import pygame

try:
    from gameinput_api import open_gamepad, XI_BUTTONS
except ImportError:
    open_gamepad = None
    XI_BUTTONS = {}

IS_WINDOWS = sys.platform == "win32"

WIDTH, HEIGHT = 1280, 800
TOOLBAR_HEIGHT = 70
CANVAS_BG = (255, 255, 255)
TOOLBAR_BG = (24, 30, 27)
ACCENT = (124, 255, 178)

PALETTE = [
    (20, 20, 20), (255, 255, 255), (220, 40, 40), (255, 160, 30),
    (255, 220, 40), (60, 200, 90), (50, 140, 255), (160, 80, 220),
    (255, 120, 180), (120, 80, 50),
]

MIN_BRUSH, MAX_BRUSH = 2, 48
STICK_DEADZONE = 0.2
CURSOR_SPEED = 640  # pixels/second at full stick deflection
CLEAR_CONFIRM_SECONDS = 2.0


def _pictures_save_dir():
    """The real Windows Pictures folder via SHGetKnownFolderPath (can be
    relocated, same reasoning as the Downloads plug-on's folder lookup),
    falling back to ~/Pictures if that call fails for any reason."""
    if IS_WINDOWS:
        try:
            FOLDERID_PICTURES = "{33E28130-4E1E-4676-835A-98395C3BC3BB}"
            import uuid

            class _GUID(ctypes.Structure):
                _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                            ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]

            u = uuid.UUID(FOLDERID_PICTURES)
            g = _GUID(u.time_low, u.time_mid, u.time_hi_version, (ctypes.c_ubyte * 8)(*u.bytes[8:]))
            path_ptr = ctypes.c_wchar_p()
            result = ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(path_ptr))
            if result == 0 and path_ptr.value:
                path = path_ptr.value
                ctypes.windll.ole32.CoTaskMemFree(path_ptr)
                if os.path.isdir(path):
                    return os.path.join(path, "Meridian Paint")
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Pictures", "Meridian Paint")


def _parse_open_path_arg():
    """A bare (non "--flag") argument names a file to load onto the
    canvas at startup instead of a blank one - used by the Pictures/
    Downloads sections' Start menu "Open in Meridian Paint" option."""
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            return arg
    return None


def _parse_box_arg():
    for arg in sys.argv[1:]:
        if arg.startswith("--box="):
            try:
                x, y, w, h = (int(v) for v in arg[len("--box="):].split(","))
                return (x, y, w, h)
            except Exception:
                return None
    return None


class MeridianPaint:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Meridian Paint")

        box = _parse_box_arg()
        flags = 0
        if box:
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{box[0]},{box[1]}"
            self.width, self.height = box[2], box[3]
            flags = pygame.NOFRAME
        else:
            self.width, self.height = WIDTH, HEIGHT

        self.screen = pygame.display.set_mode((self.width, self.height), flags)
        self.canvas = pygame.Surface((self.width, self.height - TOOLBAR_HEIGHT))
        self.canvas.fill(CANVAS_BG)

        open_path = _parse_open_path_arg()
        if open_path and os.path.isfile(open_path):
            try:
                loaded = pygame.image.load(open_path)
                cw, ch = self.canvas.get_size()
                lw, lh = loaded.get_size()
                scale = min(cw / lw, ch / lh, 1.0)  # never upscale past 100% - just center smaller images
                new_size = (max(1, int(lw * scale)), max(1, int(lh * scale)))
                loaded = pygame.transform.smoothscale(loaded, new_size)
                self.canvas.blit(loaded, ((cw - new_size[0]) // 2, (ch - new_size[1]) // 2))
            except Exception:
                pass  # unsupported format or a genuinely broken file - fall back to the blank canvas silently

        self.clock = pygame.time.Clock()
        self.running = True

        self.color_index = 0
        self.brush_size = 8
        self.last_draw_pos = None

        self.controller_cursor = [self.width / 2, (self.height - TOOLBAR_HEIGHT) / 2]
        self.controller_drawing = False
        self._last_controller_draw = None
        self.gamepad = open_gamepad() if open_gamepad else None
        self.clear_armed_until = 0

        self.font = pygame.font.SysFont("Segoe UI", 16)

    # ---------------- geometry ----------------
    def exit_box_rect(self):
        return (self.width - 40, 8, 32, 32)

    def palette_rects(self):
        rects = []
        swatch = 36
        gap = 8
        x0 = 16
        y0 = (TOOLBAR_HEIGHT - swatch) // 2
        for i in range(len(PALETTE)):
            rects.append((x0 + i * (swatch + gap), y0, swatch, swatch))
        return rects

    def clear_button_rect(self):
        return (self.width - 200, 18, 80, 34)

    def save_button_rect(self):
        return (self.width - 110, 18, 60, 34)

    # ---------------- drawing ----------------
    def _draw_stroke(self, from_pos, to_pos):
        color = PALETTE[self.color_index]
        if from_pos is None:
            pygame.draw.circle(self.canvas, color, to_pos, self.brush_size // 2)
        else:
            pygame.draw.line(self.canvas, color, from_pos, to_pos, self.brush_size)
            pygame.draw.circle(self.canvas, color, to_pos, self.brush_size // 2)

    def _canvas_point(self, screen_pos):
        return (screen_pos[0], screen_pos[1] - TOOLBAR_HEIGHT)

    def save(self):
        save_dir = _pictures_save_dir()
        try:
            os.makedirs(save_dir, exist_ok=True)
            filename = "paint_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
            pygame.image.save(self.canvas, os.path.join(save_dir, filename))
            return True
        except Exception:
            return False

    def clear_canvas(self):
        self.canvas.fill(CANVAS_BG)

    # ---------------- input: mouse/keyboard ----------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key == pygame.K_LEFTBRACKET:
                self.brush_size = max(MIN_BRUSH, self.brush_size - 2)
            elif event.key == pygame.K_RIGHTBRACKET:
                self.brush_size = min(MAX_BRUSH, self.brush_size + 2)
            elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                self.save()
        elif event.type == pygame.MOUSEWHEEL:
            self.brush_size = max(MIN_BRUSH, min(MAX_BRUSH, self.brush_size + event.y * 2))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if pygame.Rect(self.exit_box_rect()).collidepoint(pos):
                self.running = False
                return
            if pygame.Rect(self.clear_button_rect()).collidepoint(pos):
                self.clear_canvas()
                return
            if pygame.Rect(self.save_button_rect()).collidepoint(pos):
                self.save()
                return
            for i, rect in enumerate(self.palette_rects()):
                if pygame.Rect(rect).collidepoint(pos):
                    self.color_index = i
                    return
            if pos[1] >= TOOLBAR_HEIGHT:
                cp = self._canvas_point(pos)
                self._draw_stroke(None, cp)
                self.last_draw_pos = cp
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.last_draw_pos = None
        elif event.type == pygame.MOUSEMOTION:
            if event.buttons[0] and event.pos[1] >= TOOLBAR_HEIGHT:
                cp = self._canvas_point(event.pos)
                self._draw_stroke(self.last_draw_pos, cp)
                self.last_draw_pos = cp

    # ---------------- input: controller ----------------
    def update_controller(self, dt):
        if not self.gamepad:
            return
        try:
            snap = self.gamepad.poll()
        except Exception:
            snap = None
        if snap is None:
            return

        dx = snap.lx if abs(snap.lx) > STICK_DEADZONE else 0.0
        dy = -snap.ly if abs(snap.ly) > STICK_DEADZONE else 0.0  # XInput: up = +1
        self.controller_cursor[0] = max(0, min(self.width, self.controller_cursor[0] + dx * CURSOR_SPEED * dt))
        self.controller_cursor[1] = max(0, min(self.height - TOOLBAR_HEIGHT, self.controller_cursor[1] + dy * CURSOR_SPEED * dt))

        a_held = bool(snap.buttons & XI_BUTTONS.get("A", 0))
        cp = (self.controller_cursor[0], self.controller_cursor[1])
        if a_held:
            if self.controller_drawing:
                self._draw_stroke(self._last_controller_draw, cp)
            else:
                self._draw_stroke(None, cp)
            self._last_controller_draw = cp
            self.controller_drawing = True
        else:
            self.controller_drawing = False

        if snap.buttons & XI_BUTTONS.get("LEFT_SHOULDER", 0):
            self.color_index = (self.color_index - 1) % len(PALETTE)
        if snap.buttons & XI_BUTTONS.get("RIGHT_SHOULDER", 0):
            self.color_index = (self.color_index + 1) % len(PALETTE)
        if snap.lt > 0.5:
            self.brush_size = max(MIN_BRUSH, self.brush_size - 1)
        if snap.rt > 0.5:
            self.brush_size = min(MAX_BRUSH, self.brush_size + 1)

        if snap.buttons & XI_BUTTONS.get("Y", 0):
            now = time.time()
            if now < self.clear_armed_until:
                self.clear_canvas()
                self.clear_armed_until = 0
            else:
                self.clear_armed_until = now + CLEAR_CONFIRM_SECONDS
        if snap.buttons & XI_BUTTONS.get("START", 0):
            self.save()
        if snap.buttons & (XI_BUTTONS.get("B", 0) | XI_BUTTONS.get("BACK", 0)):
            self.running = False

    # ---------------- draw ----------------
    def draw(self):
        self.screen.fill(TOOLBAR_BG)
        self.screen.blit(self.canvas, (0, TOOLBAR_HEIGHT))

        for i, rect in enumerate(self.palette_rects()):
            pygame.draw.rect(self.screen, PALETTE[i], rect, border_radius=6)
            if i == self.color_index:
                pygame.draw.rect(self.screen, ACCENT, rect, width=3, border_radius=6)

        pygame.draw.rect(self.screen, (40, 50, 45), self.clear_button_rect(), border_radius=6)
        label = "Clear!" if time.time() < self.clear_armed_until else "Clear"
        text = self.font.render(label, True, (255, 200, 200) if time.time() < self.clear_armed_until else (220, 220, 220))
        cx, cy, cw, ch = self.clear_button_rect()
        self.screen.blit(text, (cx + (cw - text.get_width()) // 2, cy + (ch - text.get_height()) // 2))

        pygame.draw.rect(self.screen, (40, 50, 45), self.save_button_rect(), border_radius=6)
        text = self.font.render("Save", True, (220, 220, 220))
        sx, sy, sw, sh = self.save_button_rect()
        self.screen.blit(text, (sx + (sw - text.get_width()) // 2, sy + (sh - text.get_height()) // 2))

        brush_label = self.font.render(f"Brush: {self.brush_size}px", True, (200, 220, 210))
        self.screen.blit(brush_label, (16, TOOLBAR_HEIGHT - 20))

        ex, ey, ew, eh = self.exit_box_rect()
        pygame.draw.rect(self.screen, TOOLBAR_BG, (ex, ey, ew, eh))
        pygame.draw.rect(self.screen, ACCENT, (ex, ey, ew, eh), 2)
        pad = 9
        pygame.draw.line(self.screen, ACCENT, (ex + pad, ey + pad), (ex + ew - pad, ey + eh - pad), 2)
        pygame.draw.line(self.screen, ACCENT, (ex + ew - pad, ey + pad), (ex + pad, ey + eh - pad), 2)

        if self.gamepad:
            cx, cy = self.controller_cursor
            pygame.draw.circle(self.screen, ACCENT, (int(cx), int(cy + TOOLBAR_HEIGHT)), 8, 2)

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update_controller(dt)
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    MeridianPaint().run()
