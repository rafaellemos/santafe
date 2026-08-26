# Makefile para a biblioteca TOMADA

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

LUA_INC= ../../../src

# Flags
CC= gcc
CFLAGS= -O2 -Wall -fPIC -I$(LUA_INC)

# Arquivos Fontes comuns a todas as plataformas
SRCS_COMMON= luasocket.c timeout.c buffer.c io.c auxiliar.c options.c inet.c \
             tcp.c udp.c except.c select.c compat.c

ifeq ($(PLAT),mingw)
  LIBNAME= tomada.dll
  # wsocket.c é o backend de sockets do LuaSocket para Winsock2 (porta original
  # do próprio LuaSocket, já presente na árvore-fonte)
  SRCS= $(SRCS_COMMON) wsocket.c
  LDFLAGS= -shared -lws2_32
else ifeq ($(PLAT),macosx)
  LIBNAME= tomada.so
  SRCS= $(SRCS_COMMON) usocket.c
  # Módulo Lua carregado em runtime: os símbolos lua_*/luaL_* só existem no
  # executável hospedeiro (santafé), não em libsantafé.a estático aqui. No
  # macOS isso exige "-bundle -undefined dynamic_lookup" em vez de "-shared"
  # (equivalente ao -shared do Linux, que resolve isso via -Wl,-E no host).
  LDFLAGS= -bundle -undefined dynamic_lookup
else
  LIBNAME= tomada.so
  SRCS= $(SRCS_COMMON) usocket.c
  LDFLAGS= -shared
endif

OBJS= $(SRCS:.c=.o)

# --- CONTROLE DE VERBOSIDADE ---
Q ?=

all: $(LIBNAME)

# Regra de Linkagem
$(LIBNAME): $(OBJS)
	$(Q)$(CC) $(LDFLAGS) -o $@ $(OBJS)

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
	@rm -f $(OBJS) mime.o $(LIBNAME)


limpar:
	@rm -f $(OBJS) mime.o $(LIBNAME)
	@printf "\r\033[K$(LARANJA_ESCURO)🗑️  Limpeza concluída.$(RESET)\n"

# Instalação
PREFIX= /usr/local
INSTALL_BIN= $(PREFIX)/lib/santafé/1.0/bibc

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
