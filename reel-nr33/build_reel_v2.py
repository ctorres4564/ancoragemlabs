#!/usr/bin/env python3
"""Reel v2: depoimento do Gabriel (video6) com inserções das atividades.

Uso: python3 build_reel_v2.py <pasta_de_assets> <saida.mp4> [--preview]

A voz do depoimento conduz o vídeo. As imagens das atividades (video1-5)
entram por cima com motion graphics 2D. Todos os rostos são borrados
(detecção automática + marcações manuais), inclusive o do Gabriel.
O áudio original das atividades fica mudo.
"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from faceblur import FaceBlur  # noqa: E402

A = sys.argv[1]
OUT = sys.argv[2]
PREVIEW = "--preview" in sys.argv
W, H, FPS = 1080, 1920, 30
SR = 48000
SW, SH = 478, 850  # resolução dos vídeos de origem

YELLOW = (248, 186, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
INK = (10, 10, 10)


def F(name, size):
    return ImageFont.truetype(os.path.join(A, "fonts", name), size)


def vid(n):
    return os.path.join(A, f"video{n}.mp4")


# ------------------------------------------------------------ edição da fala
# Trechos do depoimento (segundos no video6). Ficaram de fora a abertura
# ("choveu pra caramba"), hesitações longas e a parte sobre a programação
# do dia seguinte.
SEGS = [
    (11.35, 18.75),   # Foi bom até pra fazer o espaço confinado... aprendizado.
    (22.40, 31.45),   # Os perigos, né? ... o antes, o durante, o depois.
    (32.30, 39.45),   # É um trabalho considerado crítico. E, às vezes, envolve altura
    (42.20, 46.20),   # e o próprio espaço confinado. Então, são duas atividades críticas.
    (51.50, 58.85),   # Então, é muito tenso. Desgastante, insalubre. Não é um local, né?
    (60.60, 62.35),   # Próprio pra gente tá habitando.
    (63.20, 65.20),   # Mas é, sim, faz parte.
    (66.30, 77.15),   # Por isso que a gente é profissional... essas missões que
    (78.08, 82.20),   # nem todo mundo consegue executar ou tá apto, na real, pra fazer.
    (98.40, 99.05),   # Valeu!
]
T0 = 1.1      # a fala começa depois do título de abertura
GAP = 0.12

SEG_OUT = []
_t = T0
for a, b in SEGS:
    SEG_OUT.append(_t)
    _t += (b - a) + GAP
VOICE_END = _t - GAP


def vt(s):
    """Tempo no video6 -> tempo no reel."""
    for (a, b), o in zip(SEGS, SEG_OUT):
        if a - 0.6 <= s <= b + 0.6:
            return o + min(max(s - a, 0), b - a)
    raise ValueError(s)


CERT_START = VOICE_END + 0.5
CERT_DUR = 4.6
OUTRO_START = CERT_START + CERT_DUR
OUTRO_DUR = 4.4
TOTAL = OUTRO_START + OUTRO_DUR

# Legendas (texto revisado a partir do SRT, tempos no video6).
CAPS = [
    (11.35, 13.60, "Foi bom até pra fazer o espaço confinado.", {"ESPAÇO", "CONFINADO."}),
    (14.10, 16.30, "Teve que entrar, resgatar.", {"ENTRAR,", "RESGATAR."}),
    (16.80, 18.75, "Foi legal, foi maneiro o aprendizado.", {"APRENDIZADO."}),
    (22.40, 24.11, "Os perigos, né?", {"PERIGOS,"}),
    (24.11, 26.60, "De trabalhar em espaço confinado.", {"ESPAÇO", "CONFINADO."}),
    (26.70, 31.45, "O antes, o durante, o depois.", {"ANTES,", "DURANTE,", "DEPOIS."}),
    (32.30, 35.90, "É um trabalho considerado crítico.", {"CRÍTICO."}),
    (36.35, 39.45, "E, às vezes, envolve altura", {"ALTURA"}),
    (42.20, 44.20, "e o próprio espaço confinado.", {"ESPAÇO", "CONFINADO."}),
    (44.20, 46.20, "Então, são duas atividades críticas.", {"DUAS", "CRÍTICAS."}),
    (51.50, 54.90, "Então, é muito tenso.", {"TENSO."}),
    (55.00, 57.50, "Desgastante, insalubre.", {"DESGASTANTE,", "INSALUBRE."}),
    (57.50, 58.85, "Não é um local, né?", set()),
    (60.60, 62.35, "Próprio pra gente estar habitando.", set()),
    (63.20, 65.20, "Mas é, sim, faz parte.", {"FAZ", "PARTE."}),
    (66.30, 68.37, "Por isso que a gente é profissional,", {"PROFISSIONAL,"}),
    (68.37, 70.90, "por isso que a gente recebe treinamento.", {"TREINAMENTO."}),
    (70.90, 73.49, "Por isso que a gente se qualifica, se capacita.", {"QUALIFICA,", "CAPACITA."}),
    (73.50, 77.15, "Pra poder estar executando essas missões", {"MISSÕES"}),
    (78.08, 80.31, "que nem todo mundo consegue executar", {"NEM", "TODO", "MUNDO"}),
    (80.31, 82.20, "ou está apto, na real, pra fazer.", {"APTO,"}),
    (98.40, 99.05, "Valeu!", {"VALEU!"}),
]

# ------------------------------------------------------------ plano de cenas
# (início no reel, tipo, parâmetros). Cada cena vai até o início da próxima.
SHOTS = [
    (0.0, "broll", dict(v=3, at=2.0, title=True)),
    (vt(15.40), "broll", dict(v=5, at=39.0)),
    (vt(16.80), "aroll", dict(at=16.8)),
    (vt(22.40), "broll", dict(v=3, at=11.3)),
    (vt(26.70), "triptych", dict()),
    (vt(32.30), "critico", dict(v=1, at=5.0, blur=False)),
    (vt(36.80), "duo", dict(v=3, at=12.0)),
    (vt(51.50), "broll", dict(v=4, at=74.5, words=[(vt(53.5), "TENSO"), (vt(55.1), "DESGASTANTE"),
                                                (vt(56.3), "INSALUBRE")])),
    (vt(57.50), "broll", dict(v=5, at=14.5, blur=False)),  # só mãos e tronco
    (vt(63.20), "broll", dict(v=5, at=19.0, blur=False)),
    (vt(66.30), "checklist", dict(v=4, at=46.5)),
    (vt(73.50), "broll", dict(v=5, at=71.5)),
    (vt(78.08), "broll", dict(v=5, at=101.0, stamp=vt(80.25))),
    (vt(98.40), "aroll", dict(at=98.4)),
    (CERT_START, "cert", dict()),
    (OUTRO_START, "outro", dict()),
]

# Rostos que a detecção automática perde, marcados à mão após revisão
# quadro a quadro: {video: [[(t, cx, cy, w), ...], ...]} em coordenadas
# normalizadas da imagem de origem; a posição é interpolada entre as marcas.
MANUAL = {
    4: [
        # instrutor de capacete azul (colar cervical, 74-80 s)
        [(74.4, 0.84, 0.11, 0.18), (75.5, 0.90, 0.07, 0.18), (76.6, 0.95, 0.06, 0.16),
         (77.1, 0.78, 0.10, 0.20), (77.5, 0.84, 0.11, 0.20), (78.5, 0.87, 0.12, 0.20),
         (80.7, 0.88, 0.12, 0.20)],
        # instrutor de capacete azul (46-54 s)
        [(48.0, 0.97, 0.03, 0.16), (48.5, 0.86, 0.07, 0.20), (49.0, 0.89, 0.07, 0.20),
         (50.5, 0.88, 0.07, 0.20), (51.83, 0.87, 0.10, 0.20), (52.17, 0.88, 0.10, 0.20),
         (52.5, 0.76, 0.12, 0.20), (52.83, 0.66, 0.13, 0.20), (53.17, 0.62, 0.14, 0.20),
         (53.5, 0.72, 0.17, 0.22), (54.0, 0.72, 0.17, 0.22)],
    ],
    5: [
        # vítima na prancha (39-40,5 s)
        [(38.9, 0.03, 0.52, 0.12), (39.4, 0.00, 0.52, 0.12)],
        [(39.8, 0.92, 0.37, 0.13), (40.0, 0.88, 0.37, 0.15), (40.33, 0.55, 0.38, 0.17),
         (40.6, 0.50, 0.40, 0.17)],
        # equipe levantando a prancha (71,5-75,3 s)
        [(71.4, 0.95, 0.38, 0.16), (71.83, 0.75, 0.30, 0.18), (72.0, 0.71, 0.32, 0.18),
         (72.5, 0.80, 0.36, 0.18), (72.67, 0.80, 0.36, 0.18), (72.83, 0.58, 0.38, 0.18),
         (73.17, 0.60, 0.37, 0.18), (73.5, 0.66, 0.42, 0.18), (75.4, 0.66, 0.44, 0.18)],
        [(71.8, 0.55, 0.25, 0.16), (72.0, 0.45, 0.27, 0.17), (72.5, 0.25, 0.33, 0.17),
         (73.0, 0.20, 0.33, 0.17), (73.5, 0.20, 0.41, 0.17), (75.4, 0.22, 0.42, 0.17)],
        [(74.2, 0.42, 0.16, 0.10), (75.4, 0.42, 0.16, 0.10)],
        [(73.3, 0.50, 0.37, 0.14), (75.4, 0.50, 0.38, 0.14)],
        # vítima (84-86 s)
        [(83.9, 0.40, 0.40, 0.14), (85.8, 0.42, 0.40, 0.14)],
        # vítima sendo carregada (101-102 s)
        [(100.9, 0.35, 0.02, 0.14), (101.33, 0.45, 0.07, 0.15), (101.7, 0.50, 0.14, 0.15)],
    ],
}


def manual_boxes(n, t):
    out = []
    for track in MANUAL.get(n, []):
        if not (track[0][0] <= t <= track[-1][0]):
            continue
        for (ta, xa, ya, wa), (tb, xb, yb, wb) in zip(track, track[1:] + [track[-1]]):
            if ta <= t <= tb:
                k = 0 if tb == ta else (t - ta) / (tb - ta)
                w = wa + (wb - wa) * k
                out.append((xa + (xb - xa) * k, ya + (yb - ya) * k, w, w * SW / SH))
                break
    return out

# ------------------------------------------------------------ easing
def clamp(x):
    return min(max(x, 0.0), 1.0)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def ease_back(x):
    x = clamp(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ------------------------------------------------------------ fontes
f_badge = F("Montserrat-ExtraBold.ttf", 38)
f_h1 = F("Anton.ttf", 150)
f_h2 = F("Anton.ttf", 104)
f_h3 = F("Anton.ttf", 80)
f_sub = F("Montserrat-Bold.ttf", 44)
f_small = F("Montserrat-Bold.ttf", 34)
CAP_FONT = F("Montserrat-Black.ttf", 64)


def fade_layer(layer, a):
    if a < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
    return layer


def text_size(draw, txt, font, stroke=0):
    b = draw.textbbox((0, 0), txt, font=font, stroke_width=stroke)
    return b[2] - b[0], b[3] - b[1], b


def draw_centered(img, y, txt, font, fill, stroke=0, stroke_fill=BLACK, alpha=1.0, dx=0):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tw, th, b = text_size(d, txt, font, stroke)
    d.text(((img.width - tw) / 2 - b[0] + dx, y - b[1]), txt, font=font, fill=fill,
           stroke_width=stroke, stroke_fill=stroke_fill)
    img.alpha_composite(fade_layer(layer, alpha))
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
    img.alpha_composite(fade_layer(layer, alpha))
    return h


def check_icon(d, x, y, s, bg=YELLOW, fg=BLACK):
    d.ellipse((x, y, x + s, y + s), fill=bg + (255,))
    d.line([(x + s * .26, y + s * .52), (x + s * .43, y + s * .70), (x + s * .76, y + s * .33)],
           fill=fg + (255,), width=max(3, int(s * .13)), joint="curve")


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


def caption(img, txt, hl, t_in, t, y_top=1400):
    words = txt.upper().split()
    d = ImageDraw.Draw(img)
    stroke = 7
    lines = wrap(d, words, CAP_FONT, 900, stroke)
    p = ease_back((t - t_in) / 0.22)
    scale = 0.78 + 0.22 * p
    LH = 84
    box_h = 380
    layer = Image.new("RGBA", (W, box_h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    y = (box_h - LH * len(lines)) / 2
    space = text_size(ld, " ", CAP_FONT)[0] - 2
    for line in lines:
        widths = [text_size(ld, w_, CAP_FONT, stroke)[0] for w_ in line]
        x = (W - (sum(widths) + space * (len(line) - 1))) / 2
        for w_, ww in zip(line, widths):
            col = YELLOW if w_ in hl else WHITE
            b = ld.textbbox((0, 0), w_, font=CAP_FONT, stroke_width=stroke)
            ld.text((x - b[0], y), w_, font=CAP_FONT, fill=col, stroke_width=stroke, stroke_fill=BLACK)
            x += ww + space
        y += LH
    if scale != 1:
        layer = layer.resize((int(W * scale), int(box_h * scale)), Image.LANCZOS)
    fade_layer(layer, min(1.0, (t - t_in) / 0.12))
    img.alpha_composite(layer, (int((W - layer.width) / 2), int(y_top + (box_h - layer.height) / 2)))


def make_vignette():
    yy = np.linspace(0, 1, H)[:, None]
    x = np.linspace(-1, 1, W)[None, :]
    r = np.sqrt(x ** 2 * 0.6 + ((yy - 0.5) * 2) ** 2)
    a = np.clip((r - 0.55) / 0.6, 0, 1) ** 1.6 * 170
    top = np.clip(1 - yy / 0.16, 0, 1) * 140
    bot = np.clip((yy - 0.62) / 0.38, 0, 1) ** 1.3 * 200
    alpha = np.broadcast_to(np.clip(np.maximum(np.maximum(a, top), bot), 0, 255).astype(np.uint8), (H, W))
    v = np.zeros((H, W, 4), np.uint8)
    v[..., 3] = alpha
    return Image.fromarray(v, "RGBA")


VIG = make_vignette()


def tape(d, y, t, h=36):
    d.rectangle((0, y, W, y + h), fill=YELLOW + (255,))
    sh = int((t * 120) % (2 * h))
    for k in range(-2, W // (2 * h) + 3):
        x0 = k * 2 * h + sh
        d.polygon([(x0, y + h), (x0 + h, y + h), (x0 + 2 * h, y), (x0 + h, y)], fill=(15, 15, 15, 255))


def dark_bg(t):
    img = Image.new("RGBA", (W, H), (8, 8, 8, 255))
    d = ImageDraw.Draw(img)
    for gx in range(0, W + 1, 90):
        d.line([(gx, 0), (gx, H)], fill=(22, 22, 22, 255), width=2)
    off = int((t * 60) % 90)
    for gy in range(-90 + off, H + 1, 90):
        d.line([(0, gy), (W, gy)], fill=(22, 22, 22, 255), width=2)
    tape(d, 0, t)
    tape(d, H - 36, t)
    return img


# ------------------------------------------------------------ logo / mascote / certificado
logo_full = Image.open(os.path.join(A, "logo.jpg")).convert("RGB")
_la = np.asarray(logo_full).astype(np.float32)
_alpha = np.clip((_la.max(axis=2) - 18) * 3.0, 0, 255).astype(np.uint8)
logo = Image.fromarray(np.dstack([_la.astype(np.uint8), _alpha]), "RGBA")
logo = logo.crop(logo.getbbox())
logo_small = logo.resize((280, int(logo.height * 280 / logo.width)), Image.LANCZOS)

mascot = Image.open(os.path.join(A, "mascote.webp")).convert("RGBA").crop((0, 0, 512, 420))
mascot_mask = Image.new("L", mascot.size, 0)
ImageDraw.Draw(mascot_mask).rounded_rectangle((0, 0, mascot.width, mascot.height), 48, fill=255)

cert = Image.open(os.path.join(A, "certificado.jpg")).convert("RGB").rotate(90, expand=True)
cert = cert.crop((40, 20, cert.width - 40, cert.height - 20))


# ------------------------------------------------------------ leitura de vídeo com rosto borrado
class Clip:
    """Lê um vídeo a partir de `start`, já com os rostos borrados (res. de origem)."""

    def __init__(self, n, start, blur_faces=True, preroll=0.5):
        self.n = n
        pre = min(preroll, start) if blur_faces else 0
        self.t = start - pre
        cmd = ["ffmpeg", "-v", "error", "-ss", str(start - pre), "-i", vid(n),
               "-vf", f"fps={FPS},scale={SW}:{SH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.fb = FaceBlur() if blur_faces else None
        self.last = None
        for _ in range(int(round(pre * FPS))):  # aquece o rastreador antes do corte
            self.next()

    def next(self):
        buf = self.p.stdout.read(SW * SH * 3)
        if len(buf) == SW * SH * 3:
            fr = np.frombuffer(buf, np.uint8).reshape(SH, SW, 3)
            if self.fb is not None:
                fr = self.fb.apply(fr, extra=manual_boxes(self.n, self.t))
            self.last = fr
        self.t += 1 / FPS
        return self.last

    def close(self):
        try:
            self.p.kill()
        except Exception:
            pass


def to_canvas(fr, t_local, zoom_from=1.0, zoom_to=1.07, dur=6.0, grade=True):
    """Amplia o quadro de origem para 1080x1920 com zoom lento (Ken Burns)."""
    z = zoom_from + (zoom_to - zoom_from) * ease_in_out(t_local / dur)
    big = cv2.resize(fr, (int(W * z), int(H * z)), interpolation=cv2.INTER_LANCZOS4)
    y0 = (big.shape[0] - H) // 2
    x0 = (big.shape[1] - W) // 2
    a = big[y0:y0 + H, x0:x0 + W].astype(np.float32) / 255.0
    if grade:
        a = np.clip((a - 0.5) * 1.1 + 0.5 + 0.01, 0, 1)
        g = a.mean(axis=2, keepdims=True)
        a = np.clip(g + (a - g) * 1.15, 0, 1)
    return Image.fromarray((a * 255).astype(np.uint8)).convert("RGBA")


def heavy_blur(img, k=28, dark=0.45):
    small = img.resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(k / 8))
    out = small.resize((W, H), Image.BILINEAR)
    out.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * dark))))
    return out


def chrome(img, t_local):
    """Elementos fixos sobre o vídeo: vinheta e logo."""
    img.alpha_composite(VIG)
    img.alpha_composite(logo_small, (60, 120))


# ------------------------------------------------------------ áudio (precisa vir antes do waveform)
def load_audio(path, start=0.0, dur=None, filt=None, sr=SR, ch=2):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start)]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-i", path, "-vn"]
    if filt:
        cmd += ["-af", filt]
    cmd += ["-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, ch).copy()


VOICE_FILT = ("highpass=f=90,lowpass=f=9000,afftdn=nf=-28,"
              "acompressor=threshold=-22dB:ratio=3:attack=8:release=180,"
              "loudnorm=I=-15:TP=-1.5:LRA=8")
_voice_src = load_audio(vid(6), 0, None, VOICE_FILT)


def build_voice_track(n):
    v = np.zeros((n, 2), np.float32)
    fade = int(0.03 * SR)
    for (a, b), o in zip(SEGS, SEG_OUT):
        seg = _voice_src[int(a * SR):int(b * SR)].copy()
        ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
        seg[:fade] *= ramp
        seg[-fade:] *= ramp[::-1]
        s0 = int(o * SR)
        v[s0:s0 + len(seg)] += seg[:max(0, n - s0)]
    return v


N_SAMPLES = int(TOTAL * SR)
VOICE = build_voice_track(N_SAMPLES)
_mono = np.abs(VOICE.mean(axis=1))
_hop = SR // FPS
LEVEL = np.array([_mono[i * _hop:(i + 1) * _hop].mean() if i * _hop < len(_mono) else 0
                  for i in range(int(TOTAL * FPS) + 2)])
LEVEL = LEVEL / (np.percentile(LEVEL[LEVEL > 0], 95) + 1e-6)


def level_at(t):
    i = int(t * FPS)
    return float(np.clip(LEVEL[min(i, len(LEVEL) - 1)], 0, 1.4))


# ------------------------------------------------------------ cenas
clips = {}


def get_clip(key, n, start, blur=True):
    if key not in clips:
        clips[key] = Clip(n, start, blur)
    return clips[key]


def scene_broll(t, tl, dur, key, p):
    c = get_clip(key, p["v"], p["at"], p.get("blur", True))
    img = to_canvas(c.next(), tl, dur=max(dur, 3))
    chrome(img, tl)
    if p.get("title"):
        q = ease_out(tl / 0.5)
        out = 1 - ease_in_out((tl - 3.2) / 0.5)
        a = q * out
        if a > 0:
            pill(img, W // 2, 470, "TREINAMENTO NA PRÁTICA", f_badge, YELLOW, BLACK, alpha=a,
                 dy=int(-30 * (1 - q)))
            draw_centered(img, 580 + int(50 * (1 - q)), "NR 33", f_h1, WHITE, stroke=6, alpha=a)
            draw_centered(img, 760 + int(50 * (1 - q)), "ESPAÇO CONFINADO", f_h3, YELLOW, stroke=5, alpha=a)
            draw_centered(img, 880, "Depoimento após o treinamento", f_sub, WHITE, stroke=4, alpha=a)
    words = p.get("words", [])
    for i, (t_w, word) in enumerate(words):
        if t >= t_w:
            q = ease_back((t - t_w) / 0.3)
            fnt = F("Anton.ttf", int(130 * (0.6 + 0.4 * q)))
            col = YELLOW if i % 2 == 0 else WHITE
            draw_centered(img, 560 + i * 165, word, fnt, col, stroke=7, alpha=clamp((t - t_w) / 0.12))
    if p.get("stamp") and t >= p["stamp"]:
        stamp(img, t - p["stamp"])
    return img


def stamp(img, ts):
    """Carimbo "APTO" que bate na tela."""
    q = ease_out(ts / 0.18)
    s = 2.2 - 1.2 * q
    layer = Image.new("RGBA", (620, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((10, 10, 610, 290), radius=30, outline=YELLOW + (255,), width=16)
    fnt = F("Anton.ttf", 170)
    tw, th, b = text_size(d, "APTO", fnt)
    d.text(((620 - tw) / 2 - b[0] + 40, (300 - th) / 2 - b[1]), "APTO", font=fnt, fill=YELLOW + (255,))
    check_icon(d, 50, 95, 110)
    layer = layer.rotate(-8, resample=Image.BICUBIC, expand=True)
    layer = layer.resize((int(layer.width * s), int(layer.height * s)), Image.LANCZOS)
    fade_layer(layer, clamp(ts / 0.1))
    img.alpha_composite(layer, ((W - layer.width) // 2, 760 - layer.height // 2))


def scene_aroll(t, tl, dur, key, p):
    """Gabriel em selfie: rosto totalmente borrado + ondas de voz + crédito."""
    c = get_clip(key, 6, p["at"], blur=False)
    base = to_canvas(c.next(), tl, 1.0, 1.0, grade=False)
    img = heavy_blur(base, k=40, dark=0.35)
    d = ImageDraw.Draw(img)
    tape(d, 0, t, 24)
    # ondas de voz reagindo ao áudio
    lv = level_at(t)
    cx, cy = W // 2, 800
    for i in range(3):
        r = 150 + i * 70 + lv * 60 * (1 + i * 0.4)
        a = int(180 * (1 - i * 0.3))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=YELLOW + (a,), width=6 - i)
    d.ellipse((cx - 130, cy - 130, cx + 130, cy + 130), fill=YELLOW + (255,))
    # ícone de microfone
    d.rounded_rectangle((cx - 34, cy - 80, cx + 34, cy + 20), radius=34, fill=BLACK + (255,))
    d.arc((cx - 60, cy - 40, cx + 60, cy + 50), 0, 180, fill=BLACK + (255,), width=12)
    d.line([(cx, cy + 50), (cx, cy + 80)], fill=BLACK + (255,), width=12)
    d.line([(cx - 34, cy + 82), (cx + 34, cy + 82)], fill=BLACK + (255,), width=12)
    # barras de áudio
    for k in range(17):
        h = 14 + 90 * lv * (0.5 + 0.5 * math.sin(k * 1.7 + t * 11)) * (1 - abs(k - 8) / 10)
        x = cx - 17 * 22 // 2 + k * 22
        d.rounded_rectangle((x, 1080 - h / 2, x + 12, 1080 + h / 2), radius=6, fill=WHITE + (230,))
    # crédito
    q = ease_out(tl / 0.4)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    x0 = 70 - int(80 * (1 - q))
    ld.rectangle((x0, 1190, x0 + 14, 1300), fill=YELLOW + (255,))
    ld.text((x0 + 40, 1186), "GABRIEL", font=F("Anton.ttf", 70), fill=WHITE + (255,))
    ld.text((x0 + 42, 1270), "Trabalhador autorizado · NR 33", font=f_small, fill=YELLOW + (255,))
    img.alpha_composite(fade_layer(layer, q))
    img.alpha_composite(logo_small, (60, 120))
    return img


def panel(img, fr, box, label, q, tl, fy=0.45):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    src = Image.fromarray(fr).convert("RGBA")
    # recorte "cover" do quadro vertical para o painel horizontal
    sc = max(w / src.width, h / src.height) * (1.05 + 0.04 * ease_in_out(tl / 3))
    src = src.resize((int(src.width * sc), int(src.height * sc)), Image.LANCZOS)
    cx, cy = (src.width - w) // 2, int((src.height - h) * fy)
    src = src.crop((cx, cy, cx + w, cy + h))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w, h), 26, fill=255)
    src.putalpha(m)
    dx = int((1 - q) * W)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.alpha_composite(src, (x0 + dx, y0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle((x0 + dx, y0, x1 + dx, y1), 26, outline=YELLOW + (255,), width=6)
    tw = text_size(ld, label, f_badge)[0]
    ld.rounded_rectangle((x0 + dx + 24, y0 + 22, x0 + dx + 24 + tw + 44, y0 + 22 + 66), 33, fill=YELLOW + (255,))
    ld.text((x0 + dx + 46, y0 + 30), label, font=f_badge, fill=BLACK + (255,))
    img.alpha_composite(layer)


def scene_triptych(t, tl, dur, key, p):
    """Antes / durante / depois: três painéis entrando no ritmo da fala."""
    img = dark_bg(t)
    marks = [(vt(26.9), "ANTES", (2, 14.0), 0.06),
             (vt(28.4), "DURANTE", (3, 5.0), 0.45),
             (vt(29.9), "DEPOIS", (5, 84.0), 0.55)]
    top = 300
    ph = 330
    for i, (tm, label, (n, at), fy) in enumerate(marks):
        if t >= tm - 0.05:
            c = get_clip((key, i), n, at, blur=(n != 2))  # video2 só tem mãos e papel
            fr = c.next()
            q = ease_out((t - tm) / 0.45)
            panel(img, fr, (70, top + i * (ph + 30), W - 70, top + i * (ph + 30) + ph), label, q, t - tm, fy)
    img.alpha_composite(logo_small, (60, 120))
    return img


def warn_triangle(d, cx, cy, s, a=255):
    pts = [(cx, cy - s * 0.58), (cx + s * 0.6, cy + s * 0.46), (cx - s * 0.6, cy + s * 0.46)]
    d.polygon(pts, fill=YELLOW + (a,))
    inner = [(cx, cy - s * 0.38), (cx + s * 0.44, cy + s * 0.36), (cx - s * 0.44, cy + s * 0.36)]
    d.polygon(inner, fill=BLACK + (a,))
    d.rounded_rectangle((cx - s * 0.045, cy - s * 0.18, cx + s * 0.045, cy + s * 0.14), s * 0.04, fill=YELLOW + (a,))
    d.ellipse((cx - s * 0.05, cy + s * 0.19, cx + s * 0.05, cy + s * 0.29), fill=YELLOW + (a,))


def scene_critico(t, tl, dur, key, p):
    c = get_clip(key, p["v"], p["at"], p.get("blur", True))
    img = heavy_blur(to_canvas(c.next(), tl, dur=dur), k=16, dark=0.55)
    d = ImageDraw.Draw(img)
    q = ease_back(tl / 0.5)
    s = int(380 * q)
    if s > 10:
        pulse = 1 + 0.04 * math.sin(tl * 8)
        warn_triangle(d, W // 2, 700, s * pulse)
    if tl > 0.35:
        k = ease_out((tl - 0.35) / 0.4)
        draw_centered(img, 960 + int(40 * (1 - k)), "ATIVIDADE", f_h2, WHITE, alpha=k)
        draw_centered(img, 1080 + int(40 * (1 - k)), "CRÍTICA", F("Anton.ttf", 150), YELLOW, alpha=k)
    tape(d, 0, t)
    img.alpha_composite(logo_small, (60, 120))
    return img


def nr_card(img, y, title, nr, q):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0 = 70 + int((1 - q) * -W)
    d.rounded_rectangle((x0, y, x0 + W - 140, y + 230), 30, fill=(12, 12, 12, 235), outline=YELLOW + (255,), width=6)
    d.rounded_rectangle((x0 + 30, y + 40, x0 + 230, y + 190), 22, fill=YELLOW + (255,))
    fnt = F("Anton.ttf", 70)
    tw, th, b = text_size(d, nr, fnt)
    d.text((x0 + 130 - tw / 2 - b[0], y + 115 - th / 2 - b[1]), nr, font=fnt, fill=BLACK + (255,))
    d.text((x0 + 270, y + 52), title, font=F("Anton.ttf", 66), fill=WHITE + (255,))
    d.text((x0 + 272, y + 140), "Atividade crítica", font=f_small, fill=YELLOW + (255,))
    img.alpha_composite(fade_layer(layer, clamp(q * 1.5)))


def scene_duo(t, tl, dur, key, p):
    c = get_clip(key, p["v"], p["at"])
    img = to_canvas(c.next(), tl, dur=dur)
    img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 120)))
    chrome(img, tl)
    q1 = ease_out((t - vt(36.8)) / 0.5)
    nr_card(img, 430, "TRABALHO EM ALTURA", "NR 35", q1)
    if t >= vt(42.6):
        nr_card(img, 700, "ESPAÇO CONFINADO", "NR 33", ease_out((t - vt(42.6)) / 0.5))
    if t >= vt(44.6):
        k = ease_back((t - vt(44.6)) / 0.4)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle((170, 980, W - 170, 1130), 75, fill=YELLOW + (255,))
        fnt = F("Anton.ttf", 84)
        txt = "2 ATIVIDADES CRÍTICAS"
        tw, th, b = text_size(d, txt, fnt)
        d.text(((W - tw) / 2 - b[0], 1055 - th / 2 - b[1]), txt, font=fnt, fill=BLACK + (255,))
        sc = 0.6 + 0.4 * k
        layer = layer.crop((0, 940, W, 1170))
        layer = layer.resize((int(W * sc), int(230 * sc)), Image.LANCZOS)
        img.alpha_composite(fade_layer(layer, clamp((t - vt(44.6)) / 0.1)),
                            ((W - layer.width) // 2, 1055 - layer.height // 2))
    return img


def scene_checklist(t, tl, dur, key, p):
    c = get_clip(key, p["v"], p["at"])
    img = to_canvas(c.next(), tl, dur=dur)
    img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 110)))
    chrome(img, tl)
    items = [(vt(67.6), "PROFISSIONAL"), (vt(69.1), "TREINAMENTO"),
             (vt(71.9), "QUALIFICAÇÃO"), (vt(72.6), "CAPACITAÇÃO")]
    for i, (tm, txt) in enumerate(items):
        if t >= tm:
            q = ease_back((t - tm) / 0.35)
            y = 420 + i * 200
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            x0 = 110 + int((1 - q) * -500)
            d.rounded_rectangle((x0, y, x0 + 860, y + 160), 80, fill=(12, 12, 12, 225))
            check_icon(d, x0 + 22, y + 22, 116)
            d.text((x0 + 170, y + 26), txt, font=F("Anton.ttf", 92), fill=WHITE + (255,))
            img.alpha_composite(fade_layer(layer, clamp((t - tm) / 0.15)))
    return img


def scene_cert(t, tl, dur, key, p):
    img = dark_bg(t + 7)
    q = ease_out(tl / 0.5)
    pill(img, W // 2, 300, "CAPACITAÇÃO CONCLUÍDA", f_badge, YELLOW, BLACK, alpha=q, dy=int(-30 * (1 - q)))
    draw_centered(img, 420 + int(40 * (1 - q)), "CERTIFICADO", f_h2, WHITE, alpha=q)
    pp = ease_back((tl - 0.2) / 0.7) if tl > 0.2 else 0
    zoom = 1.0 + 0.05 * ease_in_out(tl / dur)
    cw = int(980 * (0.7 + 0.3 * pp) * zoom)
    if cw > 10:
        c = cert.resize((cw, int(cert.height * cw / cert.width)), Image.LANCZOS).convert("RGBA")
        border = 14
        framed = Image.new("RGBA", (c.width + border * 2, c.height + border * 2), YELLOW + (255,))
        framed.alpha_composite(c, (border, border))
        framed = framed.rotate((1 - pp) * -8, resample=Image.BICUBIC, expand=True)
        shadow = Image.new("RGBA", framed.size, (0, 0, 0, 0))
        shadow.putalpha(framed.getchannel("A").point(lambda v: int(v * 0.7)))
        shadow = shadow.filter(ImageFilter.GaussianBlur(24))
        a = clamp((tl - 0.2) / 0.25)
        fade_layer(framed, a)
        fade_layer(shadow, a)
        img.alpha_composite(shadow, (W // 2 - shadow.width // 2 + 10, 960 - shadow.height // 2 + 24))
        img.alpha_composite(framed, (W // 2 - framed.width // 2, 960 - framed.height // 2))
    items = ["NR 33 · Capacitação Inicial", "Carga horária: 16 horas", "SESI Paracatu · Kinross"]
    for i, txt in enumerate(items):
        d0 = 0.9 + i * 0.3
        if tl > d0:
            k = ease_out((tl - d0) / 0.4)
            y = 1360 + i * 92
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            tw = text_size(ld, txt, f_sub)[0]
            x0 = (W - tw - 70) / 2 + int(-60 * (1 - k))
            check_icon(ld, x0, y + 4, 46)
            ld.text((x0 + 70, y), txt, font=f_sub, fill=WHITE)
            img.alpha_composite(fade_layer(layer, k))
    if tl > 2.2:
        draw_centered(img, 1660, "Desempenho satisfatório", F("Montserrat-ExtraBold.ttf", 48), YELLOW,
                      alpha=ease_out((tl - 2.2) / 0.5))
    if tl < 0.3:
        img.alpha_composite(Image.new("RGBA", (W, H), (8, 8, 8, int(255 * (1 - ease_in_out(tl / 0.3))))))
    return img


def scene_outro(t, tl, dur, key, p):
    img = dark_bg(t + 14)
    pp = ease_back(tl / 0.8)
    mw = 600
    m = mascot.resize((mw, int(mascot.height * mw / mascot.width)), Image.LANCZOS)
    m.putalpha(mascot_mask.resize(m.size, Image.LANCZOS))
    y = int(-m.height + (300 + m.height) * pp)
    bob = int(8 * math.sin(tl * 3.0)) if tl > 0.8 else 0
    img.alpha_composite(m, ((W - mw) // 2, y + bob))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(((W - mw) // 2 - 6, y + bob - 6, (W + mw) // 2 + 6, y + bob + m.height + 6),
                        radius=52, outline=YELLOW + (255,), width=6)
    if tl > 0.5:
        k = ease_out((tl - 0.5) / 0.5)
        lg = logo.resize((880, int(logo.height * 880 / logo.width)), Image.LANCZOS)
        img.alpha_composite(fade_layer(lg, k), ((W - 880) // 2, 1010 + int(50 * (1 - k))))
    if tl > 0.9:
        draw_centered(img, 1420, "Segurança em cada ancoragem.", f_sub, WHITE, alpha=ease_out((tl - 0.9) / 0.5))
    if tl > 1.3:
        k = ease_back((tl - 1.3) / 0.45)
        pill(img, W // 2, 1540, "SIGA E COMPARTILHE", F("Montserrat-Black.ttf", 46), YELLOW, BLACK,
             pad=(44, 24), alpha=clamp((tl - 1.3) / 0.2), dy=int(30 * (1 - k)))
    if tl > dur - 0.6:
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * ease_in_out((tl - (dur - 0.6)) / 0.6)))))
    return img


SCENES = {"broll": scene_broll, "aroll": scene_aroll, "triptych": scene_triptych, "critico": scene_critico,
          "duo": scene_duo, "checklist": scene_checklist, "cert": scene_cert, "outro": scene_outro}


def flash(img, tl):
    """Transição curta: faixa amarela varrendo no início de cada cena."""
    if tl < 0.16:
        q = ease_in_out(tl / 0.16)
        d = ImageDraw.Draw(img)
        x = int(W * q * 1.3) - 260
        d.polygon([(x, 0), (x + 260, 0), (x + 120, H), (x - 140, H)], fill=YELLOW + (255,))


def render_frame(i):
    t = i / FPS
    idx = max(k for k, s in enumerate(SHOTS) if s[0] <= t + 1e-9)
    start, kind, p = SHOTS[idx]
    end = SHOTS[idx + 1][0] if idx + 1 < len(SHOTS) else TOTAL
    tl = t - start
    img = SCENES[kind](t, tl, end - start, idx, p)
    if kind not in ("cert", "outro") and idx > 0:
        flash(img, tl)
    if kind not in ("cert", "outro"):
        # legenda da fala
        for a, b, txt, hl in CAPS:
            ta, tb = vt(a), vt(b)
            if ta <= t < tb:
                y_top = 1420 if kind in ("broll", "aroll", "critico") else 1460
                caption(img, txt, hl, ta, t, y_top=y_top)
                break
        d = ImageDraw.Draw(img)
        d.rectangle((0, H - 12, W, H), fill=(0, 0, 0, 160))
        d.rectangle((0, H - 12, int(W * t / CERT_START), H), fill=YELLOW + (255,))
    # fecha leitores que não serão mais usados
    for k in list(clips):
        kk = k[0] if isinstance(k, tuple) else k
        if kk < idx:
            clips.pop(k).close()
    return img


# ------------------------------------------------------------ mixagem
def build_audio(path):
    n = N_SAMPLES
    t = np.arange(n) / SR
    music = load_audio(os.path.join(A, "music.mp3"), 0, TOTAL + 1)[:n]
    music = np.pad(music, ((0, n - len(music)), (0, 0)))
    # música baixa sob a fala, sobe na abertura e no final
    talk = np.zeros(n, np.float32)
    talk[(t > T0 - 0.4) & (t < VOICE_END + 0.2)] = 1
    k = int(0.4 * SR)
    talk = np.convolve(talk, np.ones(k) / k, mode="same")
    gain = 0.75 * (1 - talk) + 0.13 * talk
    gain *= np.clip(t / 0.3, 0, 1) * np.clip((TOTAL - t) / 1.5, 0, 1)
    mix = music * gain[:, None] + VOICE * 1.0
    peak = np.abs(mix).max()
    if peak > 0.97:
        mix *= 0.97 / peak
    mix.astype(np.float32).tofile(path)


def main():
    print(f"duração {TOTAL:.1f}s, fala termina em {VOICE_END:.1f}s", flush=True)
    audio_path = OUT + ".f32"
    build_audio(audio_path)
    frames = range(int(round(TOTAL * FPS)))
    if PREVIEW:
        os.makedirs(OUT, exist_ok=True)
        sel = [int(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")] \
            if len(sys.argv) > sys.argv.index("--preview") + 1 else list(range(0, len(frames), 45))
        cur = 0
        for i in frames:
            if i > max(sel):
                break
            img = render_frame(i)
            if i in sel:
                img.convert("RGB").resize((360, 640)).save(os.path.join(OUT, f"f{i:05d}.jpg"), quality=85)
        return
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", audio_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-level", "4.1",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", OUT,
    ], stdin=subprocess.PIPE)
    for i in frames:
        enc.stdin.write(render_frame(i).convert("RGB").tobytes())
        if i % 150 == 0:
            print(f"{i}/{len(frames)}", flush=True)
    enc.stdin.close()
    enc.wait()
    os.remove(audio_path)
    print("ok", OUT)


if __name__ == "__main__":
    main()
