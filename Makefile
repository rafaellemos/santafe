# Makefile instalador do Santafé
#

# == ALTERE AS CONFIGURAÇÕES ABAIXO DE ACORDO COM SEU AMBIENTE =======================

# Define o shell como Bash para permitir o uso de arrays na animação
SHELL = /bin/bash

# Your platform. See PLATS for possible values.
PLAT = none

# Versão do Lua (núcleo) e do Santafé (layout de diretórios)
V   = 5.3
R   = $V.6            # 5.3.6 (versão do Lua)
# Versão "pública" do Santafé para caminhos de bibliotecas e ferramentas.
SFV = 3.0

# Diretórios de instalação padrão
INSTALL_TOP  = /usr/local
INSTALL_BIN  = $(INSTALL_TOP)/bin
INSTALL_INC  = $(INSTALL_TOP)/include
INSTALL_LIB  = $(INSTALL_TOP)/lib
INSTALL_LMOD = $(INSTALL_TOP)/share/santafé/3.0/bibf
INSTALL_CMOD = $(INSTALL_TOP)/lib/santafé/3.0/bibc

# Ferramentas de instalação
INSTALL      = install -p
INSTALL_EXEC = $(INSTALL) -m 0755
INSTALL_DATA = $(INSTALL) -m 0644
MKDIR        = mkdir -p
RM           = rm -f

# Plataformas convenientes
PLATS = aix bsd c89 freebsd generic linux macosx mingw posix solaris

# O que instalar do núcleo Lua/Santafé
# No mingw (Windows) o src/Makefile gera santafe.exe/santafec.exe (sem acento,
# por segurança com PATHEXT/cmd.exe de locales antigos) — nas outras
# plataformas é santafé/santafec. AUTO_PLAT é definido mais abaixo neste
# arquivo, mas como TO_BIN só é expandido quando usado (variável "=", não
# ":="), isso funciona: por essa altura o Make já leu o arquivo inteiro.
TO_BIN = $(if $(filter mingw,$(AUTO_PLAT)),santafe.exe santafec.exe,santafé santafec santafé-sls)
TO_INC = lua.h luaconf.h lualib.h lauxlib.h lua.hpp
TO_LIB = liblua.a
SLS_FONTE = ferramentas/sls/sls.fé
SLS_INICIALIZADOR = ferramentas/sls/santafé-sls
SLS_INSTALADO = $(INSTALL_TOP)/share/santafé/$(SFV)/ferramentas/sls.fé

# `make instalar` continua instalando dependências quando chamado diretamente.
# O instalador guiado (`./instalar.sh`) já as resolve antes, como usuário
# normal, e por isso chama este alvo com DEPENDENCIAS=0.
DEPENDENCIAS ?= 1

# --- CONFIGURAÇÃO DO CARREGADOR E CORES ---
BRANCO        := "\033[1;37m"
AMARELO       := "\033[1;93m"
AMARELO_CLARO := "\033[1;93m"
VERDE         := "\033[1;32m"
VERDE_CLARO   := "\033[1;92m"
AZUL          := "\033[1;34m"
AZUL_CLARO    := "\033[1;94m"
CIANO         := "\033[1;36m"

