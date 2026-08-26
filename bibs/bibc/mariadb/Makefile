# Makefile para a biblioteca mariadb

SHELL := /bin/bash

# --- CONFIGURAÇÃO DO CARREGADOR E CORES ---
BRANCO          := "\033[1;37m"
AMARELO         := "\033[1;93m"
AMARELO_CLARO   := "\033[1;93m"
VERDE           := "\033[1;32m"
VERDE_CLARO     := "\033[1;92m"
AZUL            := "\033[1;34m"
AZUL_CLARO      := "\033[1;94m"
CIANO           := "\033[1;36m"

LARANJA_ESCURO  := \033[38;5;208m
RESET           := \033[0m

# PLAT: linux (padrão), macosx ou mingw. Detecta via uname se não vier do
# Makefile principal (permite rodar "make" direto nesta pasta também).
UNAME_S := $(shell uname -s 2>/dev/null)
ifeq ($(PLAT),)
  ifeq ($(UNAME_S),Darwin)
    PLAT := macosx
  else ifneq (,$(findstring MINGW,$(UNAME_S)))
    PLAT := mingw
  else ifneq (,$(findstring MSYS,$(UNAME_S)))
    PLAT := mingw
  else
    PLAT := linux
  endif
endif

# Inclui cabeçalhos do Santafé/Lua
LUA_INC = ../../../src

# Pacotes necessários (mariadb.c usa GIO, além de GLib puro)
PKGS = gio-2.0 gobject-2.0 glib-2.0

# Flags de MariaDB/MySQL (usa mariadb_config se existir, senão mysql_config;
# no Windows/MSYS2, use o mariadb_config do pacote mingw-w64-*-libmariadb).
# No macOS via Homebrew, "mariadb-connector-c" é keg-only e não entra no PATH,
# então tentamos achar o mariadb_config dentro do prefixo do brew também.
# Homebrew exige macOS Sonoma (14)+; em versões mais antigas o caminho normal
# é MacPorts (prefixo fixo /opt/local, ver instalar.sh), cujo port "mariadb"
# já deixa o mariadb_config em /opt/local/bin.
BREW_MARIADB_PREFIX := $(shell brew --prefix mariadb-connector-c 2>/dev/null)
MARIADB_CONFIG := $(shell command -v mariadb_config 2>/dev/null || \
                     ( [ -n "$(BREW_MARIADB_PREFIX)" ] && echo "$(BREW_MARIADB_PREFIX)/bin/mariadb_config" ) || \
                     ( [ -x /opt/local/bin/mariadb_config ] && echo /opt/local/bin/mariadb_config ) )

MYSQL_CFLAGS = $(shell $(MARIADB_CONFIG) --cflags 2>/dev/null || mysql_config --cflags 2>/dev/null)
MYSQL_LIBS   = $(shell $(MARIADB_CONFIG) --libs   2>/dev/null || mysql_config --libs   2>/dev/null)

# Compilador
CC      = gcc

# CFLAGS: Includes e configurações de compilação
CFLAGS  = -std=c99 -O2 -Wall -fPIC -I$(LUA_INC) \
          $(shell pkg-config --cflags $(PKGS)) \
          $(MYSQL_CFLAGS)

# LIBS: As bibliotecas em si (glib/gio + mariadb/mysql)
LIBS    = $(shell pkg-config --libs $(PKGS)) $(MYSQL_LIBS)

ifeq ($(PLAT),mingw)
  LIBNAME = mariadb.dll
  LDFLAGS = -shared
else ifeq ($(PLAT),macosx)
  LIBNAME = mariadb.so
  # Módulo Lua carregado em runtime pelo santafé host: símbolos lua_*/luaL_*
  # só existem no executável, não aqui (equivalente ao -Wl,-E do Linux).
  LDFLAGS = -bundle -undefined dynamic_lookup
else
  LIBNAME = mariadb.so
  LDFLAGS = -shared
endif

# Arquivos Fontes
SRCS = mariadb.c
OBJS = $(SRCS:.c=.o)

# --- CONTROLE DE VERBOSIDADE ---
Q ?=

all: $(LIBNAME)

# Regra de Linkagem
$(LIBNAME): $(OBJS)
	$(Q)$(CC) $(LDFLAGS) -o $@ $(OBJS) $(LIBS)

# Regra de Compilação de Objetos
.c.o:
	$(Q)$(CC) $(CFLAGS) -c $< -o $@

install:
	@mkdir -p $(INSTALL_BIN)
	@install -m 755 $(LIBNAME) $(INSTALL_BIN)/$(LIBNAME)

uninstall:
	@rm -f $(OBJS) $(LIBNAME)
	@rm -f $(INSTALL_BIN)/$(LIBNAME)

clean:
	@rm -f $(OBJS) $(LIBNAME)


limpar:
	@rm -f $(OBJS) $(LIBNAME)
	@printf "\r\033[K$(LARANJA_ESCURO)🗑️  Limpeza concluída.$(RESET)\n"

# Instalação
PREFIX      = /usr/local
INSTALL_BIN = $(PREFIX)/lib/santafé/1.0/bibc

instalar:
	@# 1. Roda o make all silenciado com Spinner animado
	@($(MAKE) all Q=@) > /dev/null 2>&1 & pid=$$!; \
	spin_chars=( "◉       " " ◉      " "  ◉     " "   ◉    " "    ◉   " "     ◉  " "      ◉ " "       ◉"); \
	colors=( $(AZUL) $(VERDE) $(CIANO) $(VERDE_CLARO) $(AZUL_CLARO) $(AMARELO) $(AMARELO_CLARO) $(BRANCO) ); \
	delay=0.05; \
	tput civis; \
	while kill -0 $$pid 2>/dev/null; do \
		for i in 0 1 2 3 4 5 6 7 6 5 4 3 2 1 0; do \
			kill -0 $$pid 2>/dev/null || break; \
			idx=$$(( i % 8 )); \
			current_color=$${colors[$$idx]}; \
			current_char=$${spin_chars[$$i]}; \
			printf "\r\033[K$(LARANJA_ESCURO)Ⓡ Compilando $(RESET)$$current_color$$current_char$(RESET)"; \
			sleep $$delay; \
		done; \
	done; \
	tput cnorm; \
	wait $$pid; \
	if [ $$? -eq 0 ]; then \
		:; \
	else \
		echo ""; \
		echo "❌ Falha ao executar a compilação."; \
		exit 1; \
	fi

	@# 2. Exibe sucesso
	@printf "\r\033[K$(LARANJA_ESCURO)✅ Compilado$(RESET)\n"

	@# 3. Instala
	@printf "\r\033[K$(LARANJA_ESCURO)📦 Instalando $(LIBNAME) em $(INSTALL_BIN)...$(RESET)\n"
	@mkdir -p $(INSTALL_BIN)
	@install -m 755 $(LIBNAME) $(INSTALL_BIN)/$(LIBNAME)
	@printf "\r\033[K$(LARANJA_ESCURO)✨ Instalação concluída!$(RESET)\n"

desinstalar:
	@printf "\r\033[K$(LARANJA_ESCURO)🗑️  Removendo $(LIBNAME)...$(RESET)\n"
	@rm -f $(INSTALL_BIN)/$(LIBNAME)
	@printf "\r\033[K$(LARANJA_ESCURO)✅ Desinstalado$(RESET)\n"
