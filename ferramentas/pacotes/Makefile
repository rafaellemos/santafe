CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra
PLAT ?= $(shell uname -s)
GLIB_CFLAGS := $(shell pkg-config --cflags glib-2.0)
GLIB_LIBS := $(shell pkg-config --libs glib-2.0)
ifeq ($(filter macosx Darwin,$(PLAT)),)
SHARED = -shared
else
SHARED = -bundle -undefined dynamic_lookup
endif
all: nativo.so
nativo.so: nativo.c ../../src/lua.h ../../src/lauxlib.h
	$(CC) $(CFLAGS) -std=c99 -fPIC $(SHARED) -I../../src $(GLIB_CFLAGS) nativo.c $(GLIB_LIBS) -o $@
clean:
	rm -f nativo.so
.PHONY: all clean