LARANJA_ESCURO := \033[38;5;208m
RESET          := \033[0m

# Elevação apenas para cópias. Sem sudo, use root ou --prefixo em diretório próprio.
SUDO_OU_SU := $(shell \
    if [ "$$(id -u)" -eq 0 ]; then \
        echo ""; \
    elif command -v sudo >/dev/null 2>&1; then \
        echo sudo; \
    else \
        echo ""; \
    fi)

# Diretório para pkg-config e nome do arquivo .pc
PKGCONFIG_DIR = $(INSTALL_LIB)/pkgconfig
PC_FILE       = santafe.pc

# Diretórios de bibs C que serão compilados/instalados em cbibc/ibibc
BIBC_DIRS = \
    bibs/bibc/arquivo \
    bibs/bibc/rede \
    bibs/bibc/mariadb \
    bibs/bibc/segredo \
    bibs/bibc/tomada

BIBF_FILES = \
    bibs/bibf/bit32.fé \
    bibs/bibf/caminheiro.fé \
    bibs/bibf/carteiro.fé \
    bibs/bibf/correio.fé \
    bibs/bibf/nomes.fé \
    bibs/bibf/imagem.fé \
    bibs/bibf/imagem_jpeg.fé \
    bibs/bibf/imagem_png.fé \
    bibs/bibf/imagem_svg.fé \
    bibs/bibf/pulso.fé \
    bibs/bibf/rpdf.fé \
    bibs/bibf/rpdf_unicode.fé \
    bibs/bibf/turing.fé \
    bibs/bibf/vigia.fé

BIBF_MODULE_FILES = \
    bibs/bibf/correio/antivírus.fé \
    bibs/bibf/correio/autenticação.fé \
    bibs/bibf/correio/depósito.fé \
    bibs/bibf/correio/cd.fé \
    bibs/bibf/correio/dkim.fé \
    bibs/bibf/correio/dmarc.fé \
    bibs/bibf/correio/entrega.fé \
    bibs/bibf/correio/imap.fé \
    bibs/bibf/correio/mariadb.fé \
    bibs/bibf/correio/spf.fé \
    bibs/bibf/correio/triagem.fé \
    bibs/bibf/correio/util.fé \
    bibs/bibf/nomes/acesso.fé \
    bibs/bibf/nomes/autoridade.fé \
    bibs/bibf/nomes/dnssec.fé \
    bibs/bibf/nomes/resolvedor.fé \
    bibs/bibf/nomes/zona.fé \
    bibs/bibf/nomes/LEIA-ME.md

RPDF_FONT_FILES = \
    bibs/bibf/rpdf/fontes/NotoSans-Regular.ttf \
    bibs/bibf/rpdf/fontes/OFL.txt
RPDF_DOC_FILE = bibs/bibf/rpdf/LEIA-ME.md
IMAGEM_DOC_FILE = bibs/bibf/imagem/LEIA-ME.md
PULSO_DOC_FILE = bibs/bibf/pulso/LEIA-ME.md
CORREIO_DOC_FILE = bibs/bibf/correio/LEIA-ME.md
VIGIA_DOC_FILE = bibs/bibf/vigia/LEIA-ME.md
OBSOLETE_BIBF_FILES = \
    png.fé \
    rpdf_imagem.fé \
    correio/armazenamento.fé \
    dns.fé \
    dns/acesso.fé \
    dns/autoritativo.fé \
    dns/recursivo.fé \
    dns/dnssec.fé \
    dns/zona.fé \
    dns/LEIA-ME.md

# Plataforma automática: tenta usar $(PLAT) se não for 'none'; senão detecta via uname
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
  DETECTED_PLAT = macosx
else ifeq ($(UNAME_S),Linux)
  DETECTED_PLAT = linux
else ifneq (,$(findstring MINGW,$(UNAME_S)))
  DETECTED_PLAT = mingw
else ifneq (,$(findstring MSYS,$(UNAME_S)))
  DETECTED_PLAT = mingw
else
  DETECTED_PLAT = linux
endif

AUTO_PLAT = $(if $(filter none,$(PLAT)),$(DETECTED_PLAT),$(PLAT))

# Targets “originais” do Makefile do Lua
all:    $(PLAT)

$(PLATS) clean:
	cd src && $(MAKE) $@

test: testar

testar:
	./testar.sh

testar-correio-mariadb:
	./testes/integracao/testar_correio_mariadb.sh

testar-marco-postal:
	./testes/integracao/testar_marco_postal_1_0.sh

install: cbin
	@bash ferramentas/instalar-arquivos.sh bin "$(INSTALL_TOP)" "$(AUTO_PLAT)"
	@bash ferramentas/instalar-arquivos.sh sls "$(INSTALL_TOP)" "$(AUTO_PLAT)"

uninstall:
	@bash ferramentas/desinstalar-arquivos.sh bin "$(INSTALL_TOP)" "$(AUTO_PLAT)"

local:
	@$(MAKE) install INSTALL_TOP="$(CURDIR)/install"

none:
	@echo "Use './instalar.sh' ou 'make cbin'. Plataformas disponíveis:"
	@echo "   $(PLATS)"

dummy:

echo:
	@echo "PLAT= $(PLAT)"
	@echo "V= $V"
	@echo "R= $R"
	@echo "SFV= $(SFV)"
	@echo "TO_BIN= $(TO_BIN)"

# =============================================================================
#  Alvos de dependências e build separados
# =============================================================================

# detecta distro e tenta instalar dependências mínimas para:
# - compilar o Santafé
# - compilar rede (glib/gio)
# - compilar mariadb (libmariadb/mysqlclient)
ideps:
	@bash instalar.sh --dependencias-apenas

# Compila o núcleo do Santafé (sem instalar)
cbin:
	@printf "$(LARANJA_ESCURO)==> Compilando núcleo Santafé (plataforma $(AUTO_PLAT))...$(RESET)\n"
	@cd src && $(MAKE) $(AUTO_PLAT)
	@$(MAKE) sls

# O SLS é escrito em Santafé e distribuído com um inicializador pequeno. Ele
# sempre chama o executável Santafé instalado ao lado, evitando divergência de
# versão entre o servidor de linguagem e o núcleo.
sls:
	@cp "$(SLS_INICIALIZADOR)" "src/santafé-sls"
	@chmod 0755 "src/santafé-sls"
	@if [ "$(AUTO_PLAT)" != mingw ]; then $(MAKE) -C ferramentas/sls PLAT=$(AUTO_PLAT); fi

# A instalação completa exige todas as bibliotecas. Para somente o núcleo:
# make cbin ibin isls DEPENDENCIAS=0
cbibc:
	@set -e; for d in $(BIBC_DIRS); do $(MAKE) -C "$$d" PLAT=$(AUTO_PLAT); done
	@$(MAKE) pacotes

pacotes:
	@if [ "$(AUTO_PLAT)" != mingw ]; then $(MAKE) -C ferramentas/pacotes PLAT=$(AUTO_PLAT); fi

ipacotes:
	@$(SUDO_OU_SU) bash ferramentas/instalar-arquivos.sh pacotes "$(INSTALL_TOP)" "$(AUTO_PLAT)"

ibin:
	@$(SUDO_OU_SU) bash ferramentas/instalar-arquivos.sh bin "$(INSTALL_TOP)" "$(AUTO_PLAT)"

isls:
	@$(SUDO_OU_SU) bash ferramentas/instalar-arquivos.sh sls "$(INSTALL_TOP)" "$(AUTO_PLAT)"

ibibc:
	@$(SUDO_OU_SU) bash ferramentas/instalar-arquivos.sh c "$(INSTALL_TOP)" "$(AUTO_PLAT)"

ibibf:
	@$(SUDO_OU_SU) bash ferramentas/instalar-arquivos.sh fe "$(INSTALL_TOP)" "$(AUTO_PLAT)"

# Gera e instala o arquivo santafe.pc para pkg-config
instalar-pc:
	@$(SUDO_OU_SU) bash ferramentas/instalar-arquivos.sh pc "$(INSTALL_TOP)" "$(AUTO_PLAT)" "$(VERSION)"

pc: instalar-pc

# =============================================================================
#  Alvos personalizados Santafé (com animação)
# =============================================================================

limpar:
	@printf "$(LARANJA_ESCURO) LIMPANDO --> src$(RESET)\n"
	@cd src && $(MAKE) clean > /dev/null 2>&1
	@$(RM) "src/santafé-sls"
	@# Limpa bibliotecas C também
	@#for d in $(BIBC_DIRS); do if [ -d "$$d" ]; then cd "$$d" && $(MAKE) clean; fi; done
	@for d in $(BIBC_DIRS); do \
	    if [ -d "$$d" ]; then \
	        printf "$(LARANJA_ESCURO) LIMPANDO --> $$d$(RESET)\n"\
	        && $(MAKE) -C $$d clean >/dev/null; \
	    fi;\
	done

	@printf "\r\033[K$(LARANJA_ESCURO)🗑️  Limpeza concluída.$(RESET)\n"

instalar:
	@# 1. Pede senha SUDO antes das cópias em /usr/local (se não for root).
	@if [ "$(SUDO_OU_SU)" = sudo ]; then \
	    printf "$(LARANJA_ESCURO)🔑 Autenticando para instalação...$(RESET)\n"; \
	    sudo -v; \
	fi

	@# 2. Cada etapa permanece em primeiro plano. Isso evita que um bloqueio de
	@# rede, gerenciador de pacotes ou compilador seja mascarado por um `sleep`.
	@if [ "$(DEPENDENCIAS)" = "1" ]; then \
	    $(MAKE) ideps; \
	else \
	    printf "$(LARANJA_ESCURO)==> Dependências já verificadas pelo instalador guiado.$(RESET)\n"; \
	fi
	@$(MAKE) cbin
	@$(MAKE) cbibc
	@$(MAKE) ibin
	@$(MAKE) isls
	@$(MAKE) ibibc
	@$(MAKE) ibibf
	@$(MAKE) ipacotes
	@$(MAKE) instalar-pc
	@printf "$(LARANJA_ESCURO)✅ Santafé compilado e instalado com sucesso!$(RESET)\n"

# Cada destino é absoluto e individual; não há rm recursivo nem limpeza do fonte.
desinstalar-bibs:
	@$(SUDO_OU_SU) bash ferramentas/desinstalar-arquivos.sh bibs "$(INSTALL_TOP)" "$(AUTO_PLAT)"

desinstalar:
	@$(MAKE) desinstalar-bibs
	@$(SUDO_OU_SU) bash ferramentas/desinstalar-arquivos.sh bin "$(INSTALL_TOP)" "$(AUTO_PLAT)"
	@echo "Arquivos conhecidos de Santafé removidos; arquivos de terceiros preservados."


.PHONY: all $(PLATS) clean test testar testar-correio-mariadb install local none dummy echo dist vscode vscode-catalogo sublime sublime-catalogo sublime-repositorio \
        ideps cbin cbibc ibin isls ibibc ibibf instalar-pc pc sls pacotes ipacotes \
        limpar instalar desinstalar



PROJECT := santafe
VERSION := 3.0.0
DISTDIR := $(PROJECT)-$(VERSION)
vscode-catalogo:
	@python3 extensões/vscode/gerar_catalogo.py

vscode: vscode-catalogo
	@python3 extensões/vscode/empacotar.py

sublime-catalogo:
	@python3 extensões/sublime/gerar_catalogo.py

sublime: sublime-catalogo
	@python3 extensões/sublime/empacotar.py

sublime-repositorio: sublime
	@python3 extensões/sublime/gerar_repositorio.py

dist: vscode-catalogo sublime-catalogo
	@echo "Gerando distribuição reproduzível em ./dist a partir da árvore atual..."
	@python3 operação/empacotar-prévia.py --versão $(VERSION)
	@echo "OK: dist/$(DISTDIR).tar.gz"
	@echo "OK: dist/$(DISTDIR).zip"
	@echo "OK: dist/SHA256SUMS"
