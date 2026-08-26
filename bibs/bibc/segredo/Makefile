PLAT ?= auto

ifeq ($(PLAT),auto)
  UNAME_S := $(shell uname -s)
  ifeq ($(UNAME_S),Darwin)
    PLAT := macosx
  else
    PLAT := linux
  endif
endif

CC ?= gcc
PKGS = gio-2.0 libsodium
CFLAGS ?= -O2 -Wall -Wextra
CFLAGS += -fPIC $(shell pkg-config --cflags $(PKGS)) -I../../../src
LIBS = $(shell pkg-config --libs $(PKGS))

ifeq ($(PLAT),macosx)
  ALVO = segredo.so
  LDFLAGS = -bundle -undefined dynamic_lookup
else ifeq ($(PLAT),mingw)
  ALVO = segredo.dll
  LDFLAGS = -shared
else
  ALVO = segredo.so
  LDFLAGS = -shared
endif

all: $(ALVO)

$(ALVO): segredo.o
	$(CC) $(LDFLAGS) -o $@ $^ $(LIBS)

segredo.o: segredo.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f segredo.o segredo.so segredo.dll segredo.dylib

.PHONY: all clean
