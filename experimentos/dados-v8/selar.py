#!/usr/bin/env python3
"""Sela apenas após conferir resultados; não instala ou publica."""
from pathlib import Path
import hashlib,json,sys,zipfile
out=Path(sys.argv[1]).resolve()
assert out.name=='candidato-dados-v8' and out.parent.name=='dist'
archive=out/'santafe-candidato-dados.8-fontes.tar.gz'
assert archive.is_file() and (out/'wasm/santafe.wasm').is_file()
for platform in ('macos','debian'):
    evidence=out/'evidencias'/platform
    tests=json.loads((evidence/'dados7-regressao.json').read_text())
    assert len(tests)==11 and all(t['codigo']==0 for t in tests)
    assert len(json.loads((evidence/'dados8-fontes.json').read_text()))==183
    assert len(json.loads((evidence/'aplicativos5.json').read_text())['passaram'])==13
    assert json.loads((evidence/'onfe-persistencia7.json').read_text())['passou']
    log=(evidence/'dados8-colares.log').read_text()
    assert 'Ran 14 tests' in log and '\nOK\n' in log
assert '18 casos + recuperação após erro: ok' in (out/'evidencias/debian/dados8-wasm-reteste.log').read_text()
assert json.loads((out/'evidencias/macos/dados8-sls-aceitacao.json').read_text())['resumo']['totais']=={'OK':39,'FALHA':0,'PENDENTE':0}
assert 'TEXTMATE_DELIMITADORES8_OK 45' in (out/'evidencias/macos/dados8-editores.log').read_text()
with zipfile.ZipFile(out/'editores/santafe-dados-experimental-0.0.8.vsix') as z:
    manifest=json.loads(z.read('extension/package.json'))
    assert manifest['version']=='0.0.8' and manifest['name']=='santafe-dados-experimental'
with zipfile.ZipFile(out/'editores/SantafeDados.sublime-package') as z:
    assert "- match: '\\[(=+)\\['" in z.read('Santafe-Dados.sublime-syntax').decode()
sha=hashlib.sha256(archive.read_bytes()).hexdigest()
(out/'ENTREGA.md').write_text('''# Candidato dados.8 — somente laboratório

Nenhum publicador de produção. Fonte estável, serviços e perfis dos editores
não foram substituídos. O executável nativo deve ser compilado em árvore/prefixo
privado; não instalar sobre a Santafé 2.1.0.

Fontes: `santafe-candidato-dados.8-fontes.tar.gz`
SHA-256: `'''+sha+'''`

Kits isolados: VS Code 0.0.8 e SantafeDados.sublime-package. Não são versões
novas do Marketplace nem do Package Control. WASM candidato em `wasm/`.

Servidor de ensaio: `/tmp/santafe-dados8.fhLMCQzP`. Dados empresariais não
foram acessados. RELATORIO.md distingue testes executados de gates pendentes.

Para conferir os fontes após extração, sem publicar:

```sh
python3 experimentos/dados-v3/conferir-fontes.py
```

Siga LEIA-ME.md para construir/testar. SHA256SUMS cobre todos os artefatos
desta entrega; os relatórios históricos mantêm seus nomes originais.
''')
files=sorted(p for p in out.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
assert not any(p.is_symlink() for p in files)
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(out))+'\n' for p in files))
print('DADOS8_SELADO',sha,len(files),'arquivos')
