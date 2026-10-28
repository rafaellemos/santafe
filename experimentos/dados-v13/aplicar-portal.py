#!/usr/bin/env python3
"""Correção determinística aplicada SOMENTE à cópia do portal em homologação."""
from pathlib import Path
import hashlib
def corrigir(path):
 path=Path(path).resolve()
 assert str(path).startswith('/tmp/santafe-apps5-') or str(path).startswith('/var/tmp/santafe-migracao11-')
 old=path.read_text()
 assert 'local função estruturaDaImagemCompleta' not in old
 marker='local função salveImagemDaComunidade(arquivoRecebido)\n'
 assert old.count(marker)==1
 code=Path(__file__).with_name('estrutura-upload.fé').read_text()
 assert code.endswith('retorne estruturaDaImagemCompleta\n')
 code=code.removesuffix('retorne estruturaDaImagemCompleta\n')
 text=old.replace(marker,code+'\n'+marker)
 marker='    local extensão = formato == "png" e ".png" ou ".jpg"\n'
 assert text.count(marker)==1
 text=text.replace(marker,'    se não estruturaDaImagemCompleta(dados, formato) então\n        retorne nulo, "estrutura da imagem inválida ou incompleta"\n    fim\n\n'+marker)
 path.write_text(text)
 return {'antes':hashlib.sha256(old.encode()).hexdigest(),'depois':hashlib.sha256(text.encode()).hexdigest()}
