# LDKLauncher — Instruções para o Claude Code

## Contexto do projeto
Migração do LDKLauncher de CustomTkinter para PySide6. O motivo é o resize travado/preto do
Tkinter no Windows — PySide6 redesenha de forma nativa e suave. Um protótipo já validou isso.

## Regras que NUNCA podem ser quebradas

- Migração incremental: uma etapa por vez. Cada etapa termina rodando antes de seguir.
- A camada de lógica (`core/`, `config/`, `shared/`) NÃO se reescreve — só se chama.
  Não "melhorar" código que já funciona e está testado.
- `ui/` só desenha e dispara ações. Quem baixa/extrai/persiste é `core/`.
- Arquivo de UI novo → pode gerar o arquivo inteiro.
  Ajuste em código existente → só o trecho alterado.
- NUNCA commitar: `shared/credentials.py`, `gen_credentials.py`, `logs/`, `dist/`, `build/`.
- Commits em português com prefixos `feat:`, `fix:`, `chore:`.

## Estrutura de pastas

```
LDKLauncher-PySide/
├── shared/
│   ├── drive_utils.py
│   ├── version_json.py
│   └── credentials.py        ← NUNCA commitar
├── launcher/
│   ├── main.py
│   ├── core/                 ← migra INTACTO do projeto antigo
│   ├── ui/                   ← UI nova em PySide6
│   │   ├── main_window.py
│   │   ├── sidebar.py
│   │   ├── game_card.py
│   │   ├── install_dialog.py
│   │   ├── setup_window.py
│   │   ├── splash_screen.py
│   │   └── theme.py          ← fonte única de cores/fontes/tamanhos
│   ├── config/
│   │   ├── settings.py
│   │   └── logger.py
│   └── assets/
└── updater/                  ← migra DEPOIS do launcher estar pronto
```

## Paleta — tudo em theme.py, sem duplicar

```python
COR_BG         = "#07152a"
COR_SIDEBAR    = "#050e1c"
COR_BANNER     = "#0a1929"
COR_BORDA      = "#0c2a4a"
COR_ITEM_ATIVO = "#0d2440"
COR_AZUL       = "#185FA5"
COR_AZUL_CLARO = "#378ADD"
COR_TEXTO      = "#e8f4fd"
COR_MUTED      = "#4a7fa8"
COR_MUTED_DARK = "#2a5a7c"
COR_STATUS_OK  = "#1a7a3a"
COR_STATUS_OUT = "#c97a00"
```

Tamanhos de fonte:
- Nome do jogo no card: 22px bold
- Versão: 12px
- Meta rótulo: 12px | meta valor: 14px
- Descrição: 13px
- Botões: 15px bold | altura: 38px
- Sidebar nome: 13px bold | ícone: 38×38px | item altura: 58px

## Ordem de migração (seguir estritamente)

1. **Janela + navegação** — janela principal, barra de título custom, sidebar, abas
   Biblioteca/Loja, troca de card. Esqueleto sem lógica real. ← ETAPA ATUAL
2. **Um card completo ligado à lógica real** — thumbnail, meta do version.json, botão Jogar.
3. **Fluxos de ação** — download com progresso, instalação, desinstalação, cancelamento.
4. **Janelas secundárias** — InstallDialog, SetupWindow, SplashScreen.
5. **Detalhes** — auto-refresh, indicador de download na sidebar, polimento.
6. **LDKUpdater** — só depois do launcher pronto.

## Decisões técnicas fixas

- Distribuição **onedir** (não onefile) — resolve path com acento no Windows.
- Credenciais Service Account em Base64 em `shared/credentials.py`, geradas por
  `gen_credentials.py` lendo a env `LDK_SERVICE_ACCOUNT`.
- Downloads autenticados via Service Account (Drive API, read-only).
- Lock de instância única via `msvcrt.locking` no `main.py`.
- Auto-update: baixa zip da release, valida com `testzip()`, aplica com robocopy + taskkill
  via .bat escrito com `encoding="utf-8-sig"` (NÃO ascii — quebra com acento).
  O robocopy usa `/XD assets` para preservar thumbnails/ícones cacheados.
- Logs em `<pasta do exe>/logs/launcher.log` via `_get_log_dir()` checando `sys.frozen`.
- Pasta de instalação e exclusões do Defender em `%LOCALAPPDATA%\LDKLauncher\config.json`.
- Auto-refresh do version.json a cada 5 minutos, atualização silenciosa da sidebar.
- `version_local.json` por jogo: `version`, `install_dir`, `last_played`.
- thumbnail_offset salvo como percentual da altura ORIGINAL da imagem.

## Pendências que entram nessa migração

- Indicador de download na sidebar: mini status no rodapé (estilo C) + nome do jogo colorido
  enquanto baixa (estilo Steam). Combinar os dois. Implementar na etapa 5.
- Cancelamento durante hash e extração (hoje só cancela no download):
  - Hash: passar `cancel_event` para `calcular_hash`.
  - ZIP: checar evento no loop por arquivo.
  - RAR: trocar `subprocess.run` por `Popen` para matar o processo.
- Limpeza de resíduos ao cancelar/falhar: deletar zip temporário e pasta parcial.

## Repositório de configuração separado

`version.json` fica em `github.com/juliocmmo/modpack-launcher-config` — repo separado,
não mexer aqui.
