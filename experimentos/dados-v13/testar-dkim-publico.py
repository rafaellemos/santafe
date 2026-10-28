#!/usr/bin/env python3
"""Leitura privada da réplica; consulta DNS público; exporta somente contagens."""
from pathlib import Path
from email.parser import BytesHeaderParser
import argparse, hashlib, json, os, re, subprocess, time
ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados13').is_file()
p=argparse.ArgumentParser();p.add_argument('indice',type=Path);a=p.parse_args()
paths=json.loads(a.indice.read_text());assert 0<len(paths)<=30
report={'resultado':'INCONCLUSIVO','mensagens':len(paths),'assinaturas':0,
        'assinaturas_expiradas':0,'assinaturas_validade_atual':0,'originais_passaram':0,
        'adulteradas_recusadas':0,'originais_falharam':0,'temporarios':0,'inconclusivos':0,
        'conteudo_exportado':False,'relogio_alterado':False,'mensagens_enviadas':0}
for name in paths:
 f=Path(name).resolve()
 assert str(f).startswith('/var/tmp/santafe-migracao11-') and re.fullmatch('[a-f0-9]{64}',f.name)
 assert f.stat().st_size<20*1024**2
 h=BytesHeaderParser().parsebytes(f.read_bytes())
 for s in h.get_all('DKIM-Signature',[]):
  tags=dict(re.findall(r'(?:^|;)\s*([a-z]+)\s*=\s*([^;]+)',str(s)))
  report['assinaturas']+=1
  report['assinaturas_expiradas' if tags.get('x') and int(tags['x'].strip())<time.time() else 'assinaturas_validade_atual']+=1
 env={k:os.environ[k] for k in ('PATH','LANG','LC_ALL') if k in os.environ}
 env['ENSAIO_MENSAGEM_PRIVADA']=str(f)
 r=subprocess.run([str(ROOT/'src/santafé'),'-E','-P','experimentos/dados-v13/dkim-publico.fé'],cwd=ROOT,env=env,capture_output=True,timeout=45)
 assert r.returncode==0,'verificador falhou; nenhuma mensagem foi exportada'
 marker=r.stdout.strip()
 if marker==b'DKIM_PUBLICO_PASSA_ADULTERACAO_FALHA':
  report['originais_passaram']+=1;report['adulteradas_recusadas']+=1
 elif marker==b'DKIM_PUBLICO_FALHA':report['originais_falharam']+=1
 elif marker==b'DKIM_PUBLICO_TEMPORARIO':report['temporarios']+=1
 else:report['inconclusivos']+=1
if report['originais_passaram']>0:report['resultado']='PASSOU'
(ROOT/'evidencias/dkim13.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report))
