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
SFV = 1.0             # versão "pública" do Santafé para paths de bibs

# Diretórios de instalação padrão
INSTALL_TOP  = /usr/local
INSTALL_BIN  = $(INSTALL_TOP)/bin
INSTALL_INC  = $(INSTALL_TOP)/include
INSTALL_LIB  = $(INSTALL_TOP)/lib
INSTALL_LMOD = $(INSTALL_TOP)/share/santafé/1.0/bibf
INSTALL_CMOD = $(INSTALL_TOP)/lib/santafé/1.0/bibc

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
TO_BIN = $(if $(filter mingw,$(AUTO_PLAT)),santafe.exe santafec.exe,santafé santafec)
TO_INC = lua.h luaconf.h lualib.h lauxlib.h lua.hpp
TO_LIB = liblua.a

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

# Comando para elevar privilégios (sudo ou su -c); vazio se já for root
SUDO_OU_SU := $(shell \
    if [ "$$(id -u)" -eq 0 ]; then \
        echo ""; \
    elif command -v sudo >/dev/null 2>&1; then \
        echo sudo; \
    else \
        echo "su -c"; \
    fi)

# Diretório para pkg-config e nome do arquivo .pc
PKGCONFIG_DIR = $(INSTALL_LIB)/pkgconfig
PC_FILE       = santafe.pc

# Diretórios de bibs C que serão compilados/instalados em cbibc/ibibc
BIBC_DIRS = \
    bibs/bibc/rede \
    bibs/bibc/mariadb \
    bibs/bibc/segredo \
    bibs/bibc/tomada

BIBF_FILES = \
    bibs/bibf/bit32.fé \
    bibs/bibf/caminheiro.fé \
    bibs/bibf/imagem.fé \
    bibs/bibf/imagem_jpeg.fé \
    bibs/bibf/imagem_png.fé \
    bibs/bibf/imagem_svg.fé \
    bibs/bibf/rpdf.fé \
    bibs/bibf/rpdf_unicode.fé \
    bibs/bibf/turing.fé

RPDF_FONT_FILES = \
    bibs/bibf/rpdf/fontes/NotoSans-Regular.ttf \
    bibs/bibf/rpdf/fontes/OFL.txt
RPDF_DOC_FILE = bibs/bibf/rpdf/LEIA-ME.md
IMAGEM_DOC_FILE = bibs/bibf/imagem/LEIA-ME.md
OBSOLETE_BIBF_FILES = png.fé rpdf_imagem.fé

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

install: dummy
	cd src && $(MKDIR) $(INSTALL_BIN) $(INSTALL_INC) $(INSTALL_LIB) $(INSTALL_LMOD) $(INSTALL_CMOD)
	cd src && $(INSTALL_EXEC) $(TO_BIN) $(INSTALL_BIN)
	cd src && $(INSTALL_DATA) $(TO_INC) $(INSTALL_INC)
	cd src && $(INSTALL_DATA) $(TO_LIB) $(INSTALL_LIB)

uninstall:
	cd src && cd $(INSTALL_BIN) && $(RM) $(TO_BIN)
	cd src && cd $(INSTALL_INC) && $(RM) $(TO_INC)
	cd src && cd $(INSTALL_LIB) && $(RM) $(TO_LIB)

