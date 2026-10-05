#!/usr/bin/env python3
"""Corte de ~15 s do reel v2 para Stories, com cartão final para a enquete.

Uso: python3 build_story.py <pasta_de_assets> <reel_v2.mp4> <saida.mp4>

Trechos do reel (já renderizado):
  A  "Por isso que a gente é profissional ... se qualifica, se capacita."
  B  "nem todo mundo consegue executar ou tá apto, na real, pra fazer." + carimbo APTO
Depois vem um cartão de 3,5 s com a pergunta e área livre para o sticker de enquete.
"""
import os
import subprocess
import sys

ASSETS, REEL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
sys.argv = [sys.argv[0], ASSETS, OUT]
import build_reel_v2 as B  # noqa: E402
from PIL import ImageDraw  # noqa: E402

CUTS = [(B.vt(66.3) - 0.09, B.vt(73.49) + 0.01), (B.vt(78.08) - 0.06, B.vt(82.2) + 0.25)]
CARD = 3.5
W, H, FPS = B.W, B.H, B.FPS


def card_frame(t):
    img = B.dark_bg(t)
    img.alpha_composite(B.logo.resize((620, int(B.logo.height * 620 / B.logo.width))), ((W - 620) // 2, 190))
    q = B.ease_back(t / 0.4)
    B.pill(img, W // 2, 520, "ENQUETE", B.f_badge, B.YELLOW, B.BLACK, alpha=B.clamp(t / 0.2), dy=int(30 * (1 - q)))
    k = B.ease_out((t - 0.15) / 0.45)
    B.draw_centered(img, 640 + int(40 * (1 - k)), "VOCÊ JÁ ENTROU EM UM", B.F("Anton.ttf", 84), B.WHITE, alpha=k)
    B.draw_centered(img, 745 + int(40 * (1 - k)), "ESPAÇO CONFINADO?", B.F("Anton.ttf", 104), B.YELLOW, alpha=k)
    # área livre (y ~ 960-1380) para o sticker de enquete do Instagram/Facebook
    if t > 0.6:
        a = B.ease_out((t - 0.6) / 0.4)
        B.draw_centered(img, 1480, "Responda na enquete acima", B.f_sub, B.WHITE, alpha=a)
        d = ImageDraw.Draw(img)
        cx, y = W // 2, 1440 - int(10 * abs(((t * 2) % 2) - 1))
        d.polygon([(cx - 26, y), (cx + 26, y), (cx, y - 30)], fill=B.YELLOW + (int(255 * a),))
    B.draw_centered(img, 1700, "Segurança em cada ancoragem.", B.f_small, B.YELLOW)
    if t > CARD - 0.4:
        from PIL import Image
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * B.ease_in_out((t - (CARD - 0.4)) / 0.4)))))
    return img


def main():
    tmp = OUT + ".parts"
    os.makedirs(tmp, exist_ok=True)
    # trechos do reel (corta a barra de progresso de 12 px da base)
    parts = []
    for i, (a, b) in enumerate(CUTS):
        p = os.path.join(tmp, f"p{i}.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-i", REEL, "-t", f"{b - a:.3f}",
                        "-vf", f"crop={W}:{H - 12}:0:0,scale={W}:{H},fps={FPS}",
                        "-af", "afade=t=in:d=0.03,afade=t=out:st=%.3f:d=0.05" % (b - a - 0.05),
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", p], check=True)
        parts.append(p)
    # cartão final, com a música continuando de onde o reel estava
    cp = os.path.join(tmp, "card.mp4")
    enc = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-ss", f"{CUTS[-1][1]:.3f}", "-t", str(CARD), "-i", os.path.join(ASSETS, "music.mp3"),
        "-map", "0:v", "-map", "1:a",
        "-af", f"volume=0.75,afade=t=in:d=0.25,afade=t=out:st={CARD - 0.8}:d=0.8",
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", cp,
    ], stdin=subprocess.PIPE)
    for i in range(int(CARD * FPS)):
        enc.stdin.write(card_frame(i / FPS).convert("RGB").tobytes())
    enc.stdin.close()
    enc.wait()
    parts.append(cp)
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", OUT], check=True)
    for p in parts + [lst]:
        os.remove(p)
    os.rmdir(tmp)
    print("ok", OUT)


if __name__ == "__main__":
    main()
