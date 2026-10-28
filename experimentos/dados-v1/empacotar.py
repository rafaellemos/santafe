#!/usr/bin/env python3
"""Pacote local de homologação, com alvos explícitos e sem configurações privadas."""
import hashlib
import json
import pathlib
import tarfile

ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/"dist/candidato-dados-v1"
FILES=[]
for pattern in ("src/*.c","src/*.h","src/Makefile","experimentos/dados-v1/*.fé",
                "experimentos/dados-v1/*.onfé","experimentos/dados-v1/*.sh",
                "experimentos/dados-v1/*.py","experimentos/dados-v1/*.js","experimentos/dados-v1/*.c",
                "experimentos/dados-v1/*.md","dist/candidato-dados-v1/editores/*"):
    FILES.extend(p for p in ROOT.glob(pattern) if p.is_file())
FILES.extend(ROOT/p for p in ("LICENSE","docs/CONTRATO-DADOS-ONFE.md",
    "ferramentas/sls/analisador.fé","dist/candidato-dados-v1/santafé-dados",
    "dist/candidato-dados-v1/santafec-dados",
    "dist/candidato-dados-v1-baseline/santafé-dados",
    "testes/bibf/teste_json.fé","testes/metatabelas.fé",
    "testes/bibf/teste_gabarito_unicode.fé","testes/bibf/teste_sls_analisador.fé",
    "extensões/vscode/syntaxes/santafe.tmLanguage.json"))
FILES=sorted(set(FILES))
assert all(p.is_file() for p in FILES), "artefato ausente"
manifest=OUT/"MANIFESTO.onfé"
entries=[]
for p in FILES:
    name=str(p.relative_to(ROOT))
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    entries.append('{arquivo='+json.dumps(name,ensure_ascii=False)+',sha256="'+digest+'"}')
manifest.write_text('{candidato="dados.1",experimental=verdadeiro,arquivos=['+','.join(entries)+']}\n')
FILES.append(manifest)
archive=OUT/"santafe-candidato-dados.1.tar.gz"
with tarfile.open(archive,"w:gz",format=tarfile.PAX_FORMAT) as tar:
    for p in FILES:
        info=tar.gettarinfo(str(p),arcname="santafe-candidato-dados.1/"+str(p.relative_to(ROOT)))
        info.uid=info.gid=0; info.uname=info.gname=""
        with p.open("rb") as f: tar.addfile(info,f)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
(OUT/"SHA256SUMS").write_text(digest+"  "+archive.name+"\n")
# Verifica o pacote gerado sem extraí-lo sobre a árvore de trabalho.
with tarfile.open(archive) as tar:
    assert len(tar.getmembers())==len(FILES)
    for member,p in zip(tar.getmembers(),FILES):
        assert member.isfile() and not pathlib.PurePosixPath(member.name).is_absolute()
        assert ".." not in pathlib.PurePosixPath(member.name).parts
        assert hashlib.sha256(tar.extractfile(member).read()).digest()==hashlib.sha256(p.read_bytes()).digest()
print(archive)
print("SHA256",digest)
print("ARQUIVOS",len(FILES))
