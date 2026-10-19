from pygments import lex
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.token import Token, Comment, Keyword, Name, String, Number, Operator
from PIL import Image, ImageDraw, ImageFont

MONO_FONT = "/System/Library/Fonts/Monaco.ttf"

PALETTE = {
    Comment: "#75715e",
    Keyword: "#f92672",
    Keyword.Constant: "#ae81ff",
    Name.Tag: "#f92672",
    Name.Class: "#a6e22e",
    Name.Function: "#a6e22e",
    Name.Decorator: "#a6e22e",
    Name.Builtin: "#66d9ef",
    Name.Attribute: "#a6e22e",
    Name: "#f8f8f2",
    String: "#e6db74",
    Number: "#ae81ff",
    Operator: "#f92672",
    Token.Punctuation: "#f8f8f2",
}

BG = "#1e1f1c"
DEFAULT_FG = "#f8f8f2"


def _color(token_type):
    t = token_type
    while t is not None:
        if t in PALETTE:
            return PALETTE[t]
        t = t.parent
    return DEFAULT_FG


def _resolve_lexer(code, language):
    try:
        return get_lexer_by_name(language)
    except Exception:
        return guess_lexer(code)


def _layout(code, language, font_size, padding, line_pad, max_width):
    lines = code.split("\n") or [""]
    font = ImageFont.truetype(MONO_FONT, font_size)
    line_height = font_size + line_pad
    longest = max(lines, key=len)
    text_w = font.getlength(longest)
    img_w = int(text_w + padding * 2)
    img_h = int(line_height * len(lines) + padding * 2)

    if img_w > max_width:
        scale = max_width / img_w
        font_size = max(int(font_size * scale), 12)
        font = ImageFont.truetype(MONO_FONT, font_size)
        line_pad = max(int(line_pad * scale), 4)
        line_height = font_size + line_pad
        padding = max(int(padding * scale), 16)
        text_w = font.getlength(longest)
        img_w = int(text_w + padding * 2)
        img_h = int(line_height * len(lines) + padding * 2)

    return font, padding, line_height, img_w, img_h, lines


def _draw(code, lexer, font, padding, line_height, size):
    img = Image.new("RGB", size, BG)
    draw = ImageDraw.Draw(img)
    x = padding
    y = padding
    for ttype, value in lex(code, lexer):
        if not value:
            continue
        parts = value.split("\n")
        for i, part in enumerate(parts):
            if part:
                draw.text((x, y), part, font=font, fill=_color(ttype))
                x += font.getlength(part)
            if i < len(parts) - 1:
                x = padding
                y += line_height
    return img


def render_code_image(code, language, font_size=34, padding=48, line_pad=10, max_width=1000):
    lexer = _resolve_lexer(code, language)
    font, padding, line_height, img_w, img_h, _ = _layout(
        code, language, font_size, padding, line_pad, max_width
    )
    return _draw(code, lexer, font, padding, line_height, (img_w, img_h))


def render_progressive_frames(code, language, font_size=34, padding=48, line_pad=10, max_width=1000):
    lexer = _resolve_lexer(code, language)
    font, padding, line_height, img_w, img_h, lines = _layout(
        code, language, font_size, padding, line_pad, max_width
    )

    frames = []
    for i in range(1, len(lines) + 1):
        partial = "\n".join(lines[:i])
        frames.append(_draw(partial, lexer, font, padding, line_height, (img_w, img_h)))
    return frames
