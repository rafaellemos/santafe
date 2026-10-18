#!/usr/bin/env python3
"""Aplica, de modo idempotente, a integração do SLS 0.1.0 ao fonte Santafé."""

from __future__ import annotations

import argparse
from pathlib import Path


def leia(arquivo: Path) -> str:
    try:
        return arquivo.read_text(encoding="utf-8")
    except FileNotFoundError as erro:
        raise SystemExit(f"Arquivo obrigatório ausente: {arquivo}") from erro


def grave(arquivo: Path, conteúdo: str) -> None:
    arquivo.write_text(conteúdo, encoding="utf-8")


def substitua_uma_vez(arquivo: Path, conteúdo: str, antigo: str, novo: str) -> str:
    if antigo not in conteúdo:
        contexto = antigo.splitlines()[0][:96]
        raise SystemExit(f"Ponto de integração não localizado: {arquivo}: {contexto!r}")
    return conteúdo.replace(antigo, novo, 1)


def atualize_makefile(raiz: Path) -> None:
    arquivo = raiz / "Makefile"
    conteúdo = leia(arquivo)
    if "SLS_FONTE =" in conteúdo:
        return

    início_sfv = "SFV = 1.0"
    posição_sfv = conteúdo.find(início_sfv)
    if posição_sfv < 0:
        raise SystemExit(f"Versão pública ausente: {arquivo}")
    fim_sfv = conteúdo.find("\n", posição_sfv)
    conteúdo = (
        conteúdo[:posição_sfv]
        + "# Versão pública do Santafé para caminhos de bibliotecas e ferramentas.\n"
        + "SFV = 1.0"
        + conteúdo[fim_sfv:]
    )

    antigo = "TO_BIN = $(if $(filter mingw,$(AUTO_PLAT)),santafe.exe santafec.exe,santafé santafec)\nTO_INC = lua.h luaconf.h lualib.h lauxlib.h lua.hpp\nTO_LIB = liblua.a"
    novo = "TO_BIN = $(if $(filter mingw,$(AUTO_PLAT)),santafe.exe santafec.exe,santafé santafec santafé-sls)\nTO_INC = lua.h luaconf.h lualib.h lauxlib.h lua.hpp\nTO_LIB = liblua.a\nSLS_FONTE = ferramentas/sls/sls.fé\nSLS_INICIALIZADOR = ferramentas/sls/santafé-sls\nSLS_INSTALADO = $(INSTALL_TOP)/share/santafé/$(SFV)/ferramentas/sls.fé"
    conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)

    antigo = "\tcd src && $(INSTALL_DATA) $(TO_LIB) $(INSTALL_LIB)\n"
    novo = antigo + "\t$(MKDIR) \"$$(dirname \"$(SLS_INSTALADO)\")\"\n\t$(INSTALL_DATA) \"$(SLS_FONTE)\" \"$(SLS_INSTALADO)\"\n"
    conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)

    antigo = "\tcd src && cd $(INSTALL_LIB) && $(RM) $(TO_LIB)\n"
    novo = antigo + "\t$(RM) \"$(SLS_INSTALADO)\"\n"
    conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)

    antigo = "\tcbin:\n"
    if antigo in conteúdo:
        raise SystemExit(f"Makefile malformado: {arquivo}")
    antigo = "cbin:\n\t@printf \"$(LARANJA_ESCURO)==> Compilando núcleo Santafé (plataforma $(AUTO_PLAT))...$(RESET)\\n\"\n\t@cd src && $(MAKE) $(AUTO_PLAT)\n"
    novo = antigo + "\t@$(MAKE) sls\n\n# O SLS é escrito em Santafé e distribuído com um inicializador pequeno. Ele\n# sempre chama o executável Santafé instalado ao lado, evitando divergência de\n# versão entre o servidor de linguagem e o núcleo.\nsls:\n\t@cp \"$(SLS_INICIALIZADOR)\" \"src/santafé-sls\"\n\t@chmod 0755 \"src/santafé-sls\"\n"
    conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)

    antigo = "\t@printf \"$(LARANJA_ESCURO)✅ Santafé instalado com sucesso.$(RESET)\\n\"\n\n# Instala as bibliotecas C (.so)"
    novo = "\t@printf \"$(LARANJA_ESCURO)✅ Santafé instalado com sucesso.$(RESET)\\n\"\n\nisls:\n\t@printf \"$(LARANJA_ESCURO)==> Instalando SLS em $(SLS_INSTALADO)...$(RESET)\\n\"\n\t@if [ -z \"$(SUDO_OU_SU)\" ]; then \\\n\t    $(MKDIR) \"$$(dirname \"$(SLS_INSTALADO)\")\"; \\\n\t    $(INSTALL_DATA) \"$(SLS_FONTE)\" \"$(SLS_INSTALADO)\"; \\\n\telif [ \"$(SUDO_OU_SU)\" = \"sudo\" ]; then \\\n\t    sudo $(MKDIR) \"$$(dirname \"$(SLS_INSTALADO)\")\"; \\\n\t    sudo $(INSTALL_DATA) \"$(SLS_FONTE)\" \"$(SLS_INSTALADO)\"; \\\n\telse \\\n\t    $(SUDO_OU_SU) '$(MKDIR) \"$(INSTALL_TOP)/share/santafé/$(SFV)/ferramentas\"'; \\\n\t    $(SUDO_OU_SU) '$(INSTALL_DATA) \"$(SLS_FONTE)\" \"$(SLS_INSTALADO)\"'; \\\n\tfi\n\t@printf \"$(LARANJA_ESCURO)✅ SLS instalado. Use santafé-sls como servidor LSP.$(RESET)\\n\"\n\n# Instala as bibliotecas C (.so)"
    conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)

    antigo = "\t@cd src && $(MAKE) clean > /dev/null 2>&1\n"
    novo = antigo + "\t@$(RM) \"src/santafé-sls\"\n"
    conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)

    antigo = "\t    $(MAKE) ibin && \\\n"
    novo = "\t    $(MAKE) ibin && \\\n\t    $(MAKE) isls && \\\n"
    conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)

    antigo = "\t    cd $(INSTALL_LIB) && $(RM) $(TO_LIB) || true; \\\n\telif [ \"$(SUDO_OU_SU)\" = \"sudo\" ]; then \\\n\t    sudo rm -f $(INSTALL_BIN)/$(TO_BIN) $(INSTALL_INC)/$(TO_INC) $(INSTALL_LIB)/$(TO_LIB) || true; \\\n\telse \\\n\t    $(SUDO_OU_SU) ' rm -f $(INSTALL_BIN)/$(TO_BIN) $(INSTALL_INC)/$(TO_INC) $(INSTALL_LIB)/$(TO_LIB) ' || true; \\\n"
    novo = "\t    cd $(INSTALL_LIB) && $(RM) $(TO_LIB) || true; \\\n\t    $(RM) \"$(SLS_INSTALADO)\" || true; \\\n\telif [ \"$(SUDO_OU_SU)\" = \"sudo\" ]; then \\\n\t    sudo rm -f $(INSTALL_BIN)/$(TO_BIN) $(INSTALL_INC)/$(TO_INC) $(INSTALL_LIB)/$(TO_LIB) \"$(SLS_INSTALADO)\" || true; \\\n\telse \\\n\t    $(SUDO_OU_SU) ' rm -f $(INSTALL_BIN)/$(TO_BIN) $(INSTALL_INC)/$(TO_INC) $(INSTALL_LIB)/$(TO_LIB) \"$(SLS_INSTALADO)\" ' || true; \\\n"
    conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)

    antigo = "        ideps cbin cbibc ibin ibibc ibibf instalar-pc pc \\\n"
    novo = "        ideps cbin cbibc ibin isls ibibc ibibf instalar-pc pc sls \\\n"
    conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)
    grave(arquivo, conteúdo)


