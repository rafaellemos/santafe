#!/usr/bin/env python3
"""Inventário privado da migração. Não executa configurações ou aplicações."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('replica', type=Path)
parser.add_argument('candidato', type=Path)
parser.add_argument('--estavel', type=Path, default=Path('/usr/local/bin/santafé'))
args = parser.parse_args()
source = args.candidato.resolve()
assert (source/'.laboratorio-dados23').is_file()
spec = importlib.util.spec_from_file_location('replica_privada', source/'experimentos/dados-v12/verificar-replica.py')
verify = importlib.util.module_from_spec(spec); spec.loader.exec_module(verify)
manifest = verify.conferir(args.replica.absolute())
env = {'PATH': '/usr/bin:/bin:/usr/local/bin', 'GSETTINGS_BACKEND': 'memory'}
version = subprocess.check_output([str(args.estavel), '-E', '-P', '-v'], env=env, text=True)
assert '2.1.0' in version
os.umask(0o077)
out = Path(tempfile.mkdtemp(prefix='santafe-auditoria23-', dir='/var/tmp'))
rows = []
for name, info in manifest['arquivos'].items():
    if not name.endswith('.fé') or not name.startswith(('opt/', 'etc/', 'usr/local/share/')):
        continue
    original = args.replica/'arquivos'/name
    result = subprocess.run([str(args.estavel), '-E', '-P',
                             str(source/'experimentos/dados-v1/migrar.fé'), str(original)],
                            env=env, capture_output=True, timeout=40)
    # O lexer lê bytes; o arquivo capturado não é carregado nem executado.
    item = {'arquivo': name, 'sha256_origem': info['sha256'],
            'avisos_nulo': result.stderr.count(b'REVISAR'),
            'conversao_lexica': result.returncode == 0}
    if result.returncode == 0:
        item['sha256_convertido'] = hashlib.sha256(result.stdout).hexdigest()
        target = out/'convertidos'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(result.stdout)
        compiled = subprocess.run([str(source/'src/santafec'), '-p', str(target)],
                                  env=env, capture_output=True, timeout=40)
        item['compila'] = compiled.returncode == 0
        if compiled.returncode:
            (out/'diagnostico-privado.log').open('ab').write(compiled.stderr)
    else:
        item['compila'] = False
        (out/'diagnostico-privado.log').open('ab').write(result.stderr)
    provider = None
    mappings = [('usr/local/share/santafé/1.0/bibf/', 'bibs/bibf/'),
                ('opt/correio/', 'aplicativos/correio/'),
                ('opt/carteiro/', 'aplicativos/carteiro/')]
    for old, new in mappings:
        if name.startswith(old):
            candidate = source/(new+name[len(old):])
            if candidate.is_file():
                provider = str(candidate.relative_to(source))
    item['fonte_candidata_correspondente'] = provider
    # Nem compilar nem ter um homônimo prova equivalência operacional.
    item['revisao_semantica_necessaria'] = item['avisos_nulo'] > 0 or not item['compila']
    rows.append(item)
old_paths = []
for name, info in manifest['arquivos'].items():
    if name.startswith(('etc/', 'opt/')) and info['tamanho'] < 4*1024**2:
        data = (args.replica/'arquivos'/name).read_bytes()
        if 'santafé/1.0/'.encode() in data:
            old_paths.append({'arquivo': name, 'sha256': info['sha256']})
needed = sum(v['tamanho'] for n,v in manifest['arquivos'].items() if not n.startswith('var/www/'))*4+2*1024**3
public = {'resultado': 'INVENTARIO_CONCLUIDO_SEM_MIGRACAO', 'fontes': len(rows),
          'compilam_apos_conversao_lexica': sum(x['compila'] for x in rows),
          'atribuicoes_nulo_a_revisar': sum(x['avisos_nulo'] for x in rows),
          'arquivos_com_nulo_a_revisar': sum(x['avisos_nulo'] > 0 for x in rows),
          'arquivos_com_fonte_candidata': sum(x['fonte_candidata_correspondente'] is not None for x in rows),
          'arquivos_com_caminho_antigo': len(old_paths),
          'necessario_bateria_replica_bytes': needed, 'livre_bytes': shutil.disk_usage(out).free,
          'producao_alterada': False, 'nenhum_configurado_executado': True,
          'aplicativos_completos_homologados_nesta_rodada': False}
(out/'inventario-privado.json').write_text(json.dumps({'resumo': public, 'fontes': rows,
    'caminhos_antigos': old_paths}, ensure_ascii=False, indent=2)+'\n')
(out/'resumo.json').write_text(json.dumps(public, ensure_ascii=False, indent=2)+'\n')
print('AUDITORIA23_PRIVADA', out)
print(json.dumps(public, ensure_ascii=False))
