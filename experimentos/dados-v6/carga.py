"""Carga limitada, sintética, somente nos serviços privados do harness dados.5."""
import concurrent.futures, imaplib, json, os, smtplib, ssl, statistics, subprocess, threading, time, shutil
from pathlib import Path

def summary(values):
    s=sorted(values)
    return {'n':len(s),'p50_ms':round(statistics.median(s)*1000,2),
            'p95_ms':round(s[max(0,int(len(s)*.95)-1)]*1000,2),'max_ms':round(max(s)*1000,2)}

def execute(lab,ports,http,context,password,dns):
    root=Path(__file__).resolve().parents[2]; report={}; rss=[]; stop=threading.Event(); limites=[]
    def memory():
        while not stop.is_set():
            live=[p.pid for p in lab.processes if p.poll() is None]
            p=subprocess.run(['ps','-o','pid=,rss=','-p',','.join(map(str,live))],capture_output=True,text=True)
            rss.append({'t':round(time.monotonic(),2),'kib':{x.split()[0]:int(x.split()[1]) for x in p.stdout.splitlines() if x.strip()}})
            free=shutil.disk_usage(lab.path).free
            logs=sum(p.stat().st_size for p in lab.path.iterdir() if p.is_file())
            if free<2*1024**3 or logs>128*1024**2 or sum(rss[-1]['kib'].values())>800*1024:
                limites.append({'disco_livre':free,'logs':logs,'rss':sum(rss[-1]['kib'].values())});stop.set()
            stop.wait(1)
    watcher=threading.Thread(target=memory);watcher.start()
    initial=int(lab.sql('SELECT COUNT(*) FROM correio_cartas'))
    latencies={k:[] for k in ('http','imap','smtp','dns')}
    duration=int(os.environ.get('SANTAFE_CARGA_SEGUNDOS','60'))
    assert 60<=duration<=7200
    begin=time.monotonic()
    try:
        def worker(kind):
            conn=None
            if kind=='imap':
                conn=imaplib.IMAP4_SSL('127.0.0.1',ports['imap'],ssl_context=context,timeout=10)
                conn.authenticate('PLAIN',lambda _: ('\0josé@ensaio.test\0'+password).encode())
            elif kind=='smtp':
                conn=smtplib.SMTP('127.0.0.1',ports['recebedor'],timeout=10)
                conn.ehlo()
            for i in range(60):
                now=time.monotonic()
                if kind=='http':
                    assert http('/carteiro/entrada')[0]==200
                    assert http('/carteiro/entrada',cookie=False)[0]==303
                elif kind=='imap':
                    assert conn.select('INBOX',readonly=True)[0]=='OK'
                    assert conn.uid('SEARCH',None,'ALL')[0]=='OK'
                elif kind=='smtp':
                    if i and i%10==0:
                        conn.quit()
                        conn=smtplib.SMTP('127.0.0.1',ports['recebedor'],timeout=10); conn.ehlo()
                    raw=('From: carga@externo.test\r\nTo: josé@ensaio.test\r\nSubject: Carga '+str(i)+'\r\nMessage-ID: <carga6-'+str(i)+'@externo.test>\r\n\r\nEnsaio sintético.\r\n').encode()
                    assert conn.sendmail('carga@externo.test',['josé@ensaio.test'],raw,mail_options=['SMTPUTF8'])=={}
                else:
                    for _ in range(20):
                        assert dns(ports['resolvedor'],'www.ensaio.test',i%2==0)[1]==1
                        time.sleep(.02) # 50/s, abaixo de 100/s; não desativa proteção.
                latencies[kind].append(time.monotonic()-now)
            if kind=='imap': conn.logout()
            if kind=='smtp': conn.quit()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(worker,latencies))
        # Permanência em carga por pelo menos 60s; quatro leitores concorrentes.
        def sustained(_):
            times=[]
            while time.monotonic()-begin<duration and not stop.is_set():
                now=time.monotonic(); response=http('/carteiro/entrada')
                if response[0]!=200:
                    (lab.path/('http-falha-'+str(threading.get_ident())+'.html')).write_bytes(response[2])
                    stop.set()
                    raise AssertionError(('HTTP carga',response[0],response[2].decode('utf-8','replace')[-5000:]))
                times.append(time.monotonic()-now); time.sleep(.02)
            return times
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            extra=[v for x in pool.map(sustained,range(4)) for v in x]
        latencies['http'].extend(extra)
        assert not limites,('orçamento do laboratório',limites)
        assert int(lab.sql('SELECT COUNT(*) FROM correio_cartas'))==initial+60
        report={'resultado':'EM_ANDAMENTO','segundos':round(time.monotonic()-begin,2),
                'concorrencia':4,'smtp_persistidas':60,'dns_consultas':1200,
                'latencias':{k:summary(v) for k,v in latencies.items()},'rss':rss,
                'limites':'carga de laboratório; DNS medido por lote de 20; não é soak de horas nem SLO de produção'}
        # Orçamento de segurança do ensaio, não promessa de capacidade.
        peak=max(sum(x['kib'].values()) for x in rss)
        assert peak<1024*1024,('RSS agregado excedeu 1 GiB',peak)
        report['rss_pico_agregado_kib']=peak
        # A proteção não deve ser desativada para o benchmark: sobrecarga recusa
        # novas conexões e emite motivo explícito no PULSO.
        refused=0
        for _ in range(65):
            try:
                with imaplib.IMAP4_SSL('127.0.0.1',ports['imap'],ssl_context=context,timeout=5): pass
            except (ConnectionResetError,ssl.SSLZeroReturnError,ssl.SSLEOFError,imaplib.IMAP4.abort): refused+=1
        # O fechamento TLS pode chegar antes de a escrita assíncrona do PULSO
        # completar. Exigir os MESMOS eventos, com prazo limitado para persistir.
        deadline=time.monotonic()+3
        while True:
            lines=(lab.path/'correio.pulso').read_text().split('\n')[:-1]
            events=[json.loads(x) for x in lines if x]
            limited=sum(e['nome']=='correio.imapConexãoLimitada' for e in events)
            if limited>=refused or time.monotonic()>=deadline:break
            time.sleep(.02)
        assert refused and limited>=refused, (refused,limited)
        report['imap_eventos_limite_persistidos']=limited
        report['imap_conexoes_recusadas_por_protecao']=refused
        for p in lab.path.glob('*.log'):
            assert 'retornou erro:' not in p.read_text(), ('erro assíncrono',p)
        # Guardar HTML REAL para inspeção; conteúdo e identidade são sintéticos.
        (root/'evidencias/carteiro-carga.html').write_bytes(http('/carteiro/entrada')[2])
    except BaseException:
        report['resultado']='FALHOU'
        raise
    else:
        report['resultado']='PASSOU'
    finally:
        stop.set();watcher.join()
        (root/'evidencias/carga6.json').write_text(json.dumps(report or {'resultado':'FALHOU','rss':rss},ensure_ascii=False,indent=2)+'\n')
    print('PASSOU carga:',report['latencias'],'RSS pico KiB:',peak,flush=True)
