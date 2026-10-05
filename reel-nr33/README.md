# Reels NR 33 – Ancoragem Labs

## v2 (atual): depoimento do Gabriel
**Arquivo:** `reel_nr33_depoimento.mp4`: vertical 1080x1920, 30 fps, cerca de 66 s, H.264 + AAC (Instagram e Facebook).

- **Base:** depoimento do Gabriel após o treinamento (`video6`), editado para ~55 s de fala.
- **Inserções:** atividades dos vídeos 1 a 5 (entrada no espaço confinado, imobilização com colar cervical, prancha, remoção da vítima), com motion graphics 2D:
  - título de abertura;
  - painéis "Antes / Durante / Depois";
  - alerta "Atividade crítica";
  - cartões NR 35 + NR 33 e o selo "2 atividades críticas";
  - palavras "Tenso / Desgastante / Insalubre";
  - checklist "Profissional / Treinamento / Qualificação / Capacitação";
  - carimbo "APTO";
  - certificado e encerramento com mascote.
- **Rostos borrados:** todos, com detecção automática (MediaPipe) mais marcações manuais revisadas quadro a quadro (`MANUAL` em `build_reel_v2.py`). O Gabriel também aparece borrado, com crédito na tela.
- **Áudio:** só a voz do depoimento e a trilha Steady Pulse. O áudio original dos vídeos de atividade fica mudo, então não entra nenhuma fala de fundo (nem o "pra cima caveira").

Regerar:
```
pip install pillow numpy opencv-python-headless mediapipe==0.10.14
python3 build_reel_v2.py assets reel_nr33_depoimento.mp4
```

## v1: `reel_nr33_ancoragemlabs.mp4`
Primeira versão (40 s), sem o depoimento. Gerada por `build_reel.py`.

## Legenda sugerida para o post
> "Por isso que a gente é profissional, recebe treinamento, se qualifica, se capacita." 🦺
> Depoimento após a capacitação NR 33 – Espaços Confinados (Trabalhadores Autorizados e Vigias): entrada, resgate e remoção de vítima na prática. Certificação SESI Paracatu.
> Segurança em cada ancoragem. ⚓
>
> #NR33 #EspaçosConfinados #NR35 #TrabalhoEmAltura #SegurançaDoTrabalho #Resgate #AncoragemLabs #VerticalEngineering #Paracatu
