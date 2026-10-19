"""Execute com runpy.run_path na console do Sublime, não no Python do sistema.

Usa a gramática instalada do pacote Santafe em uma visão sintética temporária.
Não modifica arquivos, preferências ou documentos do usuário.
"""
import json
import os
from pathlib import Path
import sublime

if not __debug__:
    raise RuntimeError('Execute com compile(..., optimize=0): o plugin_host usa Python -O.')

casos = json.loads((Path(__file__).resolve().parents[2] / "testes/realce.json").read_text(encoding="utf-8"))
for caso in casos:
    if caso.get("arquivo"):
        caso["fonte"] = (Path(__file__).resolve().parents[2] / "testes" / caso["arquivo"]).read_text(encoding="utf-8")
visão = sublime.active_window().new_file()
visão.set_scratch(True)
visão.assign_syntax("Packages/Santafe/Santafe.sublime-syntax")
texto = ""
for caso in casos:
    caso["offset"] = len(texto)
    texto += caso["fonte"] + "\n\n"
visão.run_command("append", {"characters": texto})


def confira():
    falhas = []
    for caso in casos:
        posição = -1
        for _ in range(caso.get("ocorrencia", 1)):
            posição = caso["fonte"].find(caso["trecho"], posição + 1)
        if posição < 0:
            falhas.append((caso["nome"], "trecho ausente"))
            continue
        for deslocamento in range(len(caso["trecho"])):
            escopo = visão.scope_name(caso["offset"] + posição + deslocamento)
            ok = (not caso.get("tem") or caso["tem"] in escopo)
            ok = ok and (not caso.get("nao") or caso["nao"] not in escopo)
            ok = ok and (not caso.get("tem_um") or any(s in escopo for s in caso["tem_um"]))
            if not ok:
                falhas.append((caso["nome"], deslocamento, escopo))
    visão.close()
    resultado = os.environ.get("SANTAFE_TESTE_REALCE_SAIDA")
    if resultado:
        Path(resultado).write_text(json.dumps({"casos": len(casos), "falhas": falhas}, ensure_ascii=False, indent=2))
    assert not falhas, falhas
    print("Sublime real: {} casos de interpolação, HTML, JS e isolamento: ok".format(len(casos)))


sublime.set_timeout(confira, 600)
