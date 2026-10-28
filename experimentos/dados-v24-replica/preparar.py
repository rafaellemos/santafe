#!/usr/bin/env python3
"""Prepara apenas os ensaios24 sobre a fonte23 selada; núcleo inalterado."""
import argparse, hashlib, json, shutil, tarfile
from pathlib import Path, PurePosixPath

BASE = '17480441b23708d53b3e6c421498eb92bebdf632f857a4a235c5296ca0fd0b65'
HERE = Path(__file__).resolve().parent

def prepare(archive, dest):
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == BASE
    assert not dest.exists() and not dest.is_symlink()
    with tarfile.open(archive) as t:
        rows = {}
        for m in t:
            p = PurePosixPath(m.name)
            assert m.isfile() and not p.is_absolute() and '..' not in p.parts
            assert str(p) == m.name and m.name not in rows and m.size < 32*1024**2
            rows[m.name] = (t.extractfile(m).read(), m.mode & 0o755)
    manifest = json.loads(rows['MANIFESTO-FONTES.json'][0])
    assert len(manifest) == 897
    assert manifest == {n:hashlib.sha256(b).hexdigest() for n,(b,_) in rows.items() if n!='MANIFESTO-FONTES.json'}
    dest.mkdir(mode=0o700, parents=True)
    for n,(b,mode) in rows.items():
        p=dest/n; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b); p.chmod(mode)
    out=dest/'experimentos/dados-v24-replica'; out.mkdir()
    for p in HERE.iterdir():
        if p.is_file() and p.suffix in ('.py','.md'):
            shutil.copy2(p,out/p.name)
    # A receita histórica permanece intacta. Esta cópia tem as adaptações
    # explícitas de layout24; conteúdo operacional será revisto separadamente.
    text=(dest/'experimentos/dados-v12/migrar-replica.py').read_text()
    def replace(old,new,count=1):
        nonlocal text
        assert text.count(old)==count, repr(old)
        text=text.replace(old,new)
    replace("spec=importlib.util.spec_from_file_location('verifica',HERE/'verificar-replica.py')",
            "spec=importlib.util.spec_from_file_location('verifica',HERE.parent/'dados-v12/verificar-replica.py')")
    replace("bib=cand/'local/share/santafé/1.0/bibf'", "bib=cand/'local/share/santafé/3.0/bibf'")
    replace("   shutil.copyfile(source,cand/f'local/lib/santafé/1.0/bibc/{lib}.so')",
            "   target=cand/f'local/lib/santafé/3.0/bibc/{lib}.so'; target.parent.mkdir(parents=True,exist_ok=True)\n   shutil.copyfile(source,target)")
    replace('0.0.0-dados.12','3.0.0-rc.1',2)
    replace('1.0.0-dados.12','1.1.0-rc.1',2)
    start=text.index('  # Limite expirado é remoção')
    end=text.index("  for kind in ('estavel','candidata'):",start)
    text=text[:start]+'  self.adjust_operational(cand)\n'+text[end:]
    replace("'--innodb-buffer-pool-size=128M'", "'--innodb-buffer-pool-size=64M','--innodb-log-file-size=16M'")
    (out/'replica-base.py').write_text(text)
    shutil.copy2(dest/'experimentos/dados-v23-distribuicao/transacao.py',out/'transacao.py')
    shutil.copy2(dest/'experimentos/dados-v23-distribuicao/testar-transacao.py',out/'testar-transacao.py')
    # DNS tem configurações Fé próprias; nenhuma chave/certificado vira destino.
    p=out/'transacao.py'; text=p.read_text()
    old="or parts[:2] in (('etc', 'santafe'), ('etc', 'paodocafe')))"
    new="or parts[:2] in (('etc', 'santafe'), ('etc', 'paodocafe'))\n                   or (parts[:2] in (('etc', 'santafe-nomes'), ('etc', 'santafe-dns'))\n                       and p.suffix in ('.fé', '.env')))"
    assert text.count(old)==1; p.write_text(text.replace(old,new))
    (dest/'.laboratorio-dados24').write_text('Ensaio operacional isolado; núcleo23 preservado.\n')
    print(dest)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('base',type=Path);p.add_argument('destino',type=Path)
    a=p.parse_args();prepare(a.base,a.destino.absolute())
