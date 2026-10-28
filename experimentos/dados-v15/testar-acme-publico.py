#!/usr/bin/env python3
"""Ensaios adversariais do publicador; nenhum pedido a uma CA pública."""
from pathlib import Path
import contextlib,http.server,importlib.util,json,os,shutil,socketserver,subprocess,sys,tempfile,threading,time,unittest.mock as mock
spec=importlib.util.spec_from_file_location('acme',Path(__file__).with_name('acme-publico.py'));A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
lab=Path(tempfile.mkdtemp(prefix='santafe-acme15-test-',dir='/tmp')).resolve();passed=[]
def ok(name):passed.append(name);print('PASSOU',name,flush=True)
def fail(f):
 try:f()
 except (RuntimeError,OSError):return
 raise AssertionError('operação inválida aceita')
root=lab/'web';root.mkdir();challenge=root/'.well-known/acme-challenge';challenge.mkdir(parents=True)
private=lab/'private';private.mkdir();(private/'tokens').mkdir()
class Handler(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*args,**kw):super().__init__(*args,directory=str(root),**kw)
 def log_message(self,*args):pass
class Server(socketserver.ThreadingTCPServer):allow_reuse_address=True
srv=Server(('127.0.0.1',0),Handler);th=threading.Thread(target=srv.serve_forever,daemon=True);th.start()
A.save(private/'contexto.json',{'dominio':A.DOMAIN,'desafios':str(challenge),'origem_http':'http://127.0.0.1:'+str(srv.server_address[1])})
token='A'*43;value=token+'.'+'B'*43
def env(t=token,d=A.DOMAIN,v=value):return mock.patch.dict(os.environ,{'CERTBOT_TOKEN':t,'CERTBOT_DOMAIN':d,'CERTBOT_VALIDATION':v})
try:
 with env():A.hook(private,'autorizar');assert (challenge/token).read_text()==value and (challenge/token).stat().st_mode&0o777==0o644;A.hook(private,'limpar')
 assert not(challenge/token).exists() and A.read(private/'tokens'/(token+'.json'))['limpo'];ok('autorização HTTP e limpeza exata do desafio')
 for tok,dom,val in [('../escape',A.DOMAIN,value),('C'*43,'outro.example',value),('D'*43,A.DOMAIN,'abc\nxyz')]:
  with env(tok,dom,val):fail(lambda:A.hook(private,'autorizar'))
 ok('travessia, domínio estranho e quebra de linha recusados')
 victim=challenge/('E'*43);victim.write_text('preexistente')
 with env(victim.name):fail(lambda:A.hook(private,'autorizar'))
 assert victim.read_text()=='preexistente';ok('arquivo preexistente não sobrescrito')
 external=lab/'fora';external.write_text('intacto');link=challenge/('F'*43);link.symlink_to(external)
 with env(link.name):fail(lambda:A.hook(private,'autorizar'))
 assert external.read_text()=='intacto';ok('link simbólico não seguido')
 t='G'*43
 with env(t):A.hook(private,'autorizar');(challenge/t).write_text('modificado');fail(lambda:A.hook(private,'limpar'))
 assert (challenge/t).read_text()=='modificado';ok('limpeza preserva arquivo alterado por terceiro')
 t='H'*43
 with env(t),mock.patch.object(A.urllib.request,'urlopen',side_effect=OSError('rede indisponível')):fail(lambda:A.hook(private,'autorizar'))
 assert not(challenge/t).exists() and A.read(private/'tokens'/(t+'.json'))['limpo'];ok('falha HTTP remove somente o desafio criado')
 t='I'*43
 with env(t):A.hook(private,'autorizar');(challenge/t).unlink();(challenge/t).symlink_to(external);fail(lambda:A.hook(private,'limpar'))
 assert external.read_text()=='intacto';ok('limpeza recusa link substituído')
 for renewal in [False,True]:
  cmd=A.command(private,'a'*32,renewal)
  assert '--config-dir' in cmd and '--work-dir' in cmd and '--logs-dir' in cmd and '-c' in cmd and '--no-directory-hooks' in cmd
  assert not any(x in cmd for x in ['--nginx','--apache','--standalone','--agree-tos','--register-unsafely-without-email','--deploy-hook','--pre-hook','--post-hook'])
  assert str(A.LE) not in cmd and cmd[cmd.index('--server')+1]==A.SERVER
  assert ('renew' in cmd)==renewal and ('certonly' in cmd)!=renewal
 ok('comandos isolam estado e recusam instalação, hooks de serviço e aceite automático')
 A.run(private,'processo-ok',[sys.executable,'-c','pass'])
 fail(lambda:A.run(private,'processo-falhou',[sys.executable,'-c','raise SystemExit(7)']))
 ok('falha do subprocesso não vira aprovação')
 start=time.monotonic()
 try:A.run(private,'processo-lento',[sys.executable,'-c','import time;time.sleep(60)'],timeout=.2)
 except subprocess.TimeoutExpired:pass
 else:raise AssertionError('tempo limite ignorado')
 assert time.monotonic()-start<15;ok('tempo limite encerra o grupo isolado')
 # Conta é apenas copiada depois de validar servidor, ID e status. Dados fictícios.
 ac=lab/'le';(ac/'renewal').mkdir(parents=True);folder=ac/'accounts/acme-v02.api.letsencrypt.org/directory'/('a'*32);folder.mkdir(parents=True)
 cfg=ac/'renewal'/(A.DOMAIN+'.conf');cfg.write_text('version=2.1.0\n[renewalparams]\naccount = '+('a'*32)+'\nserver = '+A.SERVER+'\n[[webroot_map]]\n')
 for name in ['meta.json','private_key.json']:(folder/name).write_text('{}')
 A.save(folder/'regr.json',{'body':{'status':'valid'},'uri':'https://acme-v02.api.letsencrypt.org/acme/acct/123'})
 with mock.patch.object(A,'LE',ac):
  assert A.choose_account()[0]=='a'*32
  cfg.write_text(cfg.read_text().replace(A.SERVER,'https://ca.example/directory'));fail(A.choose_account)
 ok('conta existente validada sem criar ou aceitar termos')
 # A comparação integral detecta mudança, sem tentar reverter produção.
 before={'nucleo':'a','certificado':'b'};after={'nucleo':'a','certificado':'c'}
 fail(lambda:A.need(before==after,'produção mudou'));ok('mudança de estado impede aprovação')
finally:
 srv.shutdown();srv.server_close();th.join(timeout=2)
report={'resultado':'PASSOU','grupos':passed,'esperados':12,'rede_publica':False,'tipo':'testes do auxiliar; não prova emissão ACME pública'}
assert len(passed)==12
(lab/'resultado.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('EVIDENCIA',lab/'resultado.json')
