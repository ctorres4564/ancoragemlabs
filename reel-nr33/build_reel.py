#!/usr/bin/env python3
"""Monta o reel NR 33 da Ancoragem Labs (1080x1920, 30 fps).

Uso: python3 build_reel.py <pasta_de_assets> <saida.mp4>

A pasta de assets deve conter: video1.mp4, video2.mp4, music.mp3,
logo.jpg, mascote.webp, certificado.jpg e a pasta fonts/.
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

F = lambda name, size: ImageFont.truetype(os.path.join(A, "fonts", name), size)

# ---------------------------------------------------------------- timeline
INTRO = 3.0
V1_IN, V1_OUT = 0.0, 19.0          # trecho do video1 (fala do instrutor)
V2_IN, V2_OUT = 13.0, 19.0         # trecho do video2 (so imagem, sem audio)
CERT = 6.5
OUTRO = 5.5

T_V1 = INTRO
T_V2 = T_V1 + (V1_OUT - V1_IN)
T_CERT = T_V2 + (V2_OUT - V2_IN)
T_OUTRO = T_CERT + CERT
TOTAL = T_OUTRO + OUTRO

# Legendas do video1 (tempos do SRT, relativos ao video1). O trecho 7 do SRT
# ("A gente vai fazer muito sábio, né?") foi omitido por ser transcrição
# duvidosa, e o 10 ("Viu, Cristo?") cai depois do fim do vídeo.
CAPS = [
    (0.44, 4.20, "Aí, vocês vão elaborar a RT com base", {"RT"}),
    (4.20, 6.12, "nesse ambiente aqui, tá?", {"AMBIENTE"}),
    (6.70, 7.84, "De acordo com a atividade.", {"ATIVIDADE."}),
    (8.14, 10.14, "Vocês vão criar uma atividade", {"ATIVIDADE"}),
    (10.14, 11.34, "que vocês podem realizar aqui.", {"REALIZAR"}),
    (12.88, 14.56, "E a RT...", {"RT..."}),
    (16.96, 19.00, "A RT vai ser com base nesse ambiente.", {"RT", "AMBIENTE."}),
]
# Só toca o áudio original onde há fala transcrita; o resto fica mudo.
V1_SPEECH = [(0.30, 11.45), (12.75, 19.0)]


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def ease_back(x):
    x = min(max(x, 0.0), 1.0)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ---------------------------------------------------------------- helpers
def text_size(draw, txt, font, stroke=0):
    b = draw.textbbox((0, 0), txt, font=font, stroke_width=stroke)
    return b[2] - b[0], b[3] - b[1], b


def draw_centered(img, y, txt, font, fill, stroke=0, stroke_fill=BLACK, alpha=1.0, dx=0):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tw, th, b = text_size(d, txt, font, stroke)
    d.text(((W - tw) / 2 - b[0] + dx, y - b[1]), txt, font=font, fill=fill,
           stroke_width=stroke, stroke_fill=stroke_fill)
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(layer)
    return th


def pill(img, cx, y, txt, font, bg, fg, pad=(34, 18), alpha=1.0, dy=0):
    d = ImageDraw.Draw(img)
    tw, th, b = text_size(d, txt, font)
    w, h = tw + pad[0] * 2, th + pad[1] * 2
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    x0, y0 = cx - w / 2, y + dy
    ld.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=h / 2, fill=bg + (255,))
    ld.text((x0 + pad[0] - b[0], y0 + pad[1] - b[1]), txt, font=font, fill=fg)
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(layer)
    return h


def wrap(draw, words, font, maxw, stroke):
    lines, cur = [], []
    for w_ in words:
        test = " ".join(cur + [w_])
        if cur and text_size(draw, test, font, stroke)[0] > maxw:
            lines.append(cur)
            cur = [w_]
        else:
            cur.append(w_)
    if cur:
        lines.append(cur)
    return lines


CAP_FONT = F("Montserrat-Black.ttf", 66)


def caption(img, txt, hl, t_in, t):
    """Legenda em caixa alta, com palavras-chave em amarelo e entrada em pop."""
    words = txt.upper().split()
    d = ImageDraw.Draw(img)
    stroke = 7
    lines = wrap(d, words, CAP_FONT, 900, stroke)
    p = ease_back((t - t_in) / 0.22)
    scale = 0.75 + 0.25 * p
    layer = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    lh = 86
    y = (420 - lh * len(lines)) / 2
    space = text_size(ld, " ", CAP_FONT)[0] - 2
    for line in lines:
        widths = [text_size(ld, w_, CAP_FONT, stroke)[0] for w_ in line]
        x = (W - (sum(widths) + space * (len(line) - 1))) / 2
        for w_, ww in zip(line, widths):
            col = YELLOW if w_ in hl else WHITE
            b = ld.textbbox((0, 0), w_, font=CAP_FONT, stroke_width=stroke)
            ld.text((x - b[0], y), w_, font=CAP_FONT, fill=col,
                    stroke_width=stroke, stroke_fill=BLACK)
            x += ww + space
        y += lh
    if scale != 1:
        nw, nh = int(W * scale), int(420 * scale)
        layer = layer.resize((nw, nh), Image.LANCZOS)
    a = min(1.0, (t - t_in) / 0.12)
    layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
    img.alpha_composite(layer, (int((W - layer.width) / 2), int(1330 + (420 - layer.height) / 2)))


def vignette():
    y = np.linspace(-1, 1, H)[:, None]
    x = np.linspace(-1, 1, W)[None, :]
    r = np.sqrt(x ** 2 * 0.6 + y ** 2)
    a = np.clip((r - 0.55) / 0.6, 0, 1) ** 1.6 * 200
    top = np.clip(1 - (np.linspace(0, 1, H)[:, None] / 0.18), 0, 1) * 150
    bot = np.clip((np.linspace(0, 1, H)[:, None] - 0.62) / 0.38, 0, 1) ** 1.3 * 190
    alpha = np.clip(np.maximum(np.maximum(a, top), bot), 0, 255).astype(np.uint8)
    alpha = np.broadcast_to(alpha, (H, W))
    v = np.zeros((H, W, 4), np.uint8)
    v[..., 3] = alpha
    return Image.fromarray(v, "RGBA")


VIG = vignette()


def dark_bg(t):
    """Fundo preto com grade sutil e faixas diagonais amarelas em movimento."""
    img = Image.new("RGBA", (W, H), (8, 8, 8, 255))
    d = ImageDraw.Draw(img)
    for gx in range(0, W + 1, 90):
        d.line([(gx, 0), (gx, H)], fill=(22, 22, 22, 255), width=2)
    off = int((t * 60) % 90)
    for gy in range(-90 + off, H + 1, 90):
        d.line([(0, gy), (W, gy)], fill=(22, 22, 22, 255), width=2)
    # faixa zebrada (fita de sinalização) no topo e na base
    for yb in (0, H - 36):
        d.rectangle((0, yb, W, yb + 36), fill=YELLOW + (255,))
        sh = int((t * 120) % 72)
        for k in range(-2, W // 72 + 3):
            x0 = k * 72 + sh
            d.polygon([(x0, yb + 36), (x0 + 36, yb + 36), (x0 + 72, yb), (x0 + 36, yb)],
                      fill=(15, 15, 15, 255))
    return img


# ---------------------------------------------------------------- assets
logo_full = Image.open(os.path.join(A, "logo.jpg")).convert("RGB")
# remove o fundo preto do logo (vira alpha) para assentar sobre qualquer fundo
la = np.asarray(logo_full).astype(np.float32)
lum = la.max(axis=2)
alpha = np.clip((lum - 18) * 3.0, 0, 255).astype(np.uint8)
logo = Image.fromarray(np.dstack([la.astype(np.uint8), alpha]), "RGBA")
logo = logo.crop(logo.getbbox())

mascot = Image.open(os.path.join(A, "mascote.webp")).convert("RGBA")
# recorte só do personagem + cidade, sem o texto inferior da arte
mascot = mascot.crop((0, 0, 512, 420))
mascot_mask = Image.new("L", mascot.size, 0)
ImageDraw.Draw(mascot_mask).rounded_rectangle((0, 0, mascot.width, mascot.height), 48, fill=255)

cert = Image.open(os.path.join(A, "certificado.jpg")).convert("RGB").rotate(90, expand=True)
cert = cert.crop((40, 20, cert.width - 40, cert.height - 20))

f_badge = F("Montserrat-ExtraBold.ttf", 38)
f_h1 = F("Anton.ttf", 150)
f_h2 = F("Anton.ttf", 96)
f_sub = F("Montserrat-Bold.ttf", 44)
f_small = F("Montserrat-Bold.ttf", 36)


# ---------------------------------------------------------------- video io
def reader(path, start, dur, w, h):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", path,
           "-vf", f"fps={FPS},scale={w}:{h}:flags=lanczos,setsar=1",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    last = None
    while True:
        buf = p.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        last = Image.frombytes("RGB", (w, h), buf)
        yield last
    while True:  # se faltar quadro no fim, repete o último
        yield last


def grade(frame):
    """Leve correção de cor: mais contraste e saturação, tom levemente quente."""
    a = np.asarray(frame).astype(np.float32) / 255.0
    a = np.clip((a - 0.5) * 1.12 + 0.5 + 0.01, 0, 1)
    g = a.mean(axis=2, keepdims=True)
    a = np.clip(g + (a - g) * 1.18, 0, 1)
    a[..., 0] *= 1.02
    a[..., 2] *= 0.97
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


# ---------------------------------------------------------------- scenes
def scene_intro(t):
    img = dark_bg(t)
    # logo entra com zoom
    p = ease_back(t / 0.7)
    lw = int(900 * (0.6 + 0.4 * p))
    lg = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    a = min(1, t / 0.35)
    lg.putalpha(lg.getchannel("A").point(lambda v: int(v * a)))
    img.alpha_composite(lg, ((W - lg.width) // 2, 470 - lg.height // 2))
    # chamada
    if t > 0.6:
        q = ease_out((t - 0.6) / 0.5)
        pill(img, W // 2, 790, "TREINAMENTO NA PRÁTICA", f_badge, YELLOW, BLACK, alpha=q,
             dy=int(40 * (1 - q)))
    if t > 0.9:
        q = ease_out((t - 0.9) / 0.5)
        draw_centered(img, 930 + int(60 * (1 - q)), "NR 33", f_h1, WHITE, alpha=q)
    if t > 1.15:
        q = ease_out((t - 1.15) / 0.5)
        draw_centered(img, 1110 + int(60 * (1 - q)), "ESPAÇOS CONFINADOS", f_h2, YELLOW, alpha=q)
    if t > 1.5:
        q = ease_out((t - 1.5) / 0.5)
        draw_centered(img, 1250, "Trabalhadores Autorizados e Vigias", f_sub, WHITE, alpha=q)
    # transição: flash amarelo varrendo no fim
    if t > INTRO - 0.3:
        q = ease_in_out((t - (INTRO - 0.3)) / 0.3)
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, int(W * q), H), fill=YELLOW + (255,))
    return img


v1 = None
v2 = None


def video_frame(frame, t_local, dur, label, sub):
    img = grade(frame).convert("RGBA")
    img.alpha_composite(VIG)
    # logo pequeno no canto
    lg = logo.resize((300, int(logo.height * 300 / logo.width)), Image.LANCZOS)
    img.alpha_composite(lg, (60, 110))
    # selo superior
    q = ease_out(t_local / 0.45)
    pill(img, W // 2, 250, label, f_badge, YELLOW, BLACK, alpha=q, dy=int(-30 * (1 - q)))
    if sub:
        draw_centered(img, 345, sub, f_small, WHITE, stroke=4, alpha=q)
    # barra de progresso
    d = ImageDraw.Draw(img)
    d.rectangle((0, H - 14, W, H), fill=(0, 0, 0, 160))
    d.rectangle((0, H - 14, int(W * t_local / dur), H), fill=YELLOW + (255,))
    # sai do flash amarelo
    if t_local < 0.3:
        q = ease_in_out(t_local / 0.3)
        d.rectangle((int(W * q), 0, W, H), fill=YELLOW + (255,))
    return img


def scene_v1(t):
    frame = next(v1)
    img = video_frame(frame, t, V1_OUT - V1_IN, "SIMULADO DE ESPAÇO CONFINADO",
                      "Análise do ambiente antes da atividade")
    tv = V1_IN + t
    for a, b, txt, hl in CAPS:
        if a <= tv < b:
            caption(img, txt, hl, a, tv)
            break
    return img


def scene_v2(t):
    frame = next(v2)
    dur = V2_OUT - V2_IN
    img = video_frame(frame, t, dur, "TEORIA + PRÁTICA", None)
    # texto de apoio (sem fala)
    lines = [("HORA DE COLOCAR", WHITE, 0.2), ("NO PAPEL", YELLOW, 0.45)]
    for i, (txt, col, d0) in enumerate(lines):
        if t > d0:
            q = ease_back((t - d0) / 0.35)
            draw_centered(img, 1330 + i * 120, txt, F("Anton.ttf", int(118 * (0.7 + 0.3 * q))),
                          col, stroke=6, alpha=min(1, (t - d0) / 0.15))
    if t > 1.0:
        q = ease_out((t - 1.0) / 0.5)
        draw_centered(img, 1600, "Cada atividade começa com planejamento", f_small, WHITE,
                      stroke=4, alpha=q)
    if t > dur - 0.35:
        q = ease_in_out((t - (dur - 0.35)) / 0.35)
        ImageDraw.Draw(img).rectangle((0, 0, W, int(H * q)), fill=(8, 8, 8, 255))
    return img


def scene_cert(t):
    img = dark_bg(t + 7)
    # título
    q = ease_out(t / 0.5)
    pill(img, W // 2, 300, "CAPACITAÇÃO CONCLUÍDA", f_badge, YELLOW, BLACK, alpha=q,
         dy=int(-30 * (1 - q)))
    draw_centered(img, 420 + int(40 * (1 - q)), "CERTIFICADO", f_h2, WHITE, alpha=q)
    # certificado com zoom lento + sombra + leve inclinação que endireita
    p = ease_back((t - 0.25) / 0.7) if t > 0.25 else 0
    zoom = 1.0 + 0.06 * ease_in_out(t / CERT)
    cw = int(980 * (0.7 + 0.3 * p) * zoom)
    if cw > 10:
        c = cert.resize((cw, int(cert.height * cw / cert.width)), Image.LANCZOS).convert("RGBA")
        border = 14
        framed = Image.new("RGBA", (c.width + border * 2, c.height + border * 2), YELLOW + (255,))
        framed.alpha_composite(c, (border, border))
        ang = (1 - p) * -8
        framed = framed.rotate(ang, resample=Image.BICUBIC, expand=True)
        shadow = Image.new("RGBA", framed.size, (0, 0, 0, 0))
        shadow.putalpha(framed.getchannel("A").point(lambda v: int(v * 0.7)))
        shadow = shadow.filter(ImageFilter.GaussianBlur(24))
        cx, cy = W // 2, 960
        a = min(1, max(0, (t - 0.25) / 0.25))
        if a < 1:
            framed.putalpha(framed.getchannel("A").point(lambda v: int(v * a)))
            shadow.putalpha(shadow.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(shadow, (cx - shadow.width // 2 + 10, cy - shadow.height // 2 + 24))
        img.alpha_composite(framed, (cx - framed.width // 2, cy - framed.height // 2))
    # pontos-chave
    items = ["NR 33 · Capacitação Inicial", "Carga horária: 16 horas", "SESI Paracatu · Kinross"]
    for i, txt in enumerate(items):
        d0 = 1.2 + i * 0.35
        if t > d0:
            q = ease_out((t - d0) / 0.4)
            y = 1360 + i * 92
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            tw = text_size(ld, txt, f_sub)[0]
            x0 = (W - tw - 70) / 2 + int(-60 * (1 - q))
            ld.ellipse((x0, y + 4, x0 + 46, y + 50), fill=YELLOW + (255,))
            ld.line([(x0 + 12, y + 28), (x0 + 20, y + 37), (x0 + 35, y + 17)], fill=BLACK, width=6)
            ld.text((x0 + 70, y), txt, font=f_sub, fill=WHITE)
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * q)))
            img.alpha_composite(layer)
    if t > 2.6:
        q = ease_out((t - 2.6) / 0.5)
        draw_centered(img, 1660, "Desempenho satisfatório", F("Montserrat-ExtraBold.ttf", 48),
                      YELLOW, alpha=q)
    if t < 0.35:  # sai do preto
        a = 1 - ease_in_out(t / 0.35)
        ov = Image.new("RGBA", (W, H), (8, 8, 8, int(255 * a)))
        img.alpha_composite(ov)
    return img


def scene_outro(t):
    img = dark_bg(t + 14)
    # mascote descendo na corda
    p = ease_back(t / 0.8)
    mw = 620
    m = mascot.resize((mw, int(mascot.height * mw / mascot.width)), Image.LANCZOS)
    mk = mascot_mask.resize(m.size, Image.LANCZOS)
    m.putalpha(mk)
    y_end = 300
    y = int(-m.height + (y_end + m.height) * p)
    bob = int(8 * math.sin(t * 3.0)) if t > 0.8 else 0
    d = ImageDraw.Draw(img)
    img.alpha_composite(m, ((W - mw) // 2, y + bob))
    d.rounded_rectangle(((W - mw) // 2 - 6, y + bob - 6, (W + mw) // 2 + 6, y + bob + m.height + 6),
                        radius=52, outline=YELLOW + (255,), width=6)
    # logo
    if t > 0.6:
        q = ease_out((t - 0.6) / 0.5)
        lw = 880
        lg = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
        lg.putalpha(lg.getchannel("A").point(lambda v: int(v * q)))
        img.alpha_composite(lg, ((W - lw) // 2, 1030 + int(50 * (1 - q))))
    if t > 1.1:
        q = ease_out((t - 1.1) / 0.5)
        draw_centered(img, 1440, "Segurança em cada ancoragem.", f_sub, WHITE, alpha=q)
    if t > 1.5:
        q = ease_back((t - 1.5) / 0.45)
        pill(img, W // 2, 1560, "SIGA E COMPARTILHE", F("Montserrat-Black.ttf", 46), YELLOW, BLACK,
             pad=(44, 24), alpha=min(1, (t - 1.5) / 0.2), dy=int(30 * (1 - q)))
    if t > OUTRO - 0.6:  # fade para preto
        a = ease_in_out((t - (OUTRO - 0.6)) / 0.6)
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * a))))
    return img


# ---------------------------------------------------------------- audio
def load_audio(path, start=0.0, dur=None, filt=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start)]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-i", path, "-vn"]
    if filt:
        cmd += ["-af", filt]
    cmd += ["-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def envelope(n, ranges, fade=0.08):
    t = np.arange(n) / SR
    e = np.zeros(n, np.float32)
    for a, b in ranges:
        up = np.clip((t - a) / fade, 0, 1)
        dn = np.clip((b - t) / fade, 0, 1)
        e = np.maximum(e, np.minimum(up, dn))
    return e


def build_audio(path):
    n = int(TOTAL * SR)
    mix = np.zeros((n, 2), np.float32)

    music = load_audio(os.path.join(A, "music.mp3"), 0, TOTAL + 1)[:n]
    music = np.pad(music, ((0, n - len(music)), (0, 0)))
    t = np.arange(n) / SR
    # duck da música durante a fala do instrutor
    duck = np.ones(n, np.float32) * 0.85
    speech_abs = [(T_V1 + a - V1_IN, T_V1 + b - V1_IN) for a, b in V1_SPEECH]
    sp = envelope(n, speech_abs, fade=0.35)
    duck = duck * (1 - sp) + 0.16 * sp
    duck *= np.clip(t / 0.4, 0, 1)                     # fade in
    duck *= np.clip((TOTAL - t) / 1.6, 0, 1)            # fade out
    mix += music * duck[:, None]

    voice = load_audio(os.path.join(A, "video1.mp4"), V1_IN, V1_OUT - V1_IN,
                       "highpass=f=120,lowpass=f=7500,afftdn=nf=-30,"
                       "acompressor=threshold=-24dB:ratio=3:attack=10:release=200,"
                       "loudnorm=I=-16:TP=-2:LRA=9")
    m = len(voice)
    gate = envelope(m, [(a - V1_IN, b - V1_IN) for a, b in V1_SPEECH])
    s0 = int(T_V1 * SR)
    end = min(n, s0 + m)
    mix[s0:end] += voice[:end - s0] * gate[:end - s0, None] * 1.25

    peak = np.abs(mix).max()
    if peak > 0.95:
        mix *= 0.95 / peak
    with open(path, "wb") as fh:
        fh.write(mix.astype(np.float32).tobytes())


# ---------------------------------------------------------------- render
def main():
    global v1, v2
    v1 = reader(os.path.join(A, "video1.mp4"), V1_IN, V1_OUT - V1_IN, W, H)
    v2 = reader(os.path.join(A, "video2.mp4"), V2_IN, V2_OUT - V2_IN, W, H)

    audio_path = OUT + ".f32"
    build_audio(audio_path)

    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", audio_path,
        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-level", "4.1", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT,
    ], stdin=subprocess.PIPE)

    nframes = int(round(TOTAL * FPS))
    for i in range(nframes):
        t = i / FPS
        if t < T_V1:
            img = scene_intro(t)
        elif t < T_V2:
            img = scene_v1(t - T_V1)
        elif t < T_CERT:
            img = scene_v2(t - T_V2)
        elif t < T_OUTRO:
            img = scene_cert(t - T_CERT)
        else:
            img = scene_outro(t - T_OUTRO)
        enc.stdin.write(img.convert("RGB").tobytes())
        if i % 60 == 0:
            print(f"{i}/{nframes}", flush=True)
    enc.stdin.close()
    enc.wait()
    os.remove(audio_path)
    print("ok", OUT, f"{TOTAL:.1f}s")


if __name__ == "__main__":
    main()