local:
	$(MAKE) install INSTALL_TOP=../install

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
	@printf "$(LARANJA_ESCURO)==> Detectando sistema e instalando dependências...$(RESET)\n"
	@uname_s=$$(uname -s); \
	if [ "$$uname_s" = "Linux" ]; then \
	  if [ -f /etc/os-release ]; then \
	    . /etc/os-release; \
	    case "$$ID" in \
	      debian|ubuntu|linuxmint|pop|neon) \
	        printf "$(LARANJA_ESCURO)==> Distribuição baseada em Debian detectada. Usando apt-get...$(RESET)\n"; \
	        if [ -z "$(SUDO_OU_SU)" ]; then \
	          apt-get install -y build-essential libreadline-dev libglib2.0-dev libmariadb-dev libsodium-dev || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via apt-get. Instale os pacotes manualmente.$(RESET)\n"; \
	        elif [ "$(SUDO_OU_SU)" = "sudo" ]; then \
	          sudo apt-get install -y build-essential libreadline-dev libglib2.0-dev libmariadb-dev libsodium-dev || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via apt-get. Instale os pacotes manualmente.$(RESET)\n"; \
	        else \
	          $(SUDO_OU_SU) 'apt-get install -y build-essential libreadline-dev libglib2.0-dev libmariadb-dev libsodium-dev' || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via apt-get. Instale os pacotes manualmente.$(RESET)\n"; \
	        fi; \
	        ;; \
	      fedora|rhel|centos|rocky|almalinux) \
	        printf "$(LARANJA_ESCURO)==> Distribuição baseada em RedHat detectada.$(RESET)\n"; \
	        if command -v dnf >/dev/null 2>&1; then \
	          printf "$(LARANJA_ESCURO)==> Usando dnf...$(RESET)\n"; \
	          if [ -z "$(SUDO_OU_SU)" ]; then \
	            dnf install -y gcc make readline-devel glib2-devel mariadb-devel libsodium-devel || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via dnf. Instale os pacotes manualmente.$(RESET)\n"; \
	          elif [ "$(SUDO_OU_SU)" = "sudo" ]; then \
	            sudo dnf install -y gcc make readline-devel glib2-devel mariadb-devel libsodium-devel || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via dnf. Instale os pacotes manualmente.$(RESET)\n"; \
	          else \
	            $(SUDO_OU_SU) 'dnf install -y gcc make readline-devel glib2-devel mariadb-connector-c-devel libsodium-devel' || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via dnf. Instale os pacotes manualmente.$(RESET)\n"; \
	          fi; \
	        elif command -v yum >/dev/null 2>&1; then \
	          printf "$(LARANJA_ESCURO)==> Usando yum...$(RESET)\n"; \
	          if [ -z "$(SUDO_OU_SU)" ]; then \
	            yum install -y gcc make readline-devel glib2-devel mariadb-devel libsodium-devel || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via yum. Instale os pacotes manualmente.$(RESET)\n"; \
	          elif [ "$(SUDO_OU_SU)" = "sudo" ]; then \
	            sudo yum install -y gcc make readline-devel glib2-devel mariadb-devel libsodium-devel || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via yum. Instale os pacotes manualmente.$(RESET)\n"; \
	          else \
	            $(SUDO_OU_SU) 'yum install -y gcc make readline-devel glib2-devel mariadb-connector-c-devel libsodium-devel' || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via yum. Instale os pacotes manualmente.$(RESET)\n"; \
	          fi; \
	        else \
	          printf "$(LARANJA_ESCURO)⚠️  Nem dnf nem yum encontrados. Instale manualmente: gcc, make, readline-devel, glib2-devel, mariadb-connector-c-devel, libsodium-devel.$(RESET)\n"; \
	        fi; \
	        ;; \
	      arch|manjaro|endeavouros) \
	        printf "$(LARANJA_ESCURO)==> Distribuição baseada em Arch detectada. Usando pacman...$(RESET)\n"; \
	        if [ -z "$(SUDO_OU_SU)" ]; then \
	          pacman -S --needed --noconfirm base-devel readline glib2 mariadb-libs libsodium || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via pacman. Instale os pacotes manualmente.$(RESET)\n"; \
	        elif [ "$(SUDO_OU_SU)" = "sudo" ]; then \
	          sudo pacman -S --needed --noconfirm base-devel readline glib2 mariadb-libs libsodium || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via pacman. Instale os pacotes manualmente.$(RESET)\n"; \
	        else \
	          $(SUDO_OU_SU) 'pacman -S --needed --noconfirm base-devel readline glib2 mariadb-libs libsodium' || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via pacman. Instale os pacotes manualmente.$(RESET)\n"; \
	        fi; \
	        ;; \
	      *) \
	        printf "$(LARANJA_ESCURO)⚠️  Distribuição Linux não suportada automaticamente ($$ID).$(RESET)\n"; \
	        printf "$(LARANJA_ESCURO)   Instale manualmente: gcc, make, libreadline-dev (ou readline-devel), glib2-dev (ou glib2-devel), libmariadb-dev (ou mariadb-connector-c-devel), libsodium-dev (ou libsodium-devel).$(RESET)\n"; \
	        ;; \
	    esac; \
	  else \
	    printf "$(LARANJA_ESCURO)⚠️  Não foi possível detectar a distribuição Linux (/etc/os-release ausente).$(RESET)\n"; \
	    printf "$(LARANJA_ESCURO)   Instale manualmente: gcc, make, libreadline-dev, glib2-dev, libmariadb-dev, libsodium-dev.$(RESET)\n"; \
	  fi; \
	elif [ "$$uname_s" = "Darwin" ]; then \
	  macos_major=$$(sw_vers -productVersion 2>/dev/null | cut -d. -f1); \
	  macos_major=$${macos_major:-0}; \
	  if [ "$$macos_major" -ge 14 ] 2>/dev/null; then \
	    printf "$(LARANJA_ESCURO)==> macOS $$macos_major (Sonoma+) detectado. Usando Homebrew (brew)...$(RESET)\n"; \
	    if ! command -v brew >/dev/null 2>&1; then \
	      printf "$(LARANJA_ESCURO)⚠️  Homebrew não encontrado. Instale em https://brew.sh e rode 'make ideps' novamente.$(RESET)\n"; \
	    else \
	      brew install pkg-config readline glib mariadb-connector-c libsodium || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via brew. Instale os pacotes manualmente.$(RESET)\n"; \
	    fi; \
	  else \
	    printf "$(LARANJA_ESCURO)==> macOS $$macos_major detectado (anterior ao Sonoma/14, fora do suporte do Homebrew atual). Usando MacPorts...$(RESET)\n"; \
	    if ! command -v port >/dev/null 2>&1; then \
	      printf "$(LARANJA_ESCURO)⚠️  MacPorts não encontrado. Instale o .pkg certo para sua versão em https://www.macports.org/install.php e rode 'make ideps' novamente.$(RESET)\n"; \
	    else \
	      sudo port install pkgconfig readline glib2 mariadb libsodium || printf "$(LARANJA_ESCURO)⚠️  Falha ao instalar via MacPorts. Instale os pacotes manualmente.$(RESET)\n"; \
	    fi; \
	  fi; \
	else \
	  printf "$(LARANJA_ESCURO)⚠️  Sistema $$uname_s não possui instalador automático aqui.$(RESET)\n"; \
	  printf "$(LARANJA_ESCURO)   Instale manualmente: gcc, make, readline (dev), glib2 (dev), mariadb (dev).$(RESET)\n"; \
	fi
	@printf "$(LARANJA_ESCURO)⚠️  Se algum passo acima falhou, instale os pacotes manualmente e rode 'make instalar' novamente.$(RESET)\n"

# Compila o núcleo do Santafé (sem instalar)
cbin:
	@printf "$(LARANJA_ESCURO)==> Compilando núcleo Santafé (plataforma $(AUTO_PLAT))...$(RESET)\n"
	@cd src && $(MAKE) $(AUTO_PLAT)

# Compila as bibliotecas C (rede, mariadb, tomada, etc.)
# Cada lib é opcional: se faltar dependência do sistema (glib, mariadb, etc.)
# avisa e segue para a próxima, sem derrubar o núcleo já compilado.
cbibc:
	@printf "$(LARANJA_ESCURO)==> Compilando bibliotecas C (bibs), plataforma $(AUTO_PLAT)...$(RESET)\n"
	@for d in $(BIBC_DIRS); do \
	  if [ -d "$$d" ]; then \
	    printf "$(LARANJA_ESCURO)  --> $$d$(RESET)\n"; \
	    $(MAKE) -C $$d PLAT=$(AUTO_PLAT) || printf "$(LARANJA_ESCURO)  ⚠️  $$d falhou ao compilar (dependência do sistema ausente?). Pulando. Rode 'make -C $$d' para ver o erro.$(RESET)\n"; \
	  fi; \
	done

# Instala os binários do núcleo.
# Falha alto (sem engolir erro) se os binários do núcleo não existirem: isso
# indica que 'cbin' não rodou ou falhou, e instalar "nada" não deve parecer sucesso.
ibin:
	@printf "$(LARANJA_ESCURO)==> Instalando núcleo Santafé em $(INSTALL_TOP)...$(RESET)\n"
	@for b in $(TO_BIN); do \
	    if [ ! -f "src/$$b" ]; then \
	        printf "$(LARANJA_ESCURO)❌ src/$$b não existe. Rode 'make cbin' primeiro e veja o erro de compilação.$(RESET)\n"; \
	        exit 1; \
	    fi; \
	done
	@if [ -z "$(SUDO_OU_SU)" ]; then \
	    $(MKDIR) $(INSTALL_BIN);\
	    cd src && $(INSTALL_EXEC) $(TO_BIN) $(INSTALL_BIN);\
	elif [ "$(SUDO_OU_SU)" = "sudo" ]; then \
	    sudo $(MKDIR) $(INSTALL_BIN);\
	    cd src && sudo $(INSTALL_EXEC) $(TO_BIN) $(INSTALL_BIN);\
	else \
	    $(SUDO_OU_SU) ' $(MKDIR) $(INSTALL_BIN)';\
	    $(SUDO_OU_SU) ' $(INSTALL_EXEC) $(TO_BIN) $(INSTALL_BIN)';\
	fi
	@printf "$(LARANJA_ESCURO)✅ Santafé instalado com sucesso.$(RESET)\n"

# Instala as bibliotecas C (.so) nas pastas de bibc do Santafé
# MODIFICADO: Instala diretamente o arquivo .so, ignorando subdiretórios criados pelo make interno
ibibc:
	@printf "$(LARANJA_ESCURO)==> Instalando bibliotecas C em $(INSTALL_CMOD) (sem subdirs)...$(RESET)\n"
	@if [ -z "$(SUDO_OU_SU)" ]; then \
	    printf "$(LARANJA_ESCURO)    --> Criando diretório $(INSTALL_CMOD)...$(RESET)\n"; \
	    $(MKDIR) $(INSTALL_CMOD)|| true;\
	elif [ "$(SUDO_OU_SU)" = "sudo" ]; then \
	    printf "$(LARANJA_ESCURO)    --> Criando diretório $(INSTALL_CMOD)...$(RESET)\n"; \
	    sudo $(MKDIR) $(INSTALL_CMOD)|| true;\
	else \
	    printf "$(LARANJA_ESCURO)    --> Criando diretório $(INSTALL_CMOD)...$(RESET)\n"; \
	    $(SUDO_OU_SU) ' $(MKDIR) $(INSTALL_CMOD)'|| true;\
	fi;
	@for d in $(BIBC_DIRS); do \
	    if [ -d "$$d" ]; then \
	        printf "$(LARANJA_ESCURO)    --> $$d (Instalando .so na raiz)$(RESET)\n"; \
	        if [ -f "$$d/Makefile" ]; then $(MAKE) -C $$d PLAT=$(AUTO_PLAT) >/dev/null 2>&1 || { printf "$(LARANJA_ESCURO)    ⚠️  $$d falhou ao compilar, pulando.$(RESET)\n"; continue; }; fi; \
	        for f in $$d/*.so $$d/*.dylib $$d/*.dll; do \
	           if [ -f "$$f" ]; then \
	               if [ -z "$(SUDO_OU_SU)" ]; then \
	                   $(INSTALL_EXEC) "$$f" "$(INSTALL_CMOD)"; \
	               elif [ "$(SUDO_OU_SU)" = "sudo" ]; then \
	                   sudo $(INSTALL_EXEC) "$$f" "$(INSTALL_CMOD)"; \
	               else \
	                   $(SUDO_OU_SU) "$(INSTALL_EXEC) '$$f' '$(INSTALL_CMOD)'"; \
	               fi; \
	           fi; \
	        done; \
	    fi; \
	done

# Instala as bibliotecas Santafé (.fé) diretamente na raiz de bibf.
ibibf:
	@printf "$(LARANJA_ESCURO)==> Instalando bibliotecas Santafé em $(INSTALL_LMOD) (sem subdirs)...$(RESET)\n"
	@if [ -z "$(SUDO_OU_SU)" ]; then \
	    printf "$(LARANJA_ESCURO)    --> Criando diretório $(INSTALL_LMOD)...$(RESET)\n"; \
	    $(MKDIR) $(INSTALL_LMOD)|| true;\
	elif [ "$(SUDO_OU_SU)" = "sudo" ]; then \
	    printf "$(LARANJA_ESCURO)    --> Criando diretório $(INSTALL_LMOD)...$(RESET)\n"; \
	    sudo $(MKDIR) $(INSTALL_LMOD)|| true;\
	else \
	    printf "$(LARANJA_ESCURO)    --> Criando diretório $(INSTALL_LMOD)...$(RESET)\n"; \
	    $(SUDO_OU_SU) ' $(MKDIR) $(INSTALL_LMOD)'|| true;\
	fi;
	@for f in $(BIBF_FILES); do \
	    if [ ! -f "$$f" ]; then \
	        printf "$(LARANJA_ESCURO)ERRO: biblioteca Santafé ausente: $$f$(RESET)\n"; \
	        exit 1; \
	    fi; \
	    printf "$(LARANJA_ESCURO)    --> $$f$(RESET)\n"; \
	    if [ -z "$(SUDO_OU_SU)" ]; then \
	        $(INSTALL_DATA) "$$f" "$(INSTALL_LMOD)"; \
	    elif [ "$(SUDO_OU_SU)" = "sudo" ]; then \
	        sudo $(INSTALL_DATA) "$$f" "$(INSTALL_LMOD)"; \
	    else \
	        $(SUDO_OU_SU) "$(INSTALL_DATA) '$$f' '$(INSTALL_LMOD)'"; \
	    fi; \
	done
	@rpdfdir="$(INSTALL_LMOD)/rpdf"; destino="$$rpdfdir/fontes"; \
	if [ -z "$(SUDO_OU_SU)" ]; then $(MKDIR) "$$destino"; $(INSTALL_DATA) "$(RPDF_DOC_FILE)" "$$rpdfdir"; \
	elif [ "$(SUDO_OU_SU)" = "sudo" ]; then sudo $(MKDIR) "$$destino"; sudo $(INSTALL_DATA) "$(RPDF_DOC_FILE)" "$$rpdfdir"; \
	else $(SUDO_OU_SU) "$(MKDIR) '$$destino'"; $(SUDO_OU_SU) "$(INSTALL_DATA) '$(RPDF_DOC_FILE)' '$$rpdfdir'"; fi; \
	for f in $(RPDF_FONT_FILES); do \
	    printf "$(LARANJA_ESCURO)    --> $$f$(RESET)\n"; \
	    if [ -z "$(SUDO_OU_SU)" ]; then $(INSTALL_DATA) "$$f" "$$destino"; \
	    elif [ "$(SUDO_OU_SU)" = "sudo" ]; then sudo $(INSTALL_DATA) "$$f" "$$destino"; \
	    else $(SUDO_OU_SU) "$(INSTALL_DATA) '$$f' '$$destino'"; fi; \
	done
	@imagemdir="$(INSTALL_LMOD)/imagem"; \
	printf "$(LARANJA_ESCURO)    --> $(IMAGEM_DOC_FILE)$(RESET)\n"; \
	if [ -z "$(SUDO_OU_SU)" ]; then $(MKDIR) "$$imagemdir"; $(INSTALL_DATA) "$(IMAGEM_DOC_FILE)" "$$imagemdir"; \
	elif [ "$(SUDO_OU_SU)" = "sudo" ]; then sudo $(MKDIR) "$$imagemdir"; sudo $(INSTALL_DATA) "$(IMAGEM_DOC_FILE)" "$$imagemdir"; \
	else $(SUDO_OU_SU) "$(MKDIR) '$$imagemdir'"; $(SUDO_OU_SU) "$(INSTALL_DATA) '$(IMAGEM_DOC_FILE)' '$$imagemdir'"; fi
	@for antigo in $(OBSOLETE_BIBF_FILES); do \
	    destino="$(INSTALL_LMOD)/$$antigo"; \
	    if [ -z "$(SUDO_OU_SU)" ]; then $(RM) "$$destino"; \
	    elif [ "$(SUDO_OU_SU)" = "sudo" ]; then sudo $(RM) "$$destino"; \
	    else $(SUDO_OU_SU) "$(RM) '$$destino'"; fi; \
	done

# Gera e instala o arquivo santafe.pc para pkg-config
instalar-pc:
	@printf "$(LARANJA_ESCURO)==> Gerando arquivo pkg-config $(PC_FILE)...$(RESET)\n"
	@$(MKDIR) $(PKGCONFIG_DIR)
	@echo "prefix=$(INSTALL_TOP)"                          >  $(PKGCONFIG_DIR)/$(PC_FILE)
	@echo "exec_prefix=\$${prefix}"                        >> $(PKGCONFIG_DIR)/$(PC_FILE)
	@echo "libdir=\$${exec_prefix}/lib"                    >> $(PKGCONFIG_DIR)/$(PC_FILE)
	@echo "includedir=\$${prefix}/include"                 >> $(PKGCONFIG_DIR)/$(PC_FILE)
	@echo ""                                               >> $(PKGCONFIG_DIR)/$(PC_FILE)
	@echo "Name: Santafe"                                  >> $(PKGCONFIG_DIR)/$(PC_FILE)
	@echo "Description: Santafé (ramificação de Lua 5.3)"         >> $(PKGCONFIG_DIR)/$(PC_FILE)
	@echo "Version: $(R)"                                  >> $(PKGCONFIG_DIR)/$(PC_FILE)
	@echo "Libs: -L\$${libdir} -llua"                      >> $(PKGCONFIG_DIR)/$(PC_FILE)
	@echo "Cflags: -I\$${includedir}"                      >> $(PKGCONFIG_DIR)/$(PC_FILE)
	@printf "\r\033[K$(LARANJA_ESCURO)✅ pkg-config instalado em $(PKGCONFIG_DIR)/$(PC_FILE)$(RESET)\n"

pc: instalar-pc

# =============================================================================
#  Alvos personalizados Santafé (com animação)
# =============================================================================

limpar:
	@printf "$(LARANJA_ESCURO) LIMPANDO --> src$(RESET)\n"
	@cd src && $(MAKE) clean > /dev/null 2>&1
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
	@# 1. Pede senha SUDO antes de esconder a saída (se não for root e sudo existir)
	@if [ "$$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then \
	    printf "$(LARANJA_ESCURO)🔑 Autenticando para instalação...$(RESET)\n"; \
	    sudo -v; \
	fi

	@# 2. Executa toda a cadeia silenciosamente em background
	@# AVISO: A saída de ideps é redirecionada para /dev/null, erros de dependência são ignorados.
	@# núcleo (cbin/ibin) é obrigatório: falha aí derruba a instalação de verdade.
	@# libs C opcionais (cbibc/ibibc) são "best effort": se faltar dependência
	@# do sistema (glib, mariadb, ...) seguem sem esconder o resultado do núcleo.
	@# Bibliotecas Fé (ibibf) são obrigatórias: bit32, caminheiro e turing fazem
	@# parte da distribuição e não dependem de pacotes externos para instalar.
	@tput civis; \
	( \
	    $(MAKE) ideps > /dev/null 2>&1 || true && \
	    ( $(MAKE) cbin > /dev/null 2> /tmp/santafe_cbin.log || { cat /tmp/santafe_cbin.log >&2; false; } ) && \
	    $(MAKE) ibin && \
	    ( $(MAKE) cbibc > /dev/null 2>&1 || true ) && \
	    ( $(MAKE) ibibc > /dev/null 2>&1 || true ) && \
	    ( $(MAKE) ibibf > /dev/null 2> /tmp/santafe_ibibf.log || { cat /tmp/santafe_ibibf.log >&2; false; } ) \
	) > /dev/null  & pid=$$!; \
	spin_chars=( "◉          " " ◉         " "  ◉        " "   ◉       " "    ◉      " "     ◉     " "      ◉    " "       ◉ " "        ◉"); \
	colors=( $(AZUL) $(VERDE) $(CIANO) $(VERDE_CLARO) $(AZUL_CLARO) $(AMARELO) $(AMARELO_CLARO) $(BRANCO) ); \
	delay=0.05; \
	tput civis; \
	while kill -0 $$pid 2>/dev/null; do \
	    for i in 0 1 2 3 4 5 6 7 7 6 5 4 3 2 1 0; do \
	        kill -0 $$pid 2>/dev/null || break; \
	        idx=$$(( i % 8 )); \
	        current_color=$${colors[$$idx]}; \
	        current_char=$${spin_chars[$$i]}; \
	        printf "\r\033[K$(LARANJA_ESCURO)Ⓡ Compilando/Instalando $(RESET)$$current_color$$current_char$(RESET)"; \
	        sleep $$delay; \
	    done; \
	done; \
	tput cnorm; \
	wait $$pid; \
	if [ $$? -eq 0 ]; then \
	    printf "\r\033[K$(LARANJA_ESCURO)✅ Santafé compilado e instalado com sucesso!$(RESET)\n"; \
	else \
	    printf "\r\033[K$(LARANJA_ESCURO)❌ Falha na compilação ou instalação. Rode 'make cbin', 'make cbibc', 'make ibin', 'make ibibc' ou 'make ibibf' para ver o erro detalhado.$(RESET)\n"; \
	    exit 1; \
	fi

# Remove as bibliotecas LMOD e CMOD (versão corrigida para arquivos flat)
desinstalar-bibs:
	@printf "$(LARANJA_ESCURO)==> Removendo bibliotecas Santafé e C...$(RESET)\n"
	@for d in $(BIBC_DIRS); do \
	    if [ -d "$$d" ]; then \
	        for f in $$d/*.so; do \
	           if [ -f "$$f" ]; then \
	              ARQ=$$(basename $$f); \
	              printf "$(LARANJA_ESCURO)    --> Removendo C: $(INSTALL_CMOD)/$$ARQ$(RESET)\n"; \
	              if [ -z "$(SUDO_OU_SU)" ]; then \
	                  $(RM) "$(INSTALL_CMOD)/$$ARQ" || true; \
	              elif [ "$(SUDO_OU_SU)" = "sudo" ]; then \
	                  sudo $(RM) "$(INSTALL_CMOD)/$$ARQ" || true; \
	              else \
	                  $(SUDO_OU_SU) " $(RM) '$(INSTALL_CMOD)/$$ARQ'" || true; \
	              fi; \
	           fi; \
	        done; \
	    fi; \
	done
	@for f in $(BIBF_FILES); do \
	    ARQ=$$(basename "$$f"); \
	    printf "$(LARANJA_ESCURO)    --> Removendo F: $(INSTALL_LMOD)/$$ARQ$(RESET)\n"; \
	    if [ -z "$(SUDO_OU_SU)" ]; then \
	        $(RM) "$(INSTALL_LMOD)/$$ARQ" || true; \
	    elif [ "$(SUDO_OU_SU)" = "sudo" ]; then \
	        sudo $(RM) "$(INSTALL_LMOD)/$$ARQ" || true; \
	    else \
	        $(SUDO_OU_SU) " $(RM) '$(INSTALL_LMOD)/$$ARQ'" || true; \
	    fi; \
	done
	@# Tenta remover o diretório pkg-config (se estiver vazio)
	@if [ -z "$(SUDO_OU_SU)" ]; then \
	    $(RM) $(PKGCONFIG_DIR)/$(PC_FILE) && rmdir $(PKGCONFIG_DIR) 2>/dev/null || true; \
	else \
	    $(SUDO_OU_SU) ' $(RM) $(PKGCONFIG_DIR)/$(PC_FILE) && rmdir $(PKGCONFIG_DIR) 2>/dev/null ' || true; \
	fi

desinstalar:
	@# 1. Pede senha SUDO antes de esconder a saída (se não for root e sudo existir)
	@if [ "$$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then \
	    printf "$(LARANJA_ESCURO)🔑 Autenticando para desinstalar...$(RESET)\n"; \
	    sudo -v; \
	fi

	@# 2. Desinstala as bibliotecas (C e Santafé) e o pkg-config
	@$(MAKE) desinstalar-bibs

	@# 3. Desinstala o núcleo (bin, inc, lib, man)
	@printf "$(LARANJA_ESCURO)🗑️    Removendo arquivos do núcleo de $(INSTALL_TOP)...$(RESET)\n"
	@if [ -z "$(SUDO_OU_SU)" ]; then \
	    cd $(INSTALL_BIN) && $(RM) $(TO_BIN) || true; \
	    cd $(INSTALL_INC) && $(RM) $(TO_INC) || true; \
	    cd $(INSTALL_LIB) && $(RM) $(TO_LIB) || true; \
	elif [ "$(SUDO_OU_SU)" = "sudo" ]; then \
	    sudo rm -f $(INSTALL_BIN)/$(TO_BIN) $(INSTALL_INC)/$(TO_INC) $(INSTALL_LIB)/$(TO_LIB) || true; \
	else \
	    $(SUDO_OU_SU) ' rm -f $(INSTALL_BIN)/$(TO_BIN) $(INSTALL_INC)/$(TO_INC) $(INSTALL_LIB)/$(TO_LIB) ' || true; \
	fi;

	@# 4. Limpeza da compilação local
	@$(MAKE) limpar

	@printf "$(LARANJA_ESCURO)✅ Santafé desinstalado com sucesso.$(RESET)\n"



.PHONY: all $(PLATS) clean test testar install local none dummy echo \
        ideps cbin cbibc ibin ibibc instalar-pc pc \
        limpar instalar desinstalar



PROJECT := santafe
VERSION := 1.0.0
DISTDIR := $(PROJECT)-$(VERSION)
dist:
	@echo "Gerando pacotes reproduzíveis em ./dist a partir do commit atual..."
	@mkdir -p dist
	@git archive --format=tar --prefix=$(DISTDIR)/ HEAD | gzip -9 > dist/$(DISTDIR).tar.gz
	@git archive --format=zip --prefix=$(DISTDIR)/ -o dist/$(DISTDIR).zip HEAD
	@cd dist && if command -v sha256sum >/dev/null 2>&1; then \
	    sha256sum $(DISTDIR).tar.gz $(DISTDIR).zip > SHA256SUMS; \
	else \
	    shasum -a 256 $(DISTDIR).tar.gz $(DISTDIR).zip > SHA256SUMS; \
	fi
	@echo "OK: dist/$(DISTDIR).tar.gz"
	@echo "OK: dist/$(DISTDIR).zip"
	@echo "OK: dist/SHA256SUMS"
