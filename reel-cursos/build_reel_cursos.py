#!/usr/bin/env python3
"""Reel "Dia de capacitação": 5 certificados + logo + mascote (1080x1920, 30 fps).

Uso: python3 build_reel_cursos.py <pasta_de_assets> <saida.mp4>

A pasta de assets deve conter: cert01.jpg ... cert05.jpg (assinaturas já
borradas), logo.jpg, mascote.webp, music.mp3 e a pasta fonts/.
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

A = sys.argv[1]
OUT = sys.argv[2]
W, H, FPS = 1080, 1920, 30
SR = 48000

YELLOW = (248, 186, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BG = (8, 8, 8)

F = lambda name, size: ImageFont.truetype(os.path.join(A, "fonts", name), size)

COURSES = [
    ("FICHA DE DADOS\nDE SEGURANÇA", "FDS", ["GHS", "Pictogramas de perigo", "16 seções da FDS"]),
    ("TRÊS PASSOS\nDE SSMA", "Risk Factor", ["Matriz de risco", "Pausar · Processar · Prosseguir"]),
    ("LGPD", "Lei Geral de Proteção de Dados", ["Dados pessoais", "Privacidade", "Responsabilidade"]),
    ("GESTÃO\nAMBIENTAL", "Requisitos legais e monitoramento", ["ISO 14001", "Gestão das águas", "Controle de poeira"]),
    ("FERRAMENTAS\nPERFUROCORTANTES", "Uso seguro de ferramentas afiadas", ["EPIs contra cortes", "Inspeção prévia", "Prevenção"]),
]

# ---------------------------------------------------------------- timeline
INTRO = 3.6
MASCOT = 2.6
CERT = 3.4
RECAP = 3.8
OUTRO = 4.6
T_MASCOT = INTRO
T_CERTS = T_MASCOT + MASCOT
T_RECAP = T_CERTS + CERT * len(COURSES)
T_OUTRO = T_RECAP + RECAP
TOTAL = T_OUTRO + OUTRO


def clamp(x):
    return min(max(x, 0.0), 1.0)


def ease_out(x):
    return 1 - (1 - clamp(x)) ** 3


def ease_in(x):
    return clamp(x) ** 3


def ease_in_out(x):
    return 0.5 - 0.5 * math.cos(math.pi * clamp(x))


def ease_back(x):
    x = clamp(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ---------------------------------------------------------------- helpers
def text_size(draw, txt, font, stroke=0):
    b = draw.textbbox((0, 0), txt, font=font, stroke_width=stroke)
    return b[2] - b[0], b[3] - b[1], b


def fade(layer, a):
    if a < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * max(a, 0))))
    return layer


def draw_centered(img, y, txt, font, fill, stroke=0, stroke_fill=BLACK, alpha=1.0, dx=0, cx=W / 2):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tw, th, b = text_size(d, txt, font, stroke)
    d.text((cx - tw / 2 - b[0] + dx, y - b[1]), txt, font=font, fill=fill,
           stroke_width=stroke, stroke_fill=stroke_fill)
    img.alpha_composite(fade(layer, alpha))
    return th


def pill(img, cx, y, txt, font, bg, fg, pad=(34, 18), alpha=1.0, dy=0, dx=0, outline=None):
    d = ImageDraw.Draw(img)
    tw, th, b = text_size(d, txt, font)
    w, h = tw + pad[0] * 2, th + pad[1] * 2
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    x0, y0 = cx - w / 2 + dx, y + dy
    if outline:
        ld.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=h / 2, fill=bg + (255,),
                             outline=outline + (255,), width=3)
    else:
        ld.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=h / 2, fill=bg + (255,))
    ld.text((x0 + pad[0] - b[0], y0 + pad[1] - b[1]), txt, font=font, fill=fg)
    img.alpha_composite(fade(layer, alpha))
    return w, h


def ring(img, cx, cy, r, width, color, alpha=1.0):
    if r <= 1 or alpha <= 0:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((cx - r, cy - r, cx + r, cy + r), outline=color + (255,),
                                  width=max(1, int(width)))
    img.alpha_composite(fade(layer, alpha))


def burst(img, cx, cy, p, n=10, r0=60, r1=210, color=YELLOW, width=8, rot=0.0):
    """Raios saindo do centro (efeito 'pop'), p de 0 a 1."""
    if p <= 0 or p >= 1:
        return
    d = ImageDraw.Draw(img)
    a = ease_out(p)
    s = r0 + (r1 - r0) * a
    e = r0 + (r1 - r0) * min(1, a * 1.6)
    for k in range(n):
        ang = rot + 2 * math.pi * k / n
        x0, y0 = cx + math.cos(ang) * s, cy + math.sin(ang) * s
        x1, y1 = cx + math.cos(ang) * e, cy + math.sin(ang) * e
        d.line([(x0, y0), (x1, y1)], fill=color + (255,), width=width)


def check_badge(img, cx, cy, p, size=110):
    """Selo circular amarelo com check desenhado progressivamente."""
    if p <= 0:
        return
    s = ease_back(p / 0.5) if p < 0.5 else 1.0
    r = size / 2 * s
    if r < 2:
        return
    d = ImageDraw.Draw(img)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=YELLOW + (255,), outline=BLACK + (255,), width=6)
    q = clamp((p - 0.3) / 0.4)
    if q > 0:
        pts = [(-0.26, 0.02), (-0.06, 0.22), (0.28, -0.2)]
        pts = [(cx + x * size * s, cy + y * size * s) for x, y in pts]
        seg1 = min(1, q * 2)
        p1 = (pts[0][0] + (pts[1][0] - pts[0][0]) * seg1, pts[0][1] + (pts[1][1] - pts[0][1]) * seg1)
        d.line([pts[0], p1], fill=BLACK + (255,), width=int(size * 0.13))
        if q > 0.5:
            seg2 = (q - 0.5) * 2
            p2 = (pts[1][0] + (pts[2][0] - pts[1][0]) * seg2, pts[1][1] + (pts[2][1] - pts[1][1]) * seg2)
            d.line([pts[1], p2], fill=BLACK + (255,), width=int(size * 0.13))


GRID = Image.new("RGBA", (W, H + 90), BG + (255,))
_gd = ImageDraw.Draw(GRID)
for gx in range(0, W + 1, 90):
    _gd.line([(gx, 0), (gx, H + 90)], fill=(22, 22, 22, 255), width=2)
for gy in range(0, H + 91, 90):
    _gd.line([(0, gy), (W, gy)], fill=(22, 22, 22, 255), width=2)

# partículas (poeira dourada) com posições fixas
_rng = np.random.default_rng(7)
PARTS = [(_rng.uniform(0, W), _rng.uniform(0, H), _rng.uniform(2, 6), _rng.uniform(20, 70),
          _rng.uniform(0, 6.28)) for _ in range(38)]


def dark_bg(t, tape=True):
    """Fundo preto com grade em movimento, partículas e fita de sinalização."""
    off = int((t * 60) % 90)
    img = GRID.crop((0, 90 - off, W, 90 - off + H))
    d = ImageDraw.Draw(img)
    for x, y, r, sp, ph in PARTS:
        yy = (y - t * sp) % H
        xx = x + 14 * math.sin(t * 0.8 + ph)
        a = int(60 + 60 * math.sin(t * 2 + ph))
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=YELLOW + (max(a, 0),))
    if tape:
        for yb in (0, H - 36):
            d.rectangle((0, yb, W, yb + 36), fill=YELLOW + (255,))
            sh = int((t * 120) % 72)
            for k in range(-2, W // 72 + 3):
                x0 = k * 72 + sh
                d.polygon([(x0, yb + 36), (x0 + 36, yb + 36), (x0 + 72, yb), (x0 + 36, yb)],
                          fill=(15, 15, 15, 255))
    return img


def diag_wipe(img, q, color=YELLOW, reverse=False):
    """Faixa diagonal que cobre a tela (q 0->1) para transição."""
    if q <= 0:
        return
    d = ImageDraw.Draw(img)
    span = W + H * 0.5
    if not reverse:
        x = -H * 0.5 + span * q
        d.polygon([(-H, 0), (x + H * 0.5, 0), (x, H), (-H, H)], fill=color + (255,))
    else:
        x = -H * 0.5 + span * q
        d.polygon([(x + H * 0.5, 0), (W + H, 0), (W + H, H), (x, H)], fill=color + (255,))


# ---------------------------------------------------------------- assets
logo_full = Image.open(os.path.join(A, "logo.jpg")).convert("RGB")
la = np.asarray(logo_full).astype(np.float32)
alpha = np.clip((la.max(axis=2) - 18) * 3.0, 0, 255).astype(np.uint8)
logo = Image.fromarray(np.dstack([la.astype(np.uint8), alpha]), "RGBA")
logo = logo.crop(logo.getbbox())
LOGO_CACHE = {}


def logo_w(w):
    w = int(w)
    if w not in LOGO_CACHE:
        LOGO_CACHE[w] = logo.resize((w, int(logo.height * w / logo.width)), Image.LANCZOS)
    return LOGO_CACHE[w].copy()


mascot = Image.open(os.path.join(A, "mascote.webp")).convert("RGBA").crop((0, 0, 512, 420))
mascot_mask = Image.new("L", mascot.size, 0)
ImageDraw.Draw(mascot_mask).rounded_rectangle((0, 0, mascot.width, mascot.height), 48, fill=255)
mascot.putalpha(mascot_mask)
MASCOT_BIG = mascot.resize((640, int(420 * 640 / 512)), Image.LANCZOS)

CERTS = []
for i in range(1, 6):
    c = Image.open(os.path.join(A, f"cert{i:02d}.jpg")).convert("RGB")
    CERTS.append(c.resize((1100, int(c.height * 1100 / c.width)), Image.LANCZOS))


def framed_cert(idx, width, border=10):
    c = CERTS[idx].resize((int(width), int(CERTS[idx].height * width / CERTS[idx].width)), Image.LANCZOS)
    f = Image.new("RGBA", (c.width + border * 2, c.height + border * 2), YELLOW + (255,))
    f.paste(c, (border, border))
    return f


def place(img, im, cx, cy, ang=0.0, alpha=1.0, shadow=True):
    if ang:
        im = im.rotate(ang, resample=Image.BICUBIC, expand=True)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.75 * alpha)))
        pad = 40
        big = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
        big.alpha_composite(sh, (pad, pad))
        big = big.filter(ImageFilter.GaussianBlur(22))
        img.alpha_composite(big, (int(cx - big.width / 2 + 12), int(cy - big.height / 2 + 26)))
    img.alpha_composite(fade(im, alpha), (int(cx - im.width / 2), int(cy - im.height / 2)))


f_badge = F("Montserrat-ExtraBold.ttf", 38)
f_h1 = F("Anton.ttf", 150)
f_h2 = F("Anton.ttf", 100)
f_title = F("Anton.ttf", 112)
f_sub = F("Montserrat-Bold.ttf", 44)
f_chip = F("Montserrat-Bold.ttf", 34)
f_small = F("Montserrat-Bold.ttf", 36)
f_num = F("Anton.ttf", 470)


# ---------------------------------------------------------------- scenes
def scene_intro(t):
    img = dark_bg(t)
    # anéis que se expandem a partir do centro
    for k in range(3):
        p = clamp((t - k * 0.12) / 0.9)
        ring(img, W / 2, 520, 40 + 700 * ease_out(p), 10 * (1 - p) + 1, YELLOW, alpha=1 - p)
    p = ease_back((t - 0.15) / 0.7)
    if t > 0.15:
        lg = logo_w(860 * (0.55 + 0.45 * p))
        img.alpha_composite(fade(lg, clamp((t - 0.15) / 0.3)), ((W - lg.width) // 2, 520 - lg.height // 2))
    if t > 0.65:
        q = ease_out((t - 0.65) / 0.45)
        pill(img, W // 2, 800, "06.10.2026 · DIA DE CAPACITAÇÃO", f_badge, YELLOW, BLACK,
             alpha=q, dy=int(40 * (1 - q)))
    if t > 0.95:
        q = ease_out((t - 0.95) / 0.45)
        draw_centered(img, 930 + int(50 * (1 - q)), "HOJE FOI DIA DE", f_h2, WHITE, alpha=q)
    if t > 1.25:
        # contador 1 -> 5
        n = 1 + min(4, int((t - 1.25) / 0.14))
        q = ease_back((t - 1.25) / 0.4)
        if n == 5:
            pop = ease_back((t - 1.25 - 0.56) / 0.3)
            burst(img, 330, 1340, (t - 1.81) / 0.5, n=12, r0=170, r1=300, width=10)
        else:
            pop = 1
        f = F("Anton.ttf", int(470 * (0.6 + 0.4 * q) * (0.85 + 0.15 * pop)))
        draw_centered(img, 1100, str(n), f, YELLOW, cx=330, alpha=clamp((t - 1.25) / 0.15))
    if t > 1.5:
        q = ease_out((t - 1.5) / 0.45)
        draw_centered(img, 1170, "CURSOS", f_h1, WHITE, cx=700, dx=int(80 * (1 - q)), alpha=q)
    if t > 1.75:
        q = ease_out((t - 1.75) / 0.45)
        draw_centered(img, 1360, "CONCLUÍDOS", F("Anton.ttf", 92), YELLOW, cx=700,
                      dx=int(80 * (1 - q)), alpha=q)
    if t > 2.1:
        q = ease_out((t - 2.1) / 0.5)
        d = ImageDraw.Draw(img)
        d.rectangle((140, 1640, 140 + int(800 * q), 1648), fill=YELLOW + (255,))
        draw_centered(img, 1675, "Uni K Educação Corporativa · Kinross Paracatu", f_small, WHITE, alpha=q)
    if t > INTRO - 0.35:
        diag_wipe(img, ease_in_out((t - (INTRO - 0.35)) / 0.35))
    return img


def scene_mascot(t):
    img = dark_bg(t + 4)
    # sai da faixa amarela
    m = MASCOT_BIG
    p = ease_back(t / 0.75)
    y_end = 520
    y = int(-m.height + (y_end + m.height) * p)
    bob = int(10 * math.sin((t - 0.75) * 3.2)) if t > 0.75 else 0
    sway = 2.5 * math.sin(t * 2.4) * clamp(t / 0.75)
    d = ImageDraw.Draw(img)
    d.line([(W // 2, 0), (W // 2, y + bob + 10)], fill=(214, 168, 40, 255), width=8)
    framed = Image.new("RGBA", (m.width + 16, m.height + 16), (0, 0, 0, 0))
    ImageDraw.Draw(framed).rounded_rectangle((0, 0, framed.width - 1, framed.height - 1), 56,
                                             fill=YELLOW + (255,))
    framed.alpha_composite(m, (8, 8))
    place(img, framed, W / 2, y + bob + framed.height / 2, ang=sway)
    # balão de fala
    if t > 0.7:
        q = ease_back((t - 0.7) / 0.4)
        bw, bh = int(860 * q), int(250 * q)
        if bw > 20:
            cx, cy = W // 2, 1430
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            ld.rounded_rectangle((cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2), 40, fill=WHITE + (255,))
            ld.polygon([(cx - 40 * q, cy - bh / 2 + 2), (cx + 30 * q, cy - bh / 2 + 2), (cx, cy - bh / 2 - 60 * q)],
                       fill=WHITE + (255,))
            img.alpha_composite(layer)
            if t > 0.95:
                a = clamp((t - 0.95) / 0.2)
                draw_centered(img, cy - 92, "BORA CONFERIR", F("Anton.ttf", 84), BLACK, alpha=a)
                draw_centered(img, cy + 12, "OS CERTIFICADOS?", F("Anton.ttf", 84), (200, 140, 0), alpha=a)
    if t < 0.35:
        diag_wipe(img, 1 - ease_in_out(t / 0.35), reverse=True)
    if t > MASCOT - 0.3:
        q = ease_in_out((t - (MASCOT - 0.3)) / 0.3)
        ImageDraw.Draw(img).rectangle((0, 0, int(W * q), H), fill=YELLOW + (255,))
    return img


def progress(img, idx, t):
    """5 segmentos na base: os anteriores cheios, o atual enchendo."""
    d = ImageDraw.Draw(img)
    x0, gap, segw, y = 140, 16, (800 - 16 * 4) / 5, 1800
    for k in range(5):
        xa = x0 + k * (segw + gap)
        d.rounded_rectangle((xa, y, xa + segw, y + 14), 7, fill=(50, 50, 50, 255))
        fill = 1 if k < idx else (clamp(t / CERT) if k == idx else 0)
        if fill > 0:
            d.rounded_rectangle((xa, y, xa + max(14, segw * fill), y + 14), 7, fill=YELLOW + (255,))


def scene_cert(t, idx):
    img = dark_bg(t + 8 + idx * 3.4)
    title, sub, chips = COURSES[idx]
    side = 1 if idx % 2 == 0 else -1
    # saída: tudo desliza para o lado oposto
    out = ease_in((t - (CERT - 0.32)) / 0.32)
    ox = int(-side * 1200 * out)

    # logo pequeno + contador
    lg = logo_w(260)
    img.alpha_composite(lg, (60, 80))
    q = ease_out(t / 0.35)
    pill(img, W - 210, 92, f"{idx + 1:02d}/05", F("Montserrat-Black.ttf", 40), YELLOW, BLACK,
         pad=(30, 14), alpha=q, dy=int(-30 * (1 - q)))

    # título do curso (linhas entram em sequência)
    lines = title.split("\n")
    ty = 250 if len(lines) == 2 else 310
    for k, line in enumerate(lines):
        d0 = 0.1 + 0.12 * k
        if t > d0:
            q = ease_out((t - d0) / 0.4)
            col = YELLOW if k == len(lines) - 1 else WHITE
            fnt = f_title
            tmp = ImageDraw.Draw(img)
            while text_size(tmp, line, fnt)[0] > 960:
                fnt = F("Anton.ttf", fnt.size - 6)
            draw_centered(img, ty + k * 128, line, fnt, col, dx=int(side * 120 * (1 - q)) + ox, alpha=q)

    # bloco amarelo de fundo que entra antes do certificado
    cy = 960
    cw = 880
    ch = int(cw * CERTS[idx].height / CERTS[idx].width) + 20
    pb = ease_out((t - 0.15) / 0.4)
    if pb > 0:
        d = ImageDraw.Draw(img)
        bx = W / 2 + side * 26 + side * (1 - pb) * 900 + ox
        d.rectangle((bx - (cw + 20) / 2, cy - ch / 2 + 30, bx + (cw + 20) / 2, cy + ch / 2 + 30),
                    fill=YELLOW + (255,))
        # traços de velocidade
        if pb < 1:
            for k in range(4):
                yy = cy - ch / 2 + 80 + k * (ch / 4)
                ln = 300 * (1 - pb)
                xs = bx - side * ((cw + 20) / 2 + 40)
                d.line([(xs, yy), (xs - side * ln, yy)], fill=YELLOW + (255,), width=6)

    # certificado: entra girando e assenta, depois zoom lento
    pc = ease_back((t - 0.28) / 0.6)
    if t > 0.28:
        zoom = 1 + 0.04 * ease_in_out((t - 0.8) / (CERT - 0.8))
        im = framed_cert(idx, cw * (0.86 + 0.14 * pc) * zoom)
        ang = side * (1 - pc) * 14
        cx = W / 2 + side * (1 - pc) * 700 + ox
        place(img, im, cx, cy, ang=ang, alpha=clamp((t - 0.28) / 0.2))

    # selo de concluído
    if t > 1.0:
        bx, by = W / 2 + cw / 2 - 30 + ox, cy - ch / 2 + 10
        burst(img, bx, by, (t - 1.05) / 0.45, n=10, r0=70, r1=150, width=7)
        check_badge(img, bx, by, (t - 1.0) / 0.6, size=124)

    # subtítulo e chips
    if t > 0.75:
        q = ease_out((t - 0.75) / 0.4)
        draw_centered(img, 1395 + int(30 * (1 - q)), sub, f_sub, WHITE, dx=ox, alpha=q)
    chip_y = 1490
    dd = ImageDraw.Draw(img)
    widths = [text_size(dd, c, f_chip)[0] + 56 for c in chips]
    gap = 18
    rows, cur, curw = [], [], 0
    for c, w_ in zip(chips, widths):
        if cur and curw + gap + w_ > 980:
            rows.append(cur)
            cur, curw = [], 0
        cur.append((c, w_))
        curw += w_ + (gap if len(cur) > 1 else 0)
    if cur:
        rows.append(cur)
    k = 0
    for r, row in enumerate(rows):
        total = sum(w_ for _, w_ in row) + gap * (len(row) - 1)
        x = (W - total) / 2
        for c, w_ in row:
            d0 = 1.0 + 0.15 * k
            if t > d0:
                q = ease_back((t - d0) / 0.35)
                pill(img, x + w_ / 2, chip_y + r * 96, c, f_chip, (24, 24, 24), YELLOW, pad=(28, 16),
                     alpha=clamp((t - d0) / 0.15), dy=int(30 * (1 - q)), dx=ox, outline=YELLOW)
            x += w_ + gap
            k += 1

    progress(img, idx, t)
    if t < 0.3:
        q = ease_in_out(t / 0.3)
        ImageDraw.Draw(img).rectangle((int(W * q), 0, W, H), fill=YELLOW + (255,))
    return img


def scene_recap(t):
    img = dark_bg(t + 30)
    q = ease_out(t / 0.4)
    pill(img, W // 2, 190, "MISSÃO CUMPRIDA", f_badge, YELLOW, BLACK, alpha=q, dy=int(-30 * (1 - q)))
    # leque com os 5 certificados
    cx, cy = W / 2, 900
    for k in range(5):
        d0 = 0.1 + 0.12 * k
        if t <= d0:
            continue
        p = ease_back((t - d0) / 0.55)
        ang_end = (k - 2) * 8
        off_end = (k - 2) * 92
        im = framed_cert(k, 500, border=8)
        ang = ang_end * p
        x = cx + off_end * p
        y = cy + abs(k - 2) * 28 * p + (1 - p) * 900
        place(img, im, x, y, ang=-ang, alpha=clamp((t - d0) / 0.2))
    # carimbo
    if t > 1.0:
        p = (t - 1.0) / 0.35
        s = 1.8 - 0.8 * ease_out(p)
        a = clamp(p * 2)
        st = Image.new("RGBA", (760, 300), (0, 0, 0, 0))
        sd = ImageDraw.Draw(st)
        sd.rounded_rectangle((8, 8, 752, 292), 26, fill=(8, 8, 8, 235), outline=YELLOW + (255,), width=10)
        f1 = F("Anton.ttf", 120)
        tw, th, b = text_size(sd, "5 CERTIFICADOS", f1)
        sd.text(((760 - tw) / 2 - b[0], 34 - b[1]), "5 CERTIFICADOS", font=f1, fill=YELLOW)
        f2 = F("Montserrat-Black.ttf", 56)
        tw, th, b = text_size(sd, "EM UM SÓ DIA", f2)
        sd.text(((760 - tw) / 2 - b[0], 196 - b[1]), "EM UM SÓ DIA", font=f2, fill=WHITE)
        st = st.resize((int(760 * s), int(300 * s)), Image.LANCZOS)
        place(img, st, W / 2, 1300, ang=6, alpha=a, shadow=False)
        if p > 1:
            burst(img, W / 2, 1300, (t - 1.35) / 0.5, n=16, r0=330, r1=470, width=8)
    if t > 1.8:
        q = ease_out((t - 1.8) / 0.5)
        draw_centered(img, 1560 + int(30 * (1 - q)), "Conhecimento também é EPI.", F("Montserrat-Black.ttf", 54),
                      WHITE, alpha=q)
    if t < 0.3:
        q = ease_in_out(t / 0.3)
        ImageDraw.Draw(img).rectangle((int(W * q), 0, W, H), fill=YELLOW + (255,))
    if t > RECAP - 0.35:
        diag_wipe(img, ease_in_out((t - (RECAP - 0.35)) / 0.35))
    return img


def scene_outro(t):
    img = dark_bg(t + 40)
    m = MASCOT_BIG.resize((600, int(MASCOT_BIG.height * 600 / MASCOT_BIG.width)), Image.LANCZOS)
    p = ease_back(t / 0.8)
    y_end = 260
    y = int(-m.height + (y_end + m.height) * p)
    bob = int(8 * math.sin(t * 3.0)) if t > 0.8 else 0
    d = ImageDraw.Draw(img)
    d.line([(W // 2, 0), (W // 2, y + bob + 10)], fill=(214, 168, 40, 255), width=8)
    framed = Image.new("RGBA", (m.width + 16, m.height + 16), (0, 0, 0, 0))
    ImageDraw.Draw(framed).rounded_rectangle((0, 0, framed.width - 1, framed.height - 1), 54, fill=YELLOW + (255,))
    framed.alpha_composite(m, (8, 8))
    place(img, framed, W / 2, y + bob + framed.height / 2)
    if t > 0.6:
        q = ease_out((t - 0.6) / 0.5)
        lg = logo_w(880)
        img.alpha_composite(fade(lg, q), ((W - lg.width) // 2, 1000 + int(50 * (1 - q))))
    if t > 1.1:
        q = ease_out((t - 1.1) / 0.5)
        draw_centered(img, 1410, "Segurança em cada ancoragem.", f_sub, WHITE, alpha=q)
    if t > 1.5:
        q = ease_back((t - 1.5) / 0.45)
        pill(img, W // 2, 1530, "SIGA E COMPARTILHE", F("Montserrat-Black.ttf", 46), YELLOW, BLACK,
             pad=(44, 24), alpha=clamp((t - 1.5) / 0.2), dy=int(30 * (1 - q)))
    if t < 0.35:
        diag_wipe(img, 1 - ease_in_out(t / 0.35), reverse=True)
    if t > OUTRO - 0.6:
        a = ease_in_out((t - (OUTRO - 0.6)) / 0.6)
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * a))))
    return img


def frame_at(t):
    if t < T_MASCOT:
        return scene_intro(t)
    if t < T_CERTS:
        return scene_mascot(t - T_MASCOT)
    if t < T_RECAP:
        k = min(4, int((t - T_CERTS) / CERT))
        return scene_cert(t - T_CERTS - k * CERT, k)
    if t < T_OUTRO:
        return scene_recap(t - T_RECAP)
    return scene_outro(t - T_OUTRO)


# ---------------------------------------------------------------- audio
def load_audio(path, start=0.0, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start)]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-i", path, "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def whoosh(dur=0.35, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    x = rng.standard_normal(n).astype(np.float32)
    # passa-baixa móvel simples (média) com corte que sobe e desce
    t = np.linspace(0, 1, n)
    env = np.sin(np.pi * t) ** 2
    k = 24
    sm = np.convolve(x, np.ones(k) / k, mode="same")
    y = (sm * 0.7 + x * 0.3 * t) * env
    return np.stack([y, y], 1) * 0.35


def ding(freq=1320, dur=0.4):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2 * t)) * np.exp(-t * 9)
    return np.stack([y, y], 1).astype(np.float32) * 0.18


def build_audio(path):
    n = int(TOTAL * SR)
    music = load_audio(os.path.join(A, "music.mp3"), 0, TOTAL + 1)[:n]
    music = np.pad(music, ((0, n - len(music)), (0, 0)))
    t = np.arange(n) / SR
    g = 0.85 * np.clip(t / 0.4, 0, 1) * np.clip((TOTAL - t) / 1.6, 0, 1)
    mix = music * g[:, None]

    def add(snd, at):
        s0 = int(at * SR)
        e = min(n, s0 + len(snd))
        if s0 < n:
            mix[s0:e] += snd[:e - s0]

    for at in (INTRO - 0.35, T_CERTS - 0.3, T_RECAP - 0.05, T_OUTRO - 0.35):
        add(whoosh(seed=int(at * 10)), at)
    for k in range(5):
        base = T_CERTS + k * CERT
        add(whoosh(0.4, seed=k), base + 0.22)
        add(ding(1320 + 110 * k), base + 1.15)
    add(ding(1760, 0.6), T_RECAP + 1.05)
    add(ding(990), INTRO * 0 + 1.81)

    peak = np.abs(mix).max()
    if peak > 0.95:
        mix *= 0.95 / peak
    with open(path, "wb") as fh:
        fh.write(mix.astype(np.float32).tobytes())


# ---------------------------------------------------------------- render
def main():
    if len(sys.argv) > 3:  # modo preview: salva quadros nos tempos pedidos
        for ts in sys.argv[3].split(","):
            frame_at(float(ts)).convert("RGB").save(f"{OUT}_{float(ts):05.2f}.png")
        return
    audio_path = OUT + ".f32"
    build_audio(audio_path)
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", audio_path,
        "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-level", "4.1", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT,
    ], stdin=subprocess.PIPE)
    nframes = int(round(TOTAL * FPS))
    for i in range(nframes):
        enc.stdin.write(frame_at(i / FPS).convert("RGB").tobytes())
        if i % 90 == 0:
            print(f"{i}/{nframes}", flush=True)
    enc.stdin.close()
    enc.wait()
    os.remove(audio_path)
    print("ok", OUT, f"{TOTAL:.1f}s")


if __name__ == "__main__":
    main()
