SHELL := /bin/bash

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

LUA_INC = ../../../src
PKGS = gio-2.0 gobject-2.0 glib-2.0
CC = gcc
CFLAGS = -std=c99 -O2 -Wall -Wextra -fPIC -I$(LUA_INC) $(shell pkg-config --cflags $(PKGS))
LIBS = $(shell pkg-config --libs $(PKGS))

ifeq ($(PLAT),mingw)
  LIBNAME = arquivo.dll
  LDFLAGS = -shared
else ifeq ($(PLAT),macosx)
  LIBNAME = arquivo.so
  LDFLAGS = -bundle -undefined dynamic_lookup
else
  LIBNAME = arquivo.so
  LDFLAGS = -shared
endif

OBJS = arquivo.o
Q ?=

all: $(LIBNAME)

$(LIBNAME): $(OBJS)
	$(Q)$(CC) $(LDFLAGS) -o $@ $(OBJS) $(LIBS)

arquivo.o: arquivo.c atomico.h atomico-lua.h
	$(Q)$(CC) $(CFLAGS) -c $< -o $@

clean limpar:
	@rm -f $(OBJS) $(LIBNAME)

PREFIX ?= /usr/local
INSTALL_BIN = $(PREFIX)/lib/santafé/3.0/bibc

install instalar: all
	@mkdir -p $(INSTALL_BIN)
	@install -m 755 $(LIBNAME) $(INSTALL_BIN)/$(LIBNAME)

uninstall desinstalar:
	@rm -f $(INSTALL_BIN)/$(LIBNAME)

.PHONY: all clean limpar install instalar uninstall desinstalar
