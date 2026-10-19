"""Casos adicionais, executados sobre o motor HTML/JS do Sublime instalado."""
def casos():
    resultado = []
    def adicione(fonte, trecho, tem=None, ocorrencia=1):
        resultado.append(dict(nome=trecho + " / " + str(len(resultado)), fonte=fonte,
                              trecho=trecho, tem=tem, ocorrencia=ocorrencia))
    html = 'local a = [[<b class="cl-]] .. web.escapeHTML(nome) .. [[resto">Olá</b>]]; mostre(a)'
    for trecho, escopo in [("cl-", "string.quoted.double.html"), ("resto", "string.quoted.double.html"),
                           ("web.escapeHTML(nome)", None), ("mostre", None), ("]] ..", None)]:
        adicione(html, trecho, escopo)
    js = 'local a = --[[javascript]] [[/* começo ]] .. nome .. [[ continuação */ const n=1;]]; mostre(a)'
    for trecho, escopo in [("começo", "comment.block.js"), ("continuação", "comment.block.js"),
                          ("const", "keyword.declaration.js"), ("nome", None), ("mostre", None)]:
        adicione(js, trecho, escopo)
    linha = 'local a = --[[javascript]] [[// antes ]] .. -- comentário do Santafé\n valor .. [[depois\nconst fim=1;]]'
    adicione(linha, "depois", "comment.line")
    adicione(linha, "const", "keyword.declaration.js")
    adicione(linha, "comentário do Santafé")
    for n in [1, 3, 100]:
        e = "=" * n
        s = 'local a = ['+e+'[<b title="x]] ]'+e+'=] ]'+e+"] .. chamada('ignorado') .. ["+e+'[ fim">é🟢</b>]'+e+']; mostre(a)'
        adicione(s, "fim", "string.quoted.double.html")
        adicione(s, "chamada('ignorado')")
        adicione(s, "mostre")
    adicione('local a = --[[html]] "<b title=\\\"" .. nome .. "fim\\\">Olá</b>"', "fim", "string.quoted.double.html")
    adicione("local a = --[[html]] '<b title=\"' .. nome .. 'fim\">Olá</b>'", "fim", "string.quoted.double.html")
    adicione('local a = [[<script>/* parte ]] .. nome .. [[ final */ const n=1;</script>]]', "final", "comment.block.js")
    adicione('local a = [[<script>/* parte ]] .. nome .. [[ final */ const n=1;</script>]]', "const", "keyword.declaration.js")
    adicione('local a = [[<!-- parte ]] .. nome .. [[ final --><h1>Oi</h1>]]', "final", "comment.block.html")
    adicione('local a = ([[<b title="]] .. (nome ou padrão)) .. [[fim">Oi</b>]]', "fim", "string.quoted.double.html")
    adicione('local a = [[<b title="]] .. web.escapeHTML(nome):troque("x", "y") .. [[fim">Oi</b>]]', "fim", "string.quoted.double.html")
    adicione('local a = [[<b title="]] .. valores[índice + 1] .. [[fim">Oi</b>]]', "fim", "string.quoted.double.html")
    adicione('local a = [[<b title="]] .. -- comentário\n nome .. [[fim">Oi</b>]]', "fim", "string.quoted.double.html")
    adicione('local a = [[<b title="x]] .. (n + 1) .. [[fim">Oi</b>]]', "fim", "string.quoted.double.html")
    adicione('local a = [[<b title="x]] .. nome .. [====[fim">Oi</b>]====]', "fim", "string.quoted.double.html")
    for marca in ["®", "Ⓡ"]:
        s = 'local a = `<b title="'+marca+"nome "+marca+"{obj({nome='}'})}"+' fim">Oi</b>`'
        adicione(s, marca+"nome")
        adicione(s, marca+"{obj({nome='}'})}")
        adicione(s, "fim", "string.quoted.double.html")
    adicione('local a = [[<b title="incompleto]]; mostre("não é atributo")', "não é atributo")
    adicione('-- local falso = [[<b title="x">]]\nlocal real = "comum"', "title")
    adicione('local a = [[<b title="x]] .. nome .. [[fim">]]\nlocal z = "comum"', "comum")
    adicione('local a = --[[html]] "<b title=\\\"🟢" .. nome .. "fim\\\">Olá</b>"\r\nmostre(a)', "fim", "string.quoted.double.html")
    return resultado
