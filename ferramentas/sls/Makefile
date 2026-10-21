CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra
PLAT ?= $(shell uname -s)
ifeq ($(filter macosx Darwin,$(PLAT)),)
SHARED = -shared
else
SHARED = -bundle -undefined dynamic_lookup
endif

all: nativo.so
nativo.so: nativo.c ../../src/lua.h ../../src/lauxlib.h
	$(CC) $(CFLAGS) -std=c99 -fPIC $(SHARED) -I../../src nativo.c -o $@
clean:
	rm -f nativo.so
.PHONY: all clean