def atualize_cjson(raiz: Path) -> None:
    arquivo = raiz / "src/lua_cjson.c"
    conteúdo = leia(arquivo)
    if "json_empty_array_marker" in conteúdo:
        return

    antigo = "static const char *char2escape[256] = {"
    novo = "/* Marcador público para uma matriz JSON vazia. Uma tabela vazia não contém\n * informação suficiente para o serializador distinguir {} de []; quem precisa\n * declarar a segunda forma usa json.matrizVazia. */\nstatic char json_empty_array_marker;\n\nstatic const char *char2escape[256] = {"
    conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)

    antigo = "    case LUA_TLIGHTUSERDATA:\n        if (lua_touserdata(l, -1) == NULL) {"
    novo = "    case LUA_TLIGHTUSERDATA:\n        if (lua_touserdata(l, -1) == (void *)&json_empty_array_marker) {\n            strbuf_append_mem(json, \"[]\", 2);\n            break;\n        }\n        if (lua_touserdata(l, -1) == NULL) {"
    conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)

    antigo = "    lua_setfield(l, -2, \"valorNulo\");\n"
    novo = "    lua_setfield(l, -2, \"valorNulo\");\n\n    lua_pushlightuserdata(l, (void *)&json_empty_array_marker);\n    lua_setfield(l, -2, \"matrizVazia\");\n"
    conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)
    grave(arquivo, conteúdo)


def atualize_testes(raiz: Path) -> None:
    arquivo = raiz / "testar.sh"
    conteúdo = leia(arquivo)
    if "testar_sls.py" not in conteúdo:
        antigo = "\necho \"✅ Todos os testes disponíveis passaram.\""
        novo = "\necho \"==> Validando o Servidor de Linguagem Santafé\"\npython3 ./testes/integracao/testar_sls.py\n" + antigo
        conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)
        grave(arquivo, conteúdo)

    arquivo = raiz / ".gitignore"
    conteúdo = leia(arquivo)
    if "src/santafé-sls" not in conteúdo:
        conteúdo = substitua_uma_vez(
            arquivo,
            conteúdo,
            "src/santafé\n",
            "src/santafé\nsrc/santafé-sls\n",
        )
        grave(arquivo, conteúdo)


