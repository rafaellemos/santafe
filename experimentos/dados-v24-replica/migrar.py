#!/usr/bin/env python3
"""Réplica completa: troca coordenada de código, nunca reversão de dados."""
import argparse, hashlib, importlib.util, json, os, re, shutil, ssl, stat
import subprocess, sys, tempfile, time, traceback, http.client
from pathlib import Path

HERE=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
B=module('base24',HERE/'replica-base.py')
T=module('transacao24',HERE/'transacao.py')
A=module('ajustes24',HERE/'ajustar-operacionais.py')

UNITS=[('sfdev.service','sfdev.fé',17000),('paodocafe.service','paodocafe/paodocafe.fé',17200),
       ('carteiro.service','carteiro/carteiro.fé',17100),('carteiro-paodocafe.service','carteiro/carteiro.fé',17101),
       ('correio-recebedor.service','correio/recebedor.fé',11025),('correio-agencia.service','correio/agência.fé',11587),
       ('correio-imap.service','correio/imap.fé',11993),('nomes-autoridade.service','santafe-nomes/autoridade.fé',15353)]

class Consumers:
    def __init__(self,x):self.x=x;self.children={};self.events=[]
    def active(self,name):
        p=self.children.get(name);return p is not None and p.poll() is None
    def start(self,name):
        assert not self.active(name)
        if name=='fila-inativa':raise RuntimeError('fila inativa não deve iniciar')
        _,entry,port=next(row for row in UNITS if row[0]==name)
        x=self.x;g=x.runtime
        env=x.env_unit(g,name)
        p=x.start('ativo24-'+name+'-'+str(len(self.events)),x.command(g,entry=entry),env,g/'opt')
        self.children[name]=p;self.events.append(('iniciar',name))
        x.wait(p,port)
    def stop(self,name):
        self.x.stop([self.children[name]]);self.events.append(('parar',name))

