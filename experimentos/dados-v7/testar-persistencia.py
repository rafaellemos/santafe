#!/usr/bin/env python3
"""Processos isolados, falhas syscall, crash e leitores concorrentes; sem produção."""
import concurrent.futures, json, os, shlex, stat, subprocess, tempfile, threading, unittest, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados7').is_file()
LAB=Path(tempfile.mkdtemp(prefix='santafe-onfe7-',dir='/tmp')).resolve()
BIN=ROOT/'src/santafé'
env=dict(os.environ, GSETTINGS_BACKEND='memory')
def quoted(s,**kwargs): return json.dumps(s,ensure_ascii=False)
BOOT='módulo.caminho='+quoted(str(ROOT)+'/bibs/bibf/?.fé;'+str(ROOT)+'/bibs/bibf/?/?.fé')+'; módulo.caminhoC='+quoted(str(ROOT)+'/bibs/bibc/?/?.so')+'; local O=importe "onfé"; '
driver=LAB/'prova'
san=['-g','-fsanitize=address,undefined','-fno-omit-frame-pointer'] if '--sanitizadores' in sys.argv else []
subprocess.run(['cc',*san,'-std=c99','-Wall','-Wextra','-Werror',str(ROOT/'experimentos/dados-v7/prova-atomico.c'),
                '-I'+str(ROOT/'bibs/bibc/arquivo'),'-o',str(driver),*shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','glib-2.0'],text=True))],check=True)
def fe(code):
    p=subprocess.run([str(BIN),'-E','-P','-e',BOOT+code],cwd=LAB,env=env,capture_output=True,text=True,timeout=20)
    assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
    return p.stdout
def raw(path,mode='normal',payload='{"novo":true}'):
    return subprocess.run([str(driver),str(path),mode,payload],capture_output=True,text=True,timeout=10)
class Persistencia(unittest.TestCase):
    def setUp(self):
        self.dir=Path(tempfile.mkdtemp(dir=LAB));self.p=self.dir/'ação.onfé';self.p.write_text('ANTIGO')
    def test_roundtrip_shapes_and_null(self):
        p=quoted(str(self.p),ensure_ascii=False)
        fe('local p='+p+'; local t={n=nulo,lista=[nulo,"José",nulo],vazia=[],objeto={},[1]="n",["1"]="t",bruto=[=[®literal\\n\nlinha]=]}; local ok,f,s=O.grave(p,t); garanta(ok e f==nulo e s=="durável"); local v=O.carregue(p); garanta(tabela.temChave(v,"n") e #v.lista==3 e v.lista[3]==nulo e tipo(v.vazia)=="lista" e tipo(v.objeto)=="tabela" e v[1]~=v["1"] e v.bruto==t.bruto)')
        self.assertEqual(stat.S_IMODE(self.p.stat().st_mode),0o600)
    def test_root_null_false_empty(self):
        fe('local p='+quoted(str(self.p))+'; para _,v em ipares([nulo,falso,"",[],{}]) início garanta(O.grave(p,v)); local x=O.carregue(p); garanta(tipo(x)==tipo(v)); se tipo(v)~="tabela" e tipo(v)~="lista" então garanta(x==v) fim fim')
    def test_invalid_before_touch(self):
        fe('local p='+quoted(str(self.p))+'; local ciclo={}; ciclo.x=ciclo; para _,v em ipares([ciclo,definaMetatabela({},{}),função() fim,("x"):replique(4*1024*1024+1)]) início local ok=proteja(O.grave,p,v); garanta(não ok) fim; garanta(não proteja(O.grave,p.."\\0outro",{})); garanta(não proteja(O.graveAssíncrono,p,{},nulo))')
        self.assertEqual(self.p.read_text(),'ANTIGO');self.assertEqual(list(self.dir.glob('.onfe-*')),[])
    def test_sync_io_failure_state(self):
        fe('local ok,f,s=O.grave('+quoted(str(self.dir/'ausente/x'))+',{}); garanta(ok==nulo e tipo(f)=="colar" e s=="inalterado")')
    def test_bad_path_and_low_level_types(self):
        fe('local A=importe "arquivo"; para _,p em ipares([nulo,123,{},falso,""]) início garanta(não proteja(O.grave,p,{})); garanta(não proteja(O.graveAssíncrono,p,{},função() fim)) fim; garanta(não proteja(A.graveAtômico,"tipo-invalido",123)); garanta(não proteja(A.graveAtômicoAssíncrono,"tipo-invalido",123,função() fim))')
        self.assertFalse((LAB/'123').exists());self.assertFalse((LAB/'tipo-invalido').exists())
    def test_async_snapshot_and_context(self):
        fe('local R=importe "rede"; local p='+quoted(str(self.p))+'; local t={v="antes",n=nulo}; local c={}; local chamadas=0; garanta(O.graveAssíncrono(p,t,função(ok,f,s,ctx) chamadas=chamadas+1; garanta(ok e f==nulo e s=="durável" e ctx==c); R.pareLaço() fim,c)); t.v="depois"; R.laço(); garanta(chamadas==1 e O.carregue(p).v=="antes")')
    def test_async_failure_and_nil_context(self):
        fe('local R=importe "rede"; local chamadas=0; O.graveAssíncrono('+quoted(str(self.dir/'ausente/x'))+',{},função(ok,f,s,ctx) chamadas=chamadas+1; garanta(ok==nulo e tipo(f)=="colar" e s=="inalterado" e ctx==nulo); R.pareLaço() fim); R.laço(); garanta(chamadas==1)')
    def test_callback_error_preserves_vm(self):
        fe('local R=importe "rede"; local p='+quoted(str(self.p))+'; local chamadas=0; O.graveAssíncrono(p,[nulo],função() chamadas=chamadas+1; R.pareLaço(); erro({}) fim); R.laço(); coleteLixo("colete"); garanta(chamadas==1 e #O.carregue(p)==1); O.graveAssíncrono(p,[1,2],função(ok,f,s) chamadas=chamadas+1; R.pareLaço(); garanta(ok e s=="durável") fim); R.laço(); garanta(chamadas==2 e #O.carregue(p)==2)')
    def test_special_targets(self):
        other=self.dir/'outro';other.write_text('PRESERVAR')
        link=self.dir/'link';link.symlink_to(other)
        fifo=self.dir/'fifo';os.mkfifo(fifo)
        folder=self.dir/'pasta';folder.mkdir()
        for path in (link,fifo,folder):
            r=raw(path);self.assertEqual(r.returncode,0);self.assertIn('0 inalterado',r.stdout);self.assertNotEqual(r.stdout.split()[0],'0')
        self.assertEqual(other.read_text(),'PRESERVAR');self.assertTrue(link.is_symlink())
    def test_all_fault_boundaries(self):
        for mode in ('criar','permissoes','escrever','sincronizar-arquivo','fechar','antes-troca','renomear','parcial-enospc','zero'):
            with self.subTest(mode=mode):
                self.p.write_text('ANTIGO');r=raw(self.p,mode,'novo'*300)
                self.assertEqual(r.returncode,0);self.assertIn('0 inalterado',r.stdout);self.assertNotEqual(r.stdout.split()[0],'0')
                self.assertEqual(self.p.read_text(),'ANTIGO');self.assertEqual(list(self.dir.glob('.onfe-*')),[])
        for mode in ('depois-troca','sincronizar-diretorio'):
            r=raw(self.p,mode,'NOVO');self.assertIn('1 publicado',r.stdout);self.assertEqual(self.p.read_text(),'NOVO');self.assertEqual(list(self.dir.glob('.onfe-*')),[])
    def test_short_writes_and_eintr(self):
        payload='á®Ⓡ'*1000;r=raw(self.p,'curta-eintr',payload)
        self.assertEqual(r.stdout.strip(),'0 2 durável');self.assertEqual(self.p.read_text(),payload)
    def test_crash_before_after(self):
        r=raw(self.p,'crash-antes','NOVO');self.assertEqual(r.returncode,91);self.assertEqual(self.p.read_text(),'ANTIGO')
        remains=list(self.dir.glob('.onfe-*'));self.assertEqual(len(remains),1);self.assertEqual(remains[0].read_text(),'NOVO')
        r=raw(self.p,'crash-depois','NOVO');self.assertEqual(r.returncode,92);self.assertEqual(self.p.read_text(),'NOVO')
        self.assertEqual(list(self.dir.glob('.onfe-*')),remains)
    def test_pinned_parent(self):
        r=raw(self.p,'mudar-pai','NOVO');self.assertEqual(r.stdout.strip(),'0 2 durável')
        self.assertEqual((Path(str(self.dir)+'-movido')/self.p.name).read_text(),'NOVO');self.assertFalse(self.p.exists())
    def test_hardlink_and_open_reader(self):
        alias=self.dir/'alias';os.link(self.p,alias)
        with self.p.open() as old:
            r=raw(self.p,'normal','NOVO');self.assertEqual(r.stdout.strip(),'0 2 durável');self.assertEqual(old.read(),'ANTIGO')
        self.assertEqual(alias.read_text(),'ANTIGO');self.assertEqual(self.p.read_text(),'NOVO')
    def test_concurrent_writers_readers(self):
        data=[json.dumps({'id':i,'corpo':str(i)*18000}) for i in range(4)]
        self.p.write_text(data[0]);stop=threading.Event();counts=[]
        def reader():
            count=0
            while not stop.is_set():
                value=json.loads(self.p.read_text());self.assertEqual(value['corpo'],str(value['id'])*18000);count+=1
            counts.append(count)
        def writer(i):
            for _ in range(35): self.assertEqual(raw(self.p,'normal',data[i]).stdout.strip(),'0 2 durável')
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
            readers=[pool.submit(reader) for _ in range(3)]
            try:
                for f in [pool.submit(writer,i) for i in range(4)]:f.result()
            finally:stop.set()
            for f in readers:f.result()
        self.assertGreater(min(counts),0);self.assertEqual(list(self.dir.glob('.onfe-*')),[])
        print('Leituras completas:',sum(counts),'; trocas: 140',flush=True)
    def test_fault_hooks_absent_from_module(self):
        module=ROOT/'bibs/bibc/arquivo/arquivo.so'
        symbols=subprocess.check_output(['nm',str(module)],text=True)
        self.assertNotIn('arq_atomo_teste',symbols)
    def test_umask_and_relative_path(self):
        fe('local ok,f,s=O.grave("relativo.onfé",[1,nulo]); garanta(ok e s=="durável"); garanta(#O.carregue("relativo.onfé")==2)')
        self.assertEqual(stat.S_IMODE((LAB/'relativo.onfé').stat().st_mode),0o600)
if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Persistencia)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (ROOT/'evidencias').mkdir(exist_ok=True)
    (ROOT/('evidencias/onfe-persistencia7'+('-asan' if san else '')+'.json')).write_text(json.dumps({'passou':result.wasSuccessful(),'grupos':result.testsRun,'falhas':len(result.failures),'erros':len(result.errors),'laboratorio':str(LAB),'sanitizadores_no_harness_c':bool(san)},indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
