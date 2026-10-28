#!/usr/bin/env python3
"""Sela entrega já conferida; não publica nem transfere nada."""
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1]).resolve()
assert out.name=='candidato-dados-v7' and out.parent.name=='dist'
archive=out/'santafe-candidato-dados.7-fontes.tar.gz'
assert archive.is_file() and (out/'wasm/santafe.wasm').is_file()
checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
for platform in ('macos','debian'):
    evidence=out/'evidencias'/platform
    assert json.loads((evidence/'onfe-persistencia7.json').read_text())['grupos']==17
    assert json.loads((evidence/'onfe-persistencia7.json').read_text())['passou']
    assert json.loads((evidence/'onfe-persistencia7-asan.json').read_text())['passou']
    assert all(x['codigo']==0 for x in json.loads((evidence/'dados7-regressao.json').read_text()))
    assert len(json.loads((evidence/'aplicativos5.json').read_text())['passaram'])==13
    assert json.loads((evidence/'carga6.json').read_text())['resultado']=='PASSOU'
delivery=f'''# Entrega dados.7 — somente homologação

Fontes: `{archive.name}`
SHA-256: `{checksum}`

Servidor: `/tmp/santafe-dados7.1S7FpWIE`.
`arvore` contém a construção testada; `entrega` contém os fontes selados,
sem executáveis instalados. Nenhum arquivo de produção foi substituído.

Para conferir os fontes recebidos, **sem publicar**:

```sh
cd /tmp/santafe-dados7.1S7FpWIE/entrega
python3 experimentos/dados-v3/conferir-fontes.py
```

Esta entrega não contém publicador de produção. Consulte RELATORIO.md e
PERSISTENCIA.md para resultados, limites e gates de estabilização restantes.
'''
(out/'ENTREGA.md').write_text(delivery)
files=sorted(p for p in out.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
assert not any(p.is_symlink() for p in files)
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(out))+'\n' for p in files))
print(checksum,len(files),'arquivos selados')