def atualize_documentação(raiz: Path) -> None:
    arquivo = raiz / "CHANGELOG.md"
    conteúdo = leia(arquivo)
    if "SLS 0.1.0" not in conteúdo:
        antigo = "### Incluído\n"
        novo = "### Incluído\n\n- SLS 0.1.0: servidor de linguagem Santafé por LSP/stdio, com sincronização\n  integral de documentos e diagnósticos sintáticos em tempo real. É distribuído\n  pelo comando `santafé-sls` junto com o núcleo.\n- `json.matrizVazia`, marcador explícito para codificar uma matriz JSON vazia\n  (`[]`) sem confundi-la com o objeto vazio (`{}`).\n"
        conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)
        grave(arquivo, conteúdo)

    arquivo = raiz / "README.md"
    conteúdo = leia(arquivo)
    if "santafé-sls" not in conteúdo:
        antigo = "\n## Bibliotecas\n"
        novo = "\n## Servidor de Linguagem (SLS)\n\nO editor inicia `santafé-sls` localmente por `stdio`. A primeira versão acompanha\na abertura, edição e salvamento dos arquivos e mostra diagnósticos sintáticos sem\nexecutar o programa. Veja [SLS](docs/SLS.md).\n" + antigo
        conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)
        grave(arquivo, conteúdo)

    arquivo = raiz / "README.en.md"
    conteúdo = leia(arquivo)
    if "santafé-sls" not in conteúdo:
        antigo = "\n## Libraries\n"
        novo = "\n## Santafé Language Server (SLS)\n\nEditors start `santafé-sls` locally over `stdio`. Its first version tracks open,\nchange, and save events and reports syntax diagnostics without executing the\nedited program. See [SLS](docs/SLS.md).\n" + antigo
        conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)
        grave(arquivo, conteúdo)

    arquivo = raiz / "site-sfdev/manual.html"
    conteúdo = leia(arquivo)
    if "json.matrizVazia" not in conteúdo:
        antigo = "<div class=\"sf-nota\"><code>nulo</code> numa tabela Santafé remove aquela chave; por isso <code>json.valorNulo</code> preserva explicitamente um valor JSON <code>null</code>.</div>"
        novo = "<div class=\"sf-nota\"><code>nulo</code> numa tabela Santafé remove aquela chave; por isso <code>json.valorNulo</code> preserva explicitamente um valor JSON <code>null</code>. Uma tabela vazia codifica como <code>{}</code>; quando o protocolo exigir explicitamente a matriz vazia <code>[]</code>, use <code>json.matrizVazia</code>.</div>"
        conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)

        antigo = "Tabelas sequenciais viram matrizes; tabelas com chaves em colar viram objetos. Referências circulares"
        novo = "Tabelas sequenciais viram matrizes; tabelas com chaves em colar viram objetos. Como uma tabela vazia não revela sua intenção, ela vira <code>{}</code>; use <code>json.matrizVazia</code> para emitir <code>[]</code>, por exemplo em campos de listas vazias de protocolos. Referências circulares"
        conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)
        grave(arquivo, conteúdo)

    conteúdo = leia(arquivo)
    if 'id="notas-sls"' not in conteúdo:
        antigo = '                <h3 id="notas-bibliotecas">Bibliotecas carregadas automaticamente</h3>'
        novo = '                <h3 id="notas-sls">Servidor de Linguagem (SLS)</h3>\n                <p>O <code>santafé-sls</code> é iniciado localmente pelo editor e conversa por entrada e saída padrão usando LSP (JSON-RPC 2.0). Ele não abre porta de rede, não transmite o fonte a terceiros e não executa o programa que está sendo editado.</p>\n                <div class="sf-nota">Nesta primeira versão, o SLS acompanha abertura, edição e salvamento de documentos e informa erros sintáticos em tempo real. Autocompletar, navegação para definição, referências, símbolos, formatação e depuração dependem da futura camada semântica.</div>\n\n' + antigo
        conteúdo = substitua_uma_vez(arquivo, conteúdo, antigo, novo)
        grave(arquivo, conteúdo)


def principal() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raiz", type=Path)
    args = parser.parse_args()
    raiz = args.raiz.resolve()
    if not (raiz / "src/lua_cjson.c").is_file():
        raise SystemExit(f"Raiz Santafé inválida: {raiz}")

    atualize_makefile(raiz)
    atualize_cjson(raiz)
    atualize_testes(raiz)
    atualize_documentação(raiz)
    print("SLS_0_1_0_FONTE_ATUALIZADO")


if __name__ == "__main__":
    principal()
