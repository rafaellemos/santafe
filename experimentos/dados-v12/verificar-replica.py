#!/usr/bin/env python3
"""Validação da cópia privada. Não inicia aplicativos nem executa configurações."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, os, stat

def resumo(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def arquivo_privado(path):
 st=path.lstat()
 if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.geteuid() or st.st_mode&0o077:
  raise ValueError('arquivo não regular, alheio ou exposto')

def conferir(root):
 if root.is_symlink() or root.parent!=Path('/var/tmp') or not root.name.startswith('santafe-replica-dados10-'):
  raise ValueError('diretório de réplica inesperado')
 st=root.stat()
 if st.st_uid!=os.geteuid() or st.st_mode&0o077:raise ValueError('cópia não privada')
 for n in ('.replica-privada','PRONTO_PARA_ADAPTAR','manifesto.json','bancos.sql','unidades.json'):arquivo_privado(root/n)
 m=json.loads((root/'manifesto.json').read_text())
 if m['formato']!=1 or set(m['bancos'])!={'santafe_comunidade','paodocafe'}:raise ValueError('réplica exige ambos os bancos isolados')
 if resumo(root/'bancos.sql')!=m['sql_sha256']:raise ValueError('dump divergente')
 for name,info in m['arquivos'].items():
  rel=PurePosixPath(name)
  if rel.is_absolute() or '..' in rel.parts or str(rel)!=name:raise ValueError('caminho inválido')
  f=root/'arquivos'/name
  for parent in [f.parent,*list(f.parents)[:len(rel.parts)]]:
   if parent.is_symlink():raise ValueError('diretório simbólico recusado')
  arquivo_privado(f)
  if f.stat().st_size!=info['tamanho'] or resumo(f)!=info['sha256']:raise ValueError('arquivo divergente: '+name)
 required=('usr/local/bin/santafé','usr/local/bin/santafec','opt/sfdev.fé')
 if not all(n in m['arquivos'] for n in required):raise ValueError('núcleo/portal ausente')
 for prefix in ('opt/carteiro/','opt/correio/','opt/paodocafe/','usr/local/share/santafé/1.0/','etc/paodocafe/','etc/santafe/'):
  if not any(n.startswith(prefix) for n in m['arquivos']):raise ValueError('árvore obrigatória ausente: '+prefix)
 units=json.loads((root/'unidades.json').read_text())
 for unit in ('sfdev.service','correio-imap.service','correio-recebedor.service','carteiro.service','carteiro-paodocafe.service','paodocafe.service'):
  if unit not in units:raise ValueError('unidade ausente: '+unit)
 return m

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('replica',type=Path);a=p.parse_args()
 m=conferir(a.replica.absolute());print('REPLICA_ARQUIVOS_INTEGROS',len(m['arquivos']),'arquivos; 2 bancos; restauração/objetos/aplicativos ainda pendentes')
