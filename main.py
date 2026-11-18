#!/usr/bin/env python3
"""Sum up 17 November 2026's world news in one image.

A deterministic, pure-stdlib Python program. It renders a 1600x1000
newspaper-style infographic PNG summarising the six biggest world-news
stories of Tuesday, 17 November 2026, and writes it to
$MAKEFUN_OUTPUT_DIR/image.png (default: ./output/image.png).

No network, no wall-clock time, no randomness, no third-party code:
the PNG encoder and the 5x7 bitmap font below were written by hand
for this program, so two runs always produce byte-identical output.
"""

import os
import struct
import zlib
from binascii import crc32

# ---------------------------------------------------------------------------
# Hand-authored 5x7 bitmap font.
#
# Each glyph is 7 rows of 5 cells. '#' is an inked pixel, '.' is blank.
# Only the characters the infographic needs are defined: A-Z, 0-9 and
# basic punctuation. Text is rendered in capitals.
# ---------------------------------------------------------------------------

FONT = {
    "A": ("..#..", ".#.#.", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "|": ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "&": (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "*": (".....", "#...#", ".#.#.", "#####", ".#.#.", "#...#", "....."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
}

GLYPH_W = 5
GLYPH_H = 7


def text_width(text, scale):
    """Pixel width of text rendered at the given scale."""
    if not text:
        return 0
    return (len(text) * (GLYPH_W + 1) - 1) * scale


def wrap_text(text, max_width, scale):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_width(trial, scale) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Minimal PNG encoder (pure stdlib: struct + zlib + binascii).
# ---------------------------------------------------------------------------

def _png_chunk(kind, data):
    chunk = struct.pack(">I", len(data)) + kind + data
    chunk += struct.pack(">I", crc32(kind + data) & 0xFFFFFFFF)
    return chunk


def encode_png(width, height, rgb):
    """Encode a width*height*3 RGB bytearray as a PNG (filter 0)."""
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter type: None
        raw += rgb[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _png_chunk(b"IEND", b"")
    return png


# ---------------------------------------------------------------------------
# Canvas: a flat RGB buffer with rectangle, circle and text drawing.
# ---------------------------------------------------------------------------

class Canvas:
    def __init__(self, width, height, background):
        self.width = width
        self.height = height
        self.pixels = bytearray(background * (width * height))

    def _set(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            i = (y * self.width + x) * 3
            self.pixels[i:i + 3] = color

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + w)
        y1 = min(self.height, y + h)
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.width + x0) * 3
            self.pixels[i:i + len(row)] = row

    def rect_border(self, x, y, w, h, color, thickness=1):
        self.fill_rect(x, y, w, thickness, color)
        self.fill_rect(x, y + h - thickness, w, thickness, color)
        self.fill_rect(x, y, thickness, h, color)
        self.fill_rect(x + w - thickness, y, thickness, h, color)

    def fill_circle(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.fill_rect(cx - dx, cy + dy, dx * 2 + 1, 1, color)

    def circle_outline(self, cx, cy, r, color, thickness=2):
        for dy in range(-r - thickness, r + thickness + 1):
            for dx in range(-r - thickness, r + thickness + 1):
                d2 = dx * dx + dy * dy
                if (r - thickness) ** 2 <= d2 <= (r + thickness) ** 2:
                    self._set(cx + dx, cy + dy, color)

    def draw_text(self, x, y, text, scale, color):
        """Draw uppercase text; unknown chars fall back to a blank glyph."""
        cx = x
        for ch in text.upper():
            glyph = FONT.get(ch, FONT[" "])
            for gy in range(GLYPH_H):
                row = glyph[gy]
                for gx in range(GLYPH_W):
                    if row[gx] == "#":
                        self.fill_rect(
                            cx + gx * scale, y + gy * scale,
                            scale, scale, color)
            cx += (GLYPH_W + 1) * scale
        return cx

    def draw_text_centered(self, cx, y, text, scale, color):
        self.draw_text(cx - text_width(text, scale) // 2, y, text, scale, color)

    def draw_lines(self, x, y, lines, scale, color, line_gap):
        for line in lines:
            self.draw_text(x, y, line, scale, color)
            y += GLYPH_H * scale + line_gap
        return y


# ---------------------------------------------------------------------------
# The news: six top world stories of Tuesday, 17 November 2026.
# Facts researched from BBC News, AP, Reuters, Al Jazeera, ABC News,
# Spaceflight Now and U.S. Department of Defense reporting of the day.
# ---------------------------------------------------------------------------

PAPER = (247, 243, 236)
NAVY = (15, 32, 64)
INK = (24, 29, 39)
GRAY = (102, 112, 133)
RULE = (217, 210, 196)
WHITE = (255, 255, 255)
GOLD = (232, 181, 77)

STORIES = [
    {
        "category": "WAR IN UKRAINE",
        "color": (180, 35, 24),
        "headline": "KERCH BRIDGE SPAN COLLAPSES AFTER UKRAINIAN STRIKE",
        "summary": (
            "UKRAINE SEVERELY DAMAGED THE BRIDGE LINKING RUSSIA TO "
            "OCCUPIED CRIMEA IN AN OPERATION WEEKS IN THE MAKING. "
            "PRESIDENT ZELENSKYY HAILED IT; THE KREMLIN VOWED TO REBUILD."
        ),
        "source": "BBC NEWS",
        "number": "2",
        "number_label": "CONSECUTIVE DAYS OF STRIKES ON THE BRIDGE",
    },
    {
        "category": "ASIA DIPLOMACY",
        "color": (23, 92, 211),
        "headline": "TRUMP LANDS IN MANILA FOR ASEAN SUMMIT",
        "summary": (
            "PRESIDENT TRUMP ARRIVED IN THE PHILIPPINES TO OPEN A "
            "THREE-DAY ASIA TRIP THAT ENDS IN CHINA, WITH THREE-WAY "
            "TALKS PLANNED WITH XI JINPING AND VLADIMIR PUTIN."
        ),
        "source": "ASSOCIATED PRESS",
        "number": "3",
        "number_label": "DAY ASIA TRIP, ENDING IN CHINA",
    },
    {
        "category": "MIDDLE EAST",
        "color": (181, 71, 8),
        "headline": "TWO TANKERS HIT MINES IN STRAIT OF HORMUZ",
        "summary": (
            "IRAN'S REVOLUTIONARY GUARDS SAID TWO OIL TANKERS STRUCK "
            "NAVAL MINES AND CAUGHT FIRE. A THIRD U.S. AIRCRAFT "
            "CARRIER, USS THEODORE ROOSEVELT, HAS ARRIVED IN THE REGION."
        ),
        "source": "REUTERS / AL JAZEERA",
        "number": "3",
        "number_label": "U.S. CARRIERS NOW IN THE REGION",
    },
    {
        "category": "ECONOMY",
        "color": (6, 118, 71),
        "headline": "JPMORGAN BLAMES SOFTWARE BUG FOR BANKING OUTAGE",
        "summary": (
            "A SOFTWARE BUG SLOWED ONLINE BANKING, BRANCH TRANSACTIONS "
            "AND ZELLE PAYMENTS ON MONDAY. THE BANK SAID THERE WAS NO "
            "INDICATION OF A CYBERATTACK."
        ),
        "source": "ABC NEWS",
        "number": "0",
        "number_label": "INDICATION OF A CYBERATTACK, THE BANK SAID",
    },
    {
        "category": "SPACE",
        "color": (105, 65, 198),
        "headline": "ULA VULCAN ROCKET FAILS, 40 AMAZON SATELLITES LOST",
        "summary": (
            "THE ROCKET SUFFERED AN ANOMALY ABOUT 10 MINUTES AFTER "
            "LAUNCHING FROM CAPE CANAVERAL, FAILING TO DELIVER ITS "
            "PAYLOAD OF 40 AMAZON LEO INTERNET SATELLITES TO ORBIT."
        ),
        "source": "SPACEFLIGHT NOW",
        "number": "40",
        "number_label": "AMAZON LEO SATELLITES LOST",
    },
    {
        "category": "U.S. POLITICS",
        "color": (52, 64, 84),
        "headline": "PENTAGON FAILS FINANCIAL AUDIT FOR NINTH YEAR",
        "summary": (
            "INDEPENDENT AUDITORS AGAIN ISSUED A DISCLAIMER ON THE "
            "PENTAGON'S BOOKS FOR FISCAL 2026, SAYING IT COULD NOT "
            "VERIFY ACCOUNTS COVERING MORE THAN $4.8 TRILLION IN ASSETS."
        ),
        "source": "U.S. DEPARTMENT OF DEFENSE",
        "number": "9",
        "number_label": "STRAIGHT YEARS WITHOUT A CLEAN AUDIT",
    },
]

WIDTH = 1600
HEIGHT = 1000


def _check_charset():
    """Fail loudly if any rendered character lacks a glyph."""
    texts = [
        "THE WORLD IN ONE DAY",
        "TUESDAY, 17 NOVEMBER 2026",
        "SIX STORIES THAT DEFINED THE DAY, FROM THE KERCH BRIDGE "
        "TO THE STRAIT OF HORMUZ",
        "SOURCES: BBC NEWS | AP | REUTERS | AL JAZEERA | ABC NEWS | "
        "SPACEFLIGHT NOW | U.S. DEPARTMENT OF DEFENSE",
        "ALL EVENTS TOOK PLACE ON TUESDAY, 17 NOVEMBER 2026.",
    ]
    for story in STORIES:
        texts += [
            story["category"], story["headline"], story["summary"],
            "SOURCE: " + story["source"], story["number"],
            story["number_label"],
        ]
    missing = sorted({ch for t in texts for ch in t.upper()} - set(FONT))
    if missing:
        raise ValueError("glyphs missing for characters: %r" % (missing,))


def _draw_globe(canvas, cx, cy, r, color):
    """Simple globe: outline, equator and two meridians as chords."""
    canvas.circle_outline(cx, cy, r, color, thickness=3)
    for dy in (-r // 2, 0, r // 2):
        half = int((r * r - dy * dy) ** 0.5)
        canvas.fill_rect(cx - half, cy + dy - 1, half * 2, 2, color)
    for dx in (-r // 2, r // 2):
        half = int((r * r - dx * dx) ** 0.5)
        canvas.fill_rect(cx + dx - 1, cy - half, 2, half * 2, color)


def _draw_card(canvas, x, y, w, h, story):
    color = story["color"]
    canvas.fill_rect(x, y, w, h, WHITE)
    canvas.rect_border(x, y, w, h, RULE, thickness=1)
    canvas.fill_rect(x, y, w, 8, color)

    inner = x + 24
    inner_w = w - 48

    # Category chip.
    tag = story["category"]
    chip_w = text_width(tag, 1) + 16
    canvas.fill_rect(inner, y + 22, chip_w, 19, color)
    canvas.draw_text(inner + 8, y + 26, tag, 1, WHITE)

    # Headline (one or two lines, scale 2).
    head_lines = wrap_text(story["headline"], inner_w, 2)
    canvas.draw_lines(inner, y + 56, head_lines, 2, INK, 6)

    # Summary (scale 1, up to three lines).
    sum_lines = wrap_text(story["summary"], inner_w, 1)
    canvas.draw_lines(inner, y + 104, sum_lines, 1, (71, 84, 103), 5)

    # Divider, then the day's key number and the source.
    canvas.fill_rect(inner, y + 168, inner_w, 1, RULE)
    canvas.draw_text(inner, y + 182, story["number"], 3, color)
    num_w = text_width(story["number"], 3)
    canvas.draw_text(inner + num_w + 14, y + 189, story["number_label"], 1, INK)
    canvas.draw_text(x + w - 24 - text_width("SOURCE: " + story["source"], 1),
                     y + 189, "SOURCE: " + story["source"], 1, GRAY)


def render():
    _check_charset()
    canvas = Canvas(WIDTH, HEIGHT, PAPER)

    # Header band.
    canvas.fill_rect(0, 0, WIDTH, 150, NAVY)
    _draw_globe(canvas, 108, 75, 46, GOLD)
    canvas.draw_text_centered(895, 36, "THE WORLD IN ONE DAY", 4, WHITE)
    canvas.draw_text_centered(895, 88, "TUESDAY, 17 NOVEMBER 2026", 2, GOLD)
    canvas.fill_rect(0, 150, WIDTH, 6, (180, 35, 24))

    # Subhead strip.
    canvas.draw_text_centered(
        WIDTH // 2, 172,
        "SIX STORIES THAT DEFINED THE DAY, FROM THE KERCH BRIDGE "
        "TO THE STRAIT OF HORMUZ",
        1, INK)

    # Story grid: 2 columns x 3 rows.
    col_w = 748
    row_h = 230
    for i, story in enumerate(STORIES):
        col = i % 2
        row = i // 2
        _draw_card(canvas, 40 + col * (col_w + 24), 210 + row * (row_h + 18),
                   col_w, row_h, story)

    # Footer.
    canvas.draw_text_centered(
        WIDTH // 2, 952,
        "SOURCES: BBC NEWS | AP | REUTERS | AL JAZEERA | ABC NEWS | "
        "SPACEFLIGHT NOW | U.S. DEPARTMENT OF DEFENSE",
        1, GRAY)
    canvas.draw_text_centered(
        WIDTH // 2, 972,
        "ALL EVENTS TOOK PLACE ON TUESDAY, 17 NOVEMBER 2026.",
        1, GRAY)

    return canvas


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "output")
    os.makedirs(out_dir, exist_ok=True)
    canvas = render()
    png = encode_png(WIDTH, HEIGHT, canvas.pixels)
    path = os.path.join(out_dir, "image.png")
    with open(path, "wb") as fh:
        fh.write(png)
    print("wrote %s (%dx%d, %d bytes)" % (path, WIDTH, HEIGHT, len(png)))


if __name__ == "__main__":
    main()
