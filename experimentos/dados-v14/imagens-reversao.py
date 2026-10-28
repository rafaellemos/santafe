#!/usr/bin/env python3
"""Complementa a reversão: leitura HTTPS dos uploads, somente na réplica encerrada."""
from pathlib import Path
import argparse,fcntl,hashlib,http.client,importlib.util,json,os,shutil,ssl,subprocess,sys,time,traceback,urllib.parse
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('carga14',HERE/'carga-base.py');B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B);M=B.M
class Ensaio(B.Carga):
 def passed(self,name,**values):
  self.results.append({'grupo':name,**values});print('PASSOU',name,values,flush=True)
  M.write(self.lab/'imagens-reversao14.json',self.report)
 def setup_images(self):
  rel=Path('var/www/santafé.dev.br/estático/comunidade/imagens')
  shared=self.lab/'imagens14-servidas';shared.mkdir(mode=0o700,exist_ok=True)
  self.synthetic={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.lab/'candidata/tmp/imagens14').iterdir() if p.is_file()}
  assert self.synthetic,'nenhuma imagem criada pelo ensaio'
  expected={}
  for source in (self.root/rel,self.lab/'candidata/tmp/imagens14'):
   for p in source.iterdir():
    assert p.is_file() and not p.is_symlink(),'imagem exige revisão'
    h=hashlib.sha256(p.read_bytes()).hexdigest();dest=shared/p.name
    if dest.exists():assert hashlib.sha256(dest.read_bytes()).hexdigest()==h,'colisão de arquivo'
    else:shutil.copy2(p,dest)
    expected[p.name]=h
  assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in shared.iterdir()}==expected
  for kind in ('candidata','estavel'):
   target=self.lab/kind/rel
   assert target.is_dir()
   self.run(['mount','--bind',shared,target]);self.run(['mount','-o','remount,bind,ro',target])
  self.shared=shared;self.images=expected
  self.passed('imagens capturadas e novos uploads preservados em cópia privada',arquivos=len(expected),novas=len(self.synthetic))
 def check(self,kind):
  g=self.lab/kind;env=self.env_unit(g,'sfdev.service')
  app=self.start('imagem-'+kind,self.command(g,entry='sfdev.fé'),env,g/'opt');self.wait(app,17000)
  token=self.tokens[(M.DBS[0],self.owners[M.DBS[0]])]
  posts=self.sql('SELECT id,imagem_arquivo FROM publicacoes WHERE imagem_arquivo IN ('+','.join(M.quote(n) for n in self.synthetic)+');',M.DBS[0]).splitlines()
  assert posts,'uploads sem referência no banco'
  for row in posts:
   pid,name=row.split('\t');assert pid.isdigit() and name in self.synthetic
   for _ in range(100):
    status,page=self.http(17000,'/comunidade/postagens/'+pid,token)
    if status==200:break
    time.sleep(.1)
   assert status==200 and name.encode() in page,'postagem não referencia upload novo'
  nginx=self.start('imagem-nginx-'+kind,['/usr/sbin/chroot',str(g),'/usr/sbin/nginx','-g','daemon off;'],M.BASE_ENV,g/'opt');self.wait(nginx,443)
  ctx=ssl.create_default_context(cafile=str(g/'etc/ssl/certs/ca-certificates.crt') if kind=='candidata' else str(self.stage/'testes/recursos/tls-local-certificado.pem'))
  if kind=='candidata':
   original=ctx.wrap_socket
   def wrap(*args,**kw):kw['server_hostname']=M.DOMS[0];return original(*args,**kw)
   ctx.wrap_socket=wrap
  for name,h in self.images.items():
   c=http.client.HTTPSConnection('127.0.0.1',443,timeout=10,context=ctx)
   c.request('GET',urllib.parse.quote('/estático/comunidade/imagens/'+name),headers={'Host':M.DOMS[0]})
   r=c.getresponse();data=r.read();c.close()
   assert r.status==200 and hashlib.sha256(data).hexdigest()==h,'imagem inacessível ou alterada por HTTPS'
  self.stop([nginx,app]);self.passed(kind+': página referencia upload e HTTPS entrega bytes íntegros',imagens=len(self.images))
 def execute(self):
  self.reuse();self.setup_images();before=self.tables();self.check('candidata');self.check('estavel')
  assert self.tables()==before
  assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.shared.iterdir()}==self.images
  self.passed('leitura após reversão preserva bancos e imagens');self.report['resultado']='PASSOU'
def main():
 p=argparse.ArgumentParser();p.add_argument('--lab',type=Path,required=True);p.add_argument('--replica',type=Path,required=True);p.add_argument('--candidato',type=Path,required=True);p.add_argument('--interior',action='store_true');a=p.parse_args()
 assert a.lab.name.startswith('santafe-migracao11-') and a.lab.parent==Path('/var/tmp')
 assert json.loads((a.lab/'resultado-dados14.json').read_text())['resultado']=='PASSOU','aguarde encerramento aprovado do conjunto'
 assert (a.candidato/'.laboratorio-dados14').is_file()
 if not a.interior:
  lock=(a.lab/'execucao14.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  env=dict(M.BASE_ENV,SANTAFE_NET_ORIGEM=os.readlink('/proc/self/ns/net'));os.nice(15)
  raise SystemExit(subprocess.call(['unshare','--user','--map-root-user','--mount','--net','--pid','--fork',sys.executable,str(Path(__file__).resolve()),*sys.argv[1:],'--interior'],env=env))
 assert os.getpid()==1 and os.readlink('/proc/self/ns/net')!=os.environ['SANTAFE_NET_ORIGEM']
 assert {q['ifname'] for q in json.loads(subprocess.check_output(['ip','-j','link']))}=={'lo'}
 subprocess.run(['ip','link','set','lo','up'],check=True);os.umask(0o077);x=Ensaio(a)
 try:x.execute()
 except BaseException as e:
  x.report.update(resultado='FALHOU',falha=type(e).__name__+': '+str(e));(x.lab/'imagens-reversao14-rastro-privado.txt').write_text(traceback.format_exc());print('FALHOU',type(e).__name__,flush=True)
 finally:
  x.stop(x.procs)
  for h in x.handles:h.close()
  M.write(x.lab/'imagens-reversao14.json',x.report)
 if x.report['resultado']!='PASSOU':raise SystemExit(1)
if __name__=='__main__':main()
