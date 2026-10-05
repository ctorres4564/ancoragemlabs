# Reel NR 33 – Ancoragem Labs

**Arquivo final:** `reel_nr33_ancoragemlabs.mp4`: vertical 1080x1920, 30 fps, 40 s, H.264 + AAC. Serve para Reels do Instagram e do Facebook.

## Roteiro
| Tempo | Cena |
|---|---|
| 0–3 s | Abertura: logo Ancoragem Labs, "NR 33 · Espaços Confinados" |
| 3–22 s | video1: instrutora explicando a RT no simulado, com legendas (fala original + música baixa) |
| 22–28 s | video2: elaboração no papel, "Hora de colocar no papel" (só música) |
| 28–34,5 s | Certificado NR 33 (SESI Paracatu / Kinross, 16 h) |
| 34,5–40 s | Encerramento: mascote + logo + "Siga e compartilhe" |

O áudio original só toca nos trechos com fala transcrita do video1. O resto do áudio original fica mudo, para que nenhuma fala fora do roteiro entre no reel (como o "pra cima caveira").

## Legenda sugerida para o post
> Treinamento na prática! 🦺
> Capacitação NR 33 – Espaços Confinados (Trabalhadores Autorizados e Vigias): análise do ambiente, elaboração da RT e certificação pelo SESI Paracatu.
> Segurança em cada ancoragem. ⚓
>
> #NR33 #EspaçosConfinados #SegurançaDoTrabalho #TrabalhoEmAltura #AncoragemLabs #VerticalEngineering #Paracatu

## Regerar
```
pip install pillow numpy
python3 build_reel.py assets reel_nr33_ancoragemlabs.mp4
```
Precisa de ffmpeg. As fontes Montserrat e Anton (OFL) ficam em `assets/fonts/`.
