# launcher/ui/theme.py
# Fonte única de cores, fontes e tamanhos — não duplicar em outros arquivos de UI.

from PySide6.QtGui import QFont

# ── Paleta de cores ───────────────────────────────────────────────────────────
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

# Aliases novos (usados em game_card e sidebar)
STATUS_VERDE   = "#1a7a3a"
STATUS_LARANJA = "#c97a00"

# Aliases antigos mantidos para não quebrar código existente
COR_STATUS_OK  = STATUS_VERDE
COR_STATUS_OUT = STATUS_LARANJA

# ── Fontes — tuplas (família, tamanho, peso) compatíveis com QFont(*FONTE_X) ─
# Uso: QFont(*FONTE_NOME_JOGO)  →  QFont("Segoe UI", 22, QFont.Bold)

FONTE_NOME_JOGO    = ("Segoe UI", 22, QFont.Bold)   # nome do jogo no card
FONTE_META         = ("Segoe UI", 12)                # versão, rótulos, detalhes
FONTE_DESC         = ("Segoe UI", 13)                # descrição
FONTE_BOTAO        = ("Segoe UI", 15, QFont.Bold)    # botões principais
FONTE_SIDEBAR_NOME = ("Segoe UI", 13, QFont.Bold)    # nome do item na sidebar

# Aliases antigos mantidos para não quebrar código existente
FONTE_CARD_NOME   = FONTE_NOME_JOGO
FONTE_VERSAO      = FONTE_META
FONTE_META_ROTULO = FONTE_META
FONTE_META_VALOR  = ("Segoe UI", 14)
FONTE_DESCRICAO   = FONTE_DESC

# ── Tamanhos de componentes ───────────────────────────────────────────────────
BTN_ALTURA            = 38          # altura dos botões em px
ITEM_SIDEBAR_ALTURA   = 58          # altura de cada item da sidebar em px
ICONE_SIDEBAR_TAMANHO = (38, 38)    # (largura, altura) do ícone na sidebar

# Aliases antigos mantidos
BOTAO_ALTURA   = BTN_ALTURA
SIDEBAR_ICONE_W = 38
SIDEBAR_ICONE_H = 38
SIDEBAR_ITEM_H  = ITEM_SIDEBAR_ALTURA