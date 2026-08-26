#!/usr/bin/env bash

echo "Instalador Santafé"

# === Cores (ANSI) ===
VERDE_CLARO="\033[1;32m"
LARANJA_ESCURO="\033[38;5;208m"
RESET="\033[0m"

# === Verifica se estamos na raiz (onde está o Makefile) ===
if [ ! -f Makefile ]; then
    echo "ERRO: Makefile não encontrado. Rode este script na pasta do projeto." >&2
    exit 1
fi

# === sudo / root ===
if [ "$EUID" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    else
        echo "ERRO: você não é root e não há 'sudo' disponível." >&2
        exit 1
    fi
else
    SUDO=""
fi

# === Spinner genérico para rodar comandos silenciosos ===
run_with_spinner() {
    # Usa: run_with_spinner comando arg1 arg2 ...
    # Tudo (stdout+stderr) vai para /dev/null
    local cmd=( "$@" )

    # caracteres e cores
    local spin_chars=( "◉" " " )
    local colors=( "$VERDE_CLARO" "" )
    local delay=0.6

    "${cmd[@]}" >/dev/null 2>&1 &
    local pid=$!

    # Esconde cursor
    tput civis 2>/dev/null || true

    while kill -0 "$pid" 2>/dev/null; do
        for i in 0 1; do
            kill -0 "$pid" 2>/dev/null || break
            local idx=$(( i % 2 ))
            local current_color="${colors[$idx]}"
            local current_char="${spin_chars[$i]}"
            printf "\r\033[K${LARANJA_ESCURO}Ⓡ Resolvendo dependências... ${RESET}${current_color}${current_char}${RESET}"
            sleep "$delay"
        done
    done

    wait "$pid"
    local status=$?

    # Limpa linha e restaura cursor
    printf "\r\033[K"
    tput cnorm 2>/dev/null || true

    return "$status"
}

# === Detecta gerenciador de pacotes ===
# No macOS, a escolha entre Homebrew e MacPorts depende da versão do sistema:
# o Homebrew atual exige oficialmente macOS Sonoma (14) ou superior
# (https://docs.brew.sh/Installation#macos-requirements). Em versões mais
# antigas (Sierra, El Capitan, Mac OS X em geral) o Homebrew não instala/
# não tem bottles disponíveis; o MacPorts cobre um intervalo muito maior
# (documentação oficial cita suporte desde OS X 10.3), então é o caminho
# certo ali.
detect_pkg_manager() {
    if [ "$(uname -s)" = "Darwin" ]; then
        local macos_major
        macos_major=$(sw_vers -productVersion 2>/dev/null | cut -d. -f1)
        macos_major=${macos_major:-0}

        if [ "$macos_major" -ge 14 ] 2>/dev/null; then
            if command -v brew >/dev/null 2>&1; then
                echo "brew"
            else
                echo "brew-ausente"
            fi
        else
            if command -v port >/dev/null 2>&1; then
                echo "macports"
            else
                echo "macports-ausente"
            fi
        fi
    elif command -v apt-get >/dev/null 2>&1; then
        echo "apt"
    elif command -v dnf >/dev/null 2>&1; then
        echo "dnf"
    elif command -v yum >/dev/null 2>&1; then
        echo "yum"
    elif command -v zypper >/dev/null 2>&1; then
        echo "zypper"
    elif command -v pacman >/dev/null 2>&1; then
        echo "pacman"
    else
        echo "unknown"
    fi
}

# === IPv4 primeiro, IPv6 de reserva (gerenciadores de pacotes Linux) ===
# Várias VMs saem de fábrica com uma interface IPv6 só link-local (sem rota
# real pra internet), mas o glibc por padrão prefere endereços IPv6 (RFC
# 6724) quando o DNS devolve os dois — o gerenciador de pacotes então fica
# minutos tentando espelhos por IPv6 inalcançável antes de cair pro IPv4 que
# funciona. Ajustamos a precedência em /etc/gai.conf em vez de desativar IPv6
# (Acquire::ForceIPv4 faria isso): se a rota v6 existir/voltar a existir, ela
# continua disponível como fallback, só não é mais tentada primeiro.
prefer_ipv4() {
    local gai_conf="/etc/gai.conf"

    if [ -f "$gai_conf" ] && grep -qE "^[[:space:]]*precedence[[:space:]]+::ffff:0:0/96" "$gai_conf" 2>/dev/null; then
        return
    fi

    echo "precedence ::ffff:0:0/96  100" | $SUDO tee -a "$gai_conf" >/dev/null 2>&1 || true
}

# === Instalações por distro (sempre silenciosas) ===
install_deps_apt() {
    local failed=0
    prefer_ipv4
    run_with_spinner "$SUDO" apt-get -qq update || failed=1
    run_with_spinner "$SUDO" apt-get -qq install -y \
        build-essential \
        pkg-config \
        libglib2.0-dev \
        libmariadb-dev \
        libsodium-dev \
        libreadline-dev || failed=1

    if [ "$failed" -ne 0 ]; then
        echo "AVISO: falha ao instalar dependências. Verifique seu gerenciador de pacotes (apt)." >&2
    fi
}

install_deps_dnf() {
    local failed=0
    prefer_ipv4
    run_with_spinner "$SUDO" dnf -q groupinstall -y "Development Tools" || failed=1
    run_with_spinner "$SUDO" dnf -q install -y \
        gcc make pkg-config \
        glib2-devel \
        mariadb-devel \
        libsodium-devel \
        readline-devel || failed=1

    if [ "$failed" -ne 0 ]; then
        echo "AVISO: falha ao instalar dependências. Verifique seu gerenciador de pacotes (dnf)." >&2
    fi
}

install_deps_yum() {
    local failed=0
    prefer_ipv4
    run_with_spinner "$SUDO" yum -q groupinstall -y "Development Tools" || failed=1
    run_with_spinner "$SUDO" yum -q install -y \
        gcc make pkg-config \
        glib2-devel \
        mariadb-devel \
        libsodium-devel \
        readline-devel || failed=1

    if [ "$failed" -ne 0 ]; then
        echo "AVISO: falha ao instalar dependências. Verifique seu gerenciador de pacotes (yum)." >&2
    fi
}

install_deps_zypper() {
    local failed=0
    prefer_ipv4
    run_with_spinner "$SUDO" zypper -q refresh || failed=1
    run_with_spinner "$SUDO" zypper -q install -y \
        gcc make pkg-config \
        glib2-devel \
        libmariadb-devel \
        libsodium-devel \
        readline-devel || failed=1

    if [ "$failed" -ne 0 ]; then
        echo "AVISO: falha ao instalar dependências. Verifique seu gerenciador de pacotes (zypper)." >&2
    fi
}

install_deps_pacman() {
    local failed=0
    prefer_ipv4
    run_with_spinner "$SUDO" pacman -Sy --noconfirm \
        base-devel \
        pkg-config \
        glib2 \
        mariadb-libs \
        libsodium \
        readline || failed=1

    if [ "$failed" -ne 0 ]; then
        echo "AVISO: falha ao instalar dependências. Verifique seu gerenciador de pacotes (pacman)." >&2
    fi
}

install_deps_brew() {
    local failed=0
    run_with_spinner brew update || true
    run_with_spinner brew install pkg-config glib readline mariadb-connector-c libsodium || failed=1

    if [ "$failed" -ne 0 ]; then
        echo "AVISO: falha ao instalar dependências via brew. Rode manualmente:" >&2
        echo "  brew install pkg-config glib readline mariadb-connector-c libsodium" >&2
    fi
}

HOMEBREW_INSTALL_CMD='/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'

# Roda o instalador oficial do Homebrew em primeiro plano (sem run_with_spinner):
# esse instalador pode precisar pedir a senha de sudo e, se algo der errado
# (Ferramentas de Linha de Comando ausentes, usuário sem privilégio de admin,
# etc.), ele imprime um motivo específico — se escondermos a saída atrás do
# spinner (que joga tudo em /dev/null), o usuário só vê um "ERRO" genérico e
# sem pista nenhuma do que realmente aconteceu.
run_homebrew_installer() {
    # O instalador do Homebrew, com NONINTERACTIVE=1, testa acesso sudo de
    # forma NÃO-interativa (sudo -n -v) — sem um "ticket" de sudo já em
    # cache, isso falha na hora e ele desiste sem nunca chegar a pedir sua
    # senha (mesmo você sendo admin). Autenticamos aqui antes, de forma
    # interativa de verdade, pra cachear o ticket que o instalador precisa.
    echo "Precisamos da sua senha de admin do macOS para instalar o Homebrew:" >&2
    if ! sudo -v; then
        echo "ERRO: não foi possível autenticar com sudo." >&2
        return 1
    fi

    export NONINTERACTIVE=1
    eval "$HOMEBREW_INSTALL_CMD"

    # O instalador não atualiza o PATH desta sessão em execução (só grava em
    # ~/.zprofile para sessões futuras); carregamos manualmente pra já poder
    # usar o brew sem precisar abrir um terminal novo.
    if [ -x /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi

    command -v brew >/dev/null 2>&1
}

install_deps_brew_ausente() {
    echo "Homebrew não encontrado. Instalando agora (pode pedir sua senha do macOS)..." >&2

    if run_homebrew_installer; then
        install_deps_brew
        return
    fi

    echo "ERRO: não foi possível instalar o Homebrew automaticamente (veja o motivo acima)." >&2
    read -r -p "Deseja tentar instalar o Homebrew agora, de novo? [S/n] " resp_brew
    resp_brew=${resp_brew:-S}
    case "$resp_brew" in
        [Nn]*)
            echo "Quando quiser, rode manualmente:" >&2
            echo "  $HOMEBREW_INSTALL_CMD" >&2
            ;;
        *)
            if run_homebrew_installer; then
                install_deps_brew
            else
                echo "ERRO: a instalação do Homebrew continua falhando. Instale manualmente e rode este instalador de novo:" >&2
                echo "  $HOMEBREW_INSTALL_CMD" >&2
            fi
            ;;
    esac
}

# MacPorts não tem um port avulso "só o cliente" de MariaDB como o
# mariadb-connector-c do Homebrew; o port disponível é o "mariadb" completo
# (cliente + servidor), que também traz o mariadb_config usado no Makefile.
install_deps_macports() {
    local failed=0
    run_with_spinner sudo port selfupdate || true
    run_with_spinner sudo port install pkgconfig glib2 readline mariadb libsodium || failed=1

    if [ "$failed" -ne 0 ]; then
        echo "AVISO: falha ao instalar dependências via MacPorts. Rode manualmente:" >&2
        echo "  sudo port install pkgconfig glib2 readline mariadb libsodium" >&2
    fi
}

# Mapeia major/minor do macOS pro codinome usado nos nomes dos .pkg do
# MacPorts (releases do GitHub macports/macports-base). Ex.: 15 -> 15-Sequoia,
# 10.12 -> 10.12-Sierra.
macports_codename() {
    local major="$1" minor="$2"
    case "$major" in
        26) echo "26-Tahoe" ;;
        15) echo "15-Sequoia" ;;
        14) echo "14-Sonoma" ;;
        13) echo "13-Ventura" ;;
        12) echo "12-Monterey" ;;
        11) echo "11-BigSur" ;;
        10)
            case "$minor" in
                15) echo "10.15-Catalina" ;;
                14) echo "10.14-Mojave" ;;
                13) echo "10.13-HighSierra" ;;
                12) echo "10.12-Sierra" ;;
                11) echo "10.11-ElCapitan" ;;
                10) echo "10.10-Yosemite" ;;
                9)  echo "10.9-Mavericks" ;;
                8)  echo "10.8-MountainLion" ;;
                7)  echo "10.7-Lion" ;;
                6)  echo "10.6-SnowLeopard" ;;
                *)  echo "" ;;
            esac
            ;;
        *) echo "" ;;
    esac
}

install_deps_macports_ausente() {
    local macos_ver macos_major macos_minor codename asset_url tmp_pkg
    macos_ver=$(sw_vers -productVersion 2>/dev/null || echo "0.0")
    macos_major=$(echo "$macos_ver" | cut -d. -f1)
    macos_minor=$(echo "$macos_ver" | cut -d. -f2)
    codename=$(macports_codename "$macos_major" "$macos_minor")

    echo "MacPorts não encontrado. Instalando agora para macOS $macos_ver..." >&2

    if [ -z "$codename" ]; then
        echo "ERRO: não sei mapear o macOS $macos_ver pra um instalador do MacPorts automaticamente." >&2
        echo "Baixe manualmente em https://www.macports.org/install.php" >&2
        echo "e rode: sudo port install pkgconfig glib2 readline mariadb libsodium" >&2
        return
    fi

    asset_url=$(curl -fsSL "https://api.github.com/repos/macports/macports-base/releases/latest" 2>/dev/null \
        | grep -oE "\"browser_download_url\": *\"[^\"]*${codename}\.pkg\"" \
        | head -1 \
        | sed -E 's/.*"(https:[^"]+)"/\1/')

    if [ -z "$asset_url" ]; then
        echo "ERRO: não achei o instalador do MacPorts para $codename automaticamente." >&2
        echo "Baixe manualmente em https://www.macports.org/install.php" >&2
        echo "e rode: sudo port install pkgconfig glib2 readline mariadb libsodium" >&2
        return
    fi

    tmp_pkg="/tmp/MacPorts-${codename}.pkg"
    echo "Baixando $asset_url ..." >&2
    if ! curl -fsSL -o "$tmp_pkg" "$asset_url"; then
        echo "ERRO: falha ao baixar o instalador do MacPorts." >&2
        return
    fi

    echo "Instalando MacPorts (pode pedir sua senha do macOS)..." >&2
    # Em primeiro plano (sem run_with_spinner): o comando 'installer' pode
    # pedir a senha de sudo e, se falhar, explica o motivo — escondido atrás
    # do spinner, o usuário só veria um "ERRO" genérico sem pista nenhuma.
    if ! sudo installer -pkg "$tmp_pkg" -target /; then
        echo "ERRO: instalação do MacPorts falhou (veja o motivo acima)." >&2
        rm -f "$tmp_pkg"
        return
    fi
    rm -f "$tmp_pkg"

    # 'port' fica em /opt/local/bin, que só entra no PATH de sessões novas
    # (o instalador atualiza /etc/paths.d, mas isso não afeta esta sessão já
    # aberta), então adicionamos manualmente pra já poder usar o port agora.
    export PATH="/opt/local/bin:/opt/local/sbin:$PATH"

    if command -v port >/dev/null 2>&1; then
        install_deps_macports
    else
        echo "AVISO: MacPorts instalado, mas 'port' não entrou no PATH desta sessão." >&2
        echo "Abra um terminal novo e rode este instalador de novo." >&2
    fi
}

install_deps_manual() {
    echo "AVISO: não foi possível detectar o gerenciador de pacotes." >&2
    echo "Instale manualmente antes de continuar:" >&2
    echo "  - gcc, make, pkg-config" >&2
    echo "  - glib dev, mariadb dev, readline dev" >&2
}

# === Fluxo principal ===

read -r -p "Instalar dependências de compilação automaticamente? [S/n] " resp
resp=${resp:-S}

case "$resp" in
    [Nn]*)
        ;;
    *)
        PM=$(detect_pkg_manager)
        case "$PM" in
            brew)             install_deps_brew ;;
            brew-ausente)     install_deps_brew_ausente ;;
            macports)         install_deps_macports ;;
            macports-ausente) install_deps_macports_ausente ;;
            apt)              install_deps_apt ;;
            dnf)              install_deps_dnf ;;
            yum)              install_deps_yum ;;
            zypper)           install_deps_zypper ;;
            pacman)           install_deps_pacman ;;
            *)                install_deps_manual ;;
        esac
        ;;
esac

$SUDO make instalar
status=$?

if [ "$status" -ne 0 ]; then
    echo "ERRO: a instalação do núcleo falhou. Rode 'make cbin' para ver o erro de compilação em detalhes." >&2
    exit "$status"
fi

if command -v santafé >/dev/null 2>&1; then
    santafé
elif [ -x /usr/local/bin/santafé ]; then
    /usr/local/bin/santafé
else
    echo "AVISO: 'santafé' não foi encontrado no PATH após a instalação." >&2
    echo "Verifique se /usr/local/bin está no seu PATH." >&2
fi