class Replica(B.Replica):
    def __init__(self,a):
        super().__init__(a);self.runtime=self.lab/'candidata';self.generation='estavel'
        self.inject=False;self.saved_after=None
    def budget(self):
        assert shutil.disk_usage(self.lab).free>=2*1024**3,'reserva de 2 GiB atingida'
    def adjust_operational(self,cand):
        rows=[]
        for name,digest in A.EXPECTED.items():
            p=cand/name;assert B.sha(p)==digest,'fonte operacional mudou: '+name
            text,reasons=A.adjust(name,p.read_text());p.write_text(text)
            rows.append({'arquivo':name,'antes':digest,'ajustes':reasons})
        portal=cand/'opt/sfdev.fé';text=portal.read_text()
        guard='local função destinoApósEntrada(valor)\n';assert text.count(guard)==1
        portal.write_text(text.replace(guard,guard+'    valor = paraColar(valor ou "")\n'))
        patch=module('upload24',self.stage/'experimentos/dados-v13/aplicar-portal.py')
        patch.corrigir(portal)
        for row in rows:row['depois']=B.sha(cand/row['arquivo'])
        # Geração3 usa apenas módulos3; geração2 continua intacta para reversão.
        for p in (cand/'etc').rglob('*'):
            if p.is_file() and p.suffix in ('.env','.conf','.service','.fé'):
                text=p.read_text();p.write_text(text.replace('/santafé/1.0/','/santafé/3.0/'))
        B.write(self.lab/'ajustes-operacionais.json',rows)
    def prepare(self):
        super().prepare()
        # Conteúdo migrado fica separado. A mesma raiz ativa começará com2.1.
        prepared=self.lab/'preparada';self.runtime.rename(prepared)
        shutil.copytree(self.lab/'estavel',self.runtime)
        self.payload=self.lab/'pacote';self.payload.mkdir(mode=0o700)
        shutil.copytree(prepared/'local',self.payload/'usr/local')
        shutil.copytree(prepared/'opt',self.payload/'opt')
        for folder in ('santafe','paodocafe','santafe-nomes','santafe-dns'):
            for p in (prepared/'etc'/folder).rglob('*'):
                if p.is_file() and p.suffix in ('.env','.fé'):
                    rel=p.relative_to(prepared);target=self.payload/rel
                    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        # Configurações de transporte do ensaio são lidas de cada geração.
        (self.runtime/'.replica-iba3').write_text('REPLICA_ISOLADA_SEM_PRODUCAO\n')
        self.runtime.chmod(0o700)
        self.budget()
    def mount(self,g):
        super().mount(g)
        # Só o bind da cópia privada fica gravável para a transação. /usr do
        # host continua somente leitura e o namespace não propaga montagens.
        self.run(['mount','-o','remount,bind,rw',g/'usr/local'])
    def env_unit(self,g,unit):
        env=super().env_unit(self.runtime,unit)
        version='3.0' if self.generation=='candidata' else '1.0'
        env['LUA_PATH']=env['LUA_PATH'].replace('/1.0/','/'+version+'/')
        env['LUA_CPATH']=env['LUA_CPATH'].replace('/1.0/','/'+version+'/')
        env.update(NOMES_AUTORIDADE_ENDERECO='127.0.0.1',NOMES_AUTORIDADE_PORTA='15353',
                   DNS_AUTORITATIVO_ENDERECO='127.0.0.1',DNS_AUTORITATIVO_PORTA='15353',
                   SANTAFE_DIRETORIO_IMAGENS_COMUNIDADE='/var/lib/imagens24')
        return env
    def command(self,g,code=None,entry=None):return super().command(self.runtime,code,entry)
    def sf(self,kind,code):return super().sf('candidata',code)
    def installed(self):
        super().installed()
        assert not self.supervisor.active('fila-inativa')
        # O arquivo antigo permanece disponível somente para a reversão, mas
        # importação e SDK ativos precisam concordar com3.0.
        result=self.sf('candidata','mostre(módulo.caminhoC); mostre(tipo([nulo]))')
        assert '/santafé/3.0/' in result and result.endswith('lista')
    def readiness(self):
        for port,path in ((17100,'/carteiro/estado'),(17101,'/carteiro/estado'),(17200,'/estado')):
            for _ in range(200):
                status,_=self.http(port,path)
                if status==200:break
                time.sleep(.1)
            else:raise RuntimeError('prontidão falhou: '+str(port))
    def infrastructure(self,kind):
        g=self.runtime;(self.lab/'estado-lib/nginx').mkdir(exist_ok=True)
        p=self.start('nginx24',['/usr/sbin/chroot',str(g),'/usr/sbin/nginx','-g','daemon off;'],B.BASE_ENV,g/'opt')
        self.wait(p,443);return [p]
    def dns(self):
        env=self.env_unit(self.runtime,'nomes-autoridade.service');zonefile=env.get('NOMES_ZONAS_ARQUIVO','/etc/santafe-nomes/zonas.fé')
        array='[]' if self.generation=='candidata' else '{}'
        code='local d=executeArquivo('+json.dumps(zonefile,ensure_ascii=False)+');local s='+array+';para _,z em ipares(d.zonas ou d) início s[#s+1]={nome=z.nome,assinada=z.dnssec e verdadeiro ou falso} fim;mostre(json.cod(s))'
        zones=json.loads(self.sf(self.generation,code));keys={};signed=0
        for zone in zones:
            for protocol in ('+tcp','+notcp'):
                answer=self.run(['dig','@127.0.0.1','-p','15353',zone['nome'],'SOA','+dnssec',protocol,'+noall','+comments','+answer','+time=2','+tries=1']).decode()
                assert 'status: NOERROR' in answer and re.search(r'\sSOA\s',answer)
                if zone['assinada']:assert 'RRSIG' in answer;signed+=1
            if zone['assinada']:
                key=self.run(['dig','@127.0.0.1','-p','15353',zone['nome'],'DNSKEY','+short','+time=2','+tries=1'])
                assert key.strip();keys[zone['nome']]=hashlib.sha256(key).hexdigest()
        if hasattr(self,'dnskeys'):assert self.dnskeys==keys
        self.dnskeys=keys
        self.passed('DNS capturado UDP/TCP; identidades DNSSEC preservadas',geracao=self.generation,zonas=len(zones),assinadas=signed)
    def https(self):
        ctx=ssl.create_default_context(cafile=str(self.stage/'testes/recursos/tls-local-certificado.pem'))
        for domain in B.DOMS:
            for path in ('/','/carteiro/estado'):
                c=http.client.HTTPSConnection('127.0.0.1',443,context=ctx,timeout=15)
                c.request('GET',path,headers={'Host':domain});r=c.getresponse();r.read();c.close();assert r.status==200
    def health(self,kind):
        self.generation='candidata' if kind=='candidata' else 'estavel'
        assert all(self.supervisor.active(n) for n,_,_ in UNITS)
        assert not self.supervisor.active('fila-inativa')
        self.readiness();self.https();self.dns();self.read_all(self.generation);self.objects();self.budget()
        if self.saved_after is not None:assert self.tables()==self.saved_after,'transação alterou dados posteriores'
        if self.inject and kind=='candidata':
            for i in range(2):self.message('falha-saude24',i)
            self.saved_after=self.tables()
            raise RuntimeError('FALHA_SAUDE24_INJETADA_APOS_ESCRITA')
    def hook(self,name):
        if name=='trocou':self.generation='candidata'
    def load(self):
        # Mesmas seis conexões e60s; reserva monitorada também durante carga.
        import threading
        stop=threading.Event();errors=[]
        def check():
            while not stop.wait(1):
                try:self.budget()
                except BaseException as e:errors.append(e);return
        t=threading.Thread(target=check);t.start()
        try:super().load()
        finally:stop.set();t.join()
        assert not errors,'reserva atingida durante carga'
    def execute(self):
        self.prepare();self.mount(self.runtime);self.database();self.setup_users()
        self.supervisor=Consumers(self)
        for name,_,_ in UNITS:self.supervisor.start(name)
        infra=self.infrastructure('estavel');self.health('anterior')
        for i in range(2):self.message('antes24',i)
        self.protocols('estavel','antes24')
        def hook(name):
            # A geração é escolhida pelo binário efetivo quando cada processo
            # começa, inclusive durante reversão automática.
            pass
        original_start=self.supervisor.start
        def start(name):
            version=subprocess.check_output([str(self.runtime/'local/bin/santafé'),'-E','-P','-v'],env=B.BASE_ENV)
            self.generation='candidata' if b'3.0.0-rc.1' in version else 'estavel'
            return original_start(name)
        self.supervisor.start=start
        units=[n for n,_,_ in UNITS]+['fila-inativa']
        for failure in (False,True):
            self.inject=failure;self.saved_after=self.tables()
            tx=T.Transacao(self.runtime,self.supervisor,self.health)
            tx.prepare(self.payload,units)
            if failure:
                try:tx.apply()
                except RuntimeError as e:assert str(e)=='FALHA_SAUDE24_INJETADA_APOS_ESCRITA'
                else:raise AssertionError('falha não exercitada')
            else:
                tx.apply();self.installed()
                self.protocols('candidata','depois24');self.load()
                for i in range(2):self.message('pos-carga24',i)
                self.saved_after=self.tables();self.objects();tx.reverse_completed()
            assert tx.load()['fase']=='REVERTIDA'
            assert self.tables()==self.saved_after
            tx.verify(tx.load(),'antes')
            self.protocols('estavel','reversao24-'+str(int(failure)))
            self.passed('reversão preservou todos os dados e estados ativos',falha_injetada=failure,arquivos=len(tx.load()['arquivos']))
            tx.work.rename(self.runtime/('.migracao-concluida-'+str(int(failure))))
        self.stop(infra);self.stop(self.procs);self.budget()
        assert all(p.poll() is not None for p in self.procs)
        self.passed('todos os processos privados encerrados; produção fora do namespace')
        self.report.update(resultado='PASSOU',limites=['captura histórica; não é instalação atualizada em produção',
            'SMTP/TLS/IMAP/fila/DNS reais em rede fechada; Mailjet/ACME externos não repetidos',
            '60 segundos de carga, não substitui ensaio prolongado', 'sem systemd global; supervisor de processos no namespace'])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('replica','restauro','candidato'):p.add_argument(n,type=Path)
    p.add_argument('--lab',type=Path);p.add_argument('--interior',action='store_true');a=p.parse_args()
    assert sys.platform=='linux' and (a.candidato/'.laboratorio-dados24').is_file()
    B.V.conferir(a.replica)
    assert a.restauro.parent==Path('/var/tmp') and a.restauro.name.startswith('santafe-restauro11-')
    assert (a.restauro/'GATE_RESTAURACAO_OK').is_file()
    if not a.interior:
        os.umask(0o077);a.lab=Path(tempfile.mkdtemp(prefix='santafe-migracao11-d24-',dir='/var/tmp'))
        env=dict(B.BASE_ENV,SANTAFE_NET_ORIGEM=os.readlink('/proc/self/ns/net'))
        print('LABORATORIO24_PRIVADO',a.lab,flush=True)
        args=['unshare','--user','--map-root-user','--mount','--net','--pid','--fork',sys.executable,str(Path(__file__).resolve()),str(a.replica),str(a.restauro),str(a.candidato),'--interior','--lab',str(a.lab)]
        return subprocess.call(args,env=env)
    assert os.getpid()==1 and os.readlink('/proc/self/ns/net')!=os.environ['SANTAFE_NET_ORIGEM']
    assert {x['ifname'] for x in json.loads(subprocess.check_output(['ip','-j','link']))}=={'lo'}
    assert not subprocess.check_output(['ip','route','show','default']).strip()
    assert not subprocess.check_output(['ip','-6','route','show','default']).strip()
    subprocess.run(['ip','link','set','lo','up'],check=True);os.umask(0o077)
    x=Replica(a)
    try:x.execute()
    except BaseException as e:
        x.report.update(resultado='FALHOU',classe=type(e).__name__)
        (a.lab/'falha-privada.txt').write_text(traceback.format_exc());print('FALHOU24',type(e).__name__,flush=True)
    finally:
        x.stop(x.procs)
        for h in x.handles:h.close()
        B.write(a.lab/'resultado24.json',x.report)
    return 0 if x.report['resultado']=='PASSOU' else 1
if __name__=='__main__':raise SystemExit(main())
