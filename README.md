# motion-design — vídeos de motion design só com código

Uma skill para o Claude Code criar vídeos de motion design usando apenas código: **HTML + Playwright + ffmpeg**. Sem After Effects, sem licença do Remotion, sem aplicativo de edição.

Cada fotograma é calculado a partir do tempo, renderizado quadro a quadro, misturado para criar desfoque de movimento e cortado no ritmo da música. Cada efeito sonoro atinge o seu pico medido.

> **Sobre o exemplo.** `examples/howseen-launch` é um filme de 24 s (lançamento fictício de uma ferramenta de visibilidade em IA) escrito para esta skill. Os números e as respostas das IAs são ilustrativos e aparecem na tela como "Example data". É uma recriação da técnica, não o vídeo oficial de lançamento de nenhuma marca. A técnica e o conceito são inspirados no trabalho de [Raphaël Aubry](https://www.linkedin.com/in/raphaelaubry03) / [Howseen](https://howseen.ai/).

## Por que programar em vez de usar um editor?

- **Determinístico:** o filme inteiro é uma única função `seek(t)`. Mesma entrada, mesmos quadros, sempre. Corrija uma cena sem alterar o resto.
- **Gratuito:** Chromium, ffmpeg, Python. Sem licença, sem assinatura.
- **Sincronia rítmica por construção:** as cenas ficam sobre um mapa de batidas, a música entra alinhada ao momento visual-chave e os efeitos sonoros são posicionados pelo pico.
- **Iterável por uma IA:** "deixe as transições mais rápidas", "troque a música", "adicione um cubo 3D na quebra" são só mudanças de código.

## Instalar

1. Copie a skill para o Claude Code:

   ```bash
   mkdir -p ~/.claude/skills && cp -r skill/motion-design ~/.claude/skills/
   ```

2. Dependências Python:

   ```bash
   pip install playwright imageio-ffmpeg numpy pillow && python -m playwright install chromium
   ```

3. No Claude Code, peça um vídeo ou digite `/motion-design`.

## Rodar o exemplo

```bash
cd examples/howseen-launch
python render.py probe 1 8 15 20     # stills rápidos -> probe/sheet.png
python render.py draft               # prévia 540p -> out/video_draft.mp4
python render.py full                # 24 s, 60 fps, desfoque por subquadros -> out/video.mp4
python audio.py                      # música + SFX pelo pico, -14 LUFS -> out/audio.wav
ffmpeg -i out/video.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v libx264 -crf 16 -c:a aac -shortest out/final.mp4
python ../../skill/motion-design/scripts/qc.py out/video.mp4 --cuts 3 14 19
```

- `render.py` sobe sozinho um servidor local (raiz do repositório, porta 8000) se não houver nada rodando. Se você usar o seu, sirva a **raiz do repositório** e abra `/examples/howseen-launch/index.html`.
- **Tempo de render:** cerca de 0,3 s por captura em 1080p. O master (24 s × 60 fps × 8 subquadros) leva em torno de uma hora num notebook. Para revisar, use `--fps 30 --subframes 4`, e `--from/--to` para re-renderizar só a cena corrigida.
- **Assets opcionais:** `python fetch_assets.py` baixa fonte Geist e logos, e lê `assets.json`. Os links de música/SFX do Mixkit ficam em branco de propósito: escolha as faixas e cole as URLs diretas. As URLs de fonte/logos **não foram verificadas** quando o repositório foi criado, porque o ambiente de criação bloqueava esses hosts; se alguma der 404, corrija no `assets.json`. Sem nenhum asset, tudo funciona: fonte do sistema (Inter), chips só com texto, e música/SFX sintetizados como reserva por `audio.py`.

## O que a skill cobre

- **Fluxo:** entradas → mapa de batidas → 4 stills aprovados → render completo → análise de som → áudio → final.
- **Motor** (`skill/motion-design/engine/`): somente `seek(t)` (sem transições CSS nem timers), molas de forma fechada, uma câmera com chave em espaço logarítmico, transferências de elementos compartilhados, inundações de cor que cobrem o canto mais distante, texto mascarado palavra por palavra, e adaptações para `seek(t)` de componentes do 21st.dev (Animated Beam, Border Beam).
- **Render** (`scripts/mdrender.py`): capturas Playwright (fontes prontas, animações pausadas, 2 rAF após cada `seek`), `draft` 540p antes do master, N subquadros por quadro em obturador de 180° (média em numpy, equivalente ao `tmix`, **sem misturar através de um corte seco**), codificação BT.709 de faixa TV, flags do SwiftShader com `WEBGL=1`.
- **QC** (`scripts/qc.py`): detecção de pop e flash de um quadro, verificação de costura de loop em posição e velocidade.
- **Áudio** (`scripts/audio_tools.py`): acha a quebra real pela energia de banda (sem confiar em grade automática), inicia a música para a quebra cair no quadro-chave, posiciona cada SFX pelo pico medido, loudnorm em duas passagens para -14 LUFS.
- **Briefing e referências** (`skill/motion-design/references/`): briefing do diretor, regras anti-"movimento de IA", biblioteca de prompts, tabela sintoma → solução.
- **Assets:** só fontes gratuitas (Mixkit, Pexels, Unsplash, SVGL, Simple Icons, Geist). `scripts/fetch_assets.py` baixa a partir de um manifesto.
- **Modo Remake** (`skill/motion-design/scripts/remake/`): refaz, quadro a quadro, um vídeo de referência **seu**, com tela dividida "original | cópia". Fase 0 extrai quadros, detecta cortes e gera a especificação; Fase 1 é um motor `seek(F)` por número de quadro com filtro de paleta; Fase 2 usa 4 agentes de construção + 1 de áudio (prompts em `AGENTS.md`); Fase 3 renderiza, codifica a tela dividida e verifica sincronia (cortes e latência de áudio). Nunca reutilize a música, a voz ou as fotos de pessoas da referência.
- **Regras de honestidade:** dados ilustrativos aparecem como "Example data"; as legendas permanecem verdadeiras.

## Estado de verificação

Testado neste repositório: probe, render completo (1080p, 30 fps, 2 subquadros), mux com áudio, `audio.py` (quebra detectada e alinhada, -14,0 LUFS), `qc.py` (flash sintético detectado) e as fases 0 e 3 do Remake (3 cortes detectados, split-screen gerado). **Não testados:** downloads de assets, render 60 fps × 8 subquadros completo, e as Fases 1–2 do Remake com agentes (são modelos de prompt e motor, sem execução ponta a ponta).

## Créditos e licenças

Código: MIT. Mídias de terceiros baixadas por `fetch_assets.py` permanecem sob suas licenças (Mixkit, Pexels/Unsplash, OFL para Geist). Logotipos de marcas pertencem aos seus donos.
