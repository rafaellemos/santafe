#!/usr/bin/env python3
"""Percursos dos processos reais, dados sintéticos e tráfego só de loopback."""
import email.policy
from email.message import EmailMessage
from http.client import HTTPConnection
import imaplib
import json
import smtplib
import socket
import struct
import ssl
import time
import urllib.parse
from laboratorio import Lab, ROOT, port

results=[]
def passed(name):
    results.append(name); print('PASSOU', name, flush=True)

def dns(number, name, tcp=False):
    question = b''.join(bytes([len(x)])+x.encode() for x in name.split('.'))+b'\0'+struct.pack('!HH',1,1)
    wire=struct.pack('!6H',3105,256,1,0,0,0)+question
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM if tcp else socket.SOCK_DGRAM) as s:
        s.settimeout(5); s.connect(('127.0.0.1',number))
        if tcp:
            s.sendall(struct.pack('!H',len(wire))+wire)
            def receive(n):
                data=b''
                while len(data)<n:
                    chunk=s.recv(n-len(data)); assert chunk; data+=chunk
                return data
            answer=receive(struct.unpack('!H',receive(2))[0])
        else: s.send(wire); answer=s.recv(4096)
    ident,flags,qd,an,ns,ar=struct.unpack('!6H',answer[:12]); assert ident==3105 and flags&32768
    return flags,an,answer

try:
    with Lab() as lab:
        lab.database()
        password='ensaio-exclusivo-5'
        hashed=lab.sf('local s=importe "segredo"; local r=importe "rede"; s.protejaSenhaAssíncrono("'+password+'",função(h,f) garanta(h,f); mostre(h); r.pareLaço() fim); r.laço()')
        token='sessao-exclusiva-laboratorio-5'; csrf='csrf-exclusivo-laboratorio-5'
        tokenhash=lab.sf('mostre((importe "segredo").resumaBilhete("'+token+'"))')
        assert hashed.startswith('$argon2id$') and len(tokenhash)==64
        lab.sql("INSERT INTO usuarios (nome,usuario,email,senha_hash) VALUES ('José Ensaio','josé','josé@ensaio.test','"+hashed+"'); INSERT INTO correio_caixas (usuario_id,parte_local,dominio_ascii,endereco_exibido,nome_exibido) VALUES (1,'josé','ensaio.test','josé@ensaio.test','José Ensaio'); INSERT INTO sessoes(usuario_id,token_hash,csrf_token,expira_em) VALUES (1,'"+tokenhash+"','"+csrf+"',DATE_ADD(NOW(), INTERVAL 1 HOUR));")
        cert=ROOT/'testes/recursos/tls-local-certificado.pem'; key=ROOT/'testes/recursos/tls-local-chave.pem'
        context=ssl.create_default_context(cafile=str(cert))
        ports={name:port() for name in ('recebedor','agencia','tls','imap','carteiro','autoridade','resolvedor','negado')}
        lab.env.update(CORREIO_RAIZ=str(ROOT/'aplicativos/correio'), CARTEIRO_RAIZ=str(ROOT/'aplicativos/carteiro'),
            CORREIO_DOMINIO='ensaio.test', CORREIO_DOMINIOS_LOCAIS='ensaio.test',
            CORREIO_DEPOSITO=str(lab.path/'deposito'), CORREIO_PULSO_ARQUIVO=str(lab.path/'correio.pulso'),
            CARTEIRO_PULSO_ARQUIVO=str(lab.path/'carteiro.pulso'), CORREIO_AUTENTICACAO_ATIVA='falso',
            CORREIO_ANTIVIRUS_ATIVO='falso', CORREIO_TRIAGEM_ATIVA='falso', CORREIO_DKIM_EXIGIR='falso',
            CORREIO_RECEBEDOR_ENDERECO='127.0.0.1', CORREIO_RECEBEDOR_PORTA=str(ports['recebedor']),
            CORREIO_RECEBEDOR_NOME='localhost', CORREIO_AGENCIA_ENDERECO='127.0.0.1',
            CORREIO_AGENCIA_PORTA_STARTTLS=str(ports['agencia']), CORREIO_AGENCIA_PORTA_TLS=str(ports['tls']),
            CORREIO_AGENCIA_NOME='localhost', CORREIO_AGENCIA_CERTIFICADO=str(cert), CORREIO_AGENCIA_CHAVE=str(key),
            CORREIO_IMAP_ENDERECO='127.0.0.1', CORREIO_IMAP_PORTA=str(ports['imap']), CORREIO_IMAP_NOME='localhost',
            CARTEIRO_ENDERECO='127.0.0.1', CARTEIRO_PORTA=str(ports['carteiro']),
            CORREIO_ENVIOS_MODO='retransmissor', CORREIO_ENVIOS_ENDERECO='127.0.0.1',
            CORREIO_ENVIOS_PORTA=str(ports['recebedor']), CORREIO_ENVIOS_SEGURANCA='nenhuma')
        processes={}
        for name,entry in [('recebedor','correio/recebedor'),('agencia','correio/agência'),('imap','correio/imap'),('carteiro','carteiro/carteiro')]:
            p=lab.app(name,'aplicativos/'+entry+'.fé'); lab.wait(p,ports[name],name)
            processes[name]=p
        def http(path, fields=None, cookie=True):
            c=HTTPConnection('127.0.0.1',ports['carteiro'],timeout=10)
            headers={'Cookie':'sf_sessao='+token} if cookie else {}
            data=None
            if fields is not None: data=urllib.parse.urlencode(fields); headers['Content-Type']='application/x-www-form-urlencoded'
            c.request('POST' if fields is not None else 'GET',path,data,headers)
            r=c.getresponse(); body=r.read(); info=(r.status,dict(r.getheaders()),body); c.close(); return info
        for attempt in range(100):
            status,_,body=http('/carteiro/estado')
            if status==200: break
            time.sleep(.1)
        assert status==200,body
        anonymous=http('/carteiro/entrada',cookie=False)
        assert anonymous[0]==303 and anonymous[1]['Location']=='/entrar?destino=/carteiro/',anonymous
        status,_,body=http('/carteiro/entrada'); assert status==200,body
        passed('inicialização real de quatro serviços; HTTP autenticado e anônimo')
        msg=EmailMessage(policy=email.policy.SMTPUTF8)
        msg['From']='Autora <origem@externo.test>'; msg['To']='José <josé@ensaio.test>'
        msg['Subject']='Homologação dados.5'; msg['Message-ID']='<apps5@externo.test>'
        msg.set_content('Corpo íntegro: ação, ®variável e nulo.')
        msg.add_alternative('<p>Corpo <b>íntegro</b></p><script>alert(1)</script>',subtype='html')
        msg.add_attachment(b'%PDF-1.7\nensaio\n',maintype='application',subtype='pdf',filename='ação.pdf')
        raw=msg.as_bytes()
        with smtplib.SMTP('127.0.0.1',ports['recebedor'],timeout=10) as smtp:
            smtp.ehlo(); assert smtp.has_extn('SMTPUTF8')
            smtp.mail('origem@externo.test',options=['SMTPUTF8']); assert smtp.rcpt('x@outro.invalid')[0]>=500; smtp.rset()
            assert not smtp.sendmail('origem@externo.test',['josé@ensaio.test'],raw,mail_options=['SMTPUTF8','BODY=8BITMIME'])
        assert lab.sql('SELECT COUNT(*) FROM correio_cartas')=='1'
        passed('recebedor SMTPUTF8: depósito real, MIME/anexo e rejeição de relay')
        status,_,body=http('/carteiro/entrada'); assert status==200 and 'Homologação'.encode() in body,body
        assert http('/carteiro/mensagens/1/original')[2]==raw
        status,_,body=http('/carteiro/mensagens/1'); assert status==200 and 'ação.pdf'.encode() in body,body
        aid=lab.sql('SELECT id FROM correio_anexos LIMIT 1')
        assert http('/carteiro/mensagens/1/anexos/'+aid)[2]==b'%PDF-1.7\nensaio\n'
        assert http('/carteiro/enviar',{'csrf':'incorreto'})[0]==403
        passed('Carteiro: lista, leitor, original exato, anexo e recusa CSRF')
        with smtplib.SMTP('127.0.0.1',ports['agencia'],timeout=15) as smtp:
            smtp.ehlo(); assert smtp.mail('jose@ensaio.test')[0]>=500
            smtp.starttls(context=context); smtp.ehlo(); assert smtp.has_extn('SMTPUTF8')
            # SASL PLAIN suporta usuário Unicode; smtplib.login usa ASCII.
            import base64
            wrong=base64.b64encode('\0josé@ensaio.test\0errada'.encode()).decode()
            assert smtp.docmd('AUTH','PLAIN '+wrong)[0]==535
            sasl=base64.b64encode(('\0josé@ensaio.test\0'+password).encode()).decode()
            assert smtp.docmd('AUTH','PLAIN '+sasl)[0]==235
            try:
                smtp.sendmail('josé@ensaio.test',['josé@ensaio.test'],raw,mail_options=['SMTPUTF8','BODY=8BITMIME'])
                raise AssertionError('autor de terceiro aceito')
            except smtplib.SMTPDataError as exc: assert exc.smtp_code==550
            msg.replace_header('From','José <josé@ensaio.test>')
            msg.replace_header('Message-ID','<agencia5@ensaio.test>')
            assert smtp.sendmail('josé@ensaio.test',['josé@ensaio.test'],msg.as_bytes(),mail_options=['SMTPUTF8','BODY=8BITMIME'])=={}
        passed('agência STARTTLS: exigência TLS, AUTH Unicode, senha inválida e fila')
        with smtplib.SMTP_SSL('127.0.0.1',ports['tls'],context=context,timeout=10) as smtp:
            smtp.ehlo(); assert smtp.docmd('AUTH','PLAIN '+sasl)[0]==235
        passed('agência TLS implícito com certificado de ensaio verificado')
        run=lab.run([str(ROOT/'src/santafé'),'-E','-P','-e',lab.bootstrap,str(ROOT/'aplicativos/correio/envios.fé')])
        assert lab.sql("SELECT COUNT(*) FROM correio_fila WHERE estado='entregue'")=='1',run.stdout+run.stderr
        assert lab.sql('SELECT COUNT(*) FROM correio_cartas WHERE direcao="entrada"')=='2'
        passed('envios: fila real → transporte local → entrega persistida')
        with imaplib.IMAP4_SSL('127.0.0.1',ports['imap'],ssl_context=context,timeout=10) as imap:
            imap.authenticate('PLAIN',lambda _: ('\0josé@ensaio.test\0'+password).encode())
            assert imap.select('INBOX')[0]=='OK'
            typ,data=imap.uid('SEARCH',None,'ALL'); assert typ=='OK' and len(data[0].split())==2,data
            uid=data[0].split()[0]
            typ,data=imap.uid('FETCH',uid,'(BODY.PEEK[])'); assert typ=='OK' and any(isinstance(x,tuple) and x[1]==raw for x in data),data
            typ,folders=imap.list(); assert typ=='OK'; print('Pastas:',folders,flush=True)
            typ,data=imap.uid('COPY',uid,'Lixeira'); assert typ=='OK',data
            assert imap.response('COPYUID')[1][0] is not None
            assert imap.select('Lixeira')[0]=='OK'
            assert imap.store('1','+FLAGS',r'(\Deleted)')[0]=='OK'; assert imap.expunge()[0]=='OK'
            typ,data=imap.append('Rascunhos',None,None,raw)
            assert typ=='NO' and b'From' in b' '.join(data),data
            typ,data=imap.append('Rascunhos',None,None,msg.as_bytes()); assert typ=='OK',data
        assert lab.sql("SELECT COUNT(*) FROM correio_cartas WHERE pasta='lixeira'")=='0'
        assert lab.sql("SELECT COUNT(*) FROM correio_cartas WHERE pasta='rascunhos'")=='1'
        passed('IMAP: AUTH Unicode, SELECT/SEARCH/FETCH, UID COPY, EXPUNGE e APPEND')
        assert http('/carteiro/mensagens/1/mover',{'csrf':csrf,'pasta':'lixeira'})[0]==303
        assert lab.sql('SELECT pasta FROM correio_cartas WHERE id=1')=='lixeira'
        assert http('/carteiro/mensagens/acao-em-lote',{'csrf':csrf,'pastaDeOrigem':'lixeira','acao':'restaurar','carta_1':'1'})[0]==303
        assert lab.sql('SELECT pasta FROM correio_cartas WHERE id=1')=='arquivadas'
        assert http('/carteiro/mensagens/1/mover',{'csrf':csrf,'pasta':'lixeira'})[0]==303
        assert http('/carteiro/lixeira/esvaziar',{'csrf':csrf})[0]==303
        assert lab.sql('SELECT COUNT(*) FROM correio_cartas WHERE id=1')=='0'
        passed('Carteiro: mover, restaurar em lote e esvaziar Lixeira sincronizados com banco')
        status,_,body=http('/carteiro/enviar',{'csrf':csrf,'para':'josé@ensaio.test','assunto':'Compositor real','texto':'texto íntegro'})
        assert status in (302,303), (status,body)
        lab.run([str(ROOT/'src/santafé'),'-E','-P','-e',lab.bootstrap,str(ROOT/'aplicativos/correio/envios.fé')])
        assert int(lab.sql("SELECT COUNT(*) FROM correio_cartas WHERE assunto='Compositor real'"))>=2
        passed('Carteiro: compositor HTTP → fila → entrega/Enviadas')
        before=lab.sql('SELECT id,uid_imap,pasta,tamanho FROM correio_cartas ORDER BY id')
        for name,entry in [('imap','correio/imap'),('carteiro','carteiro/carteiro')]:
            processes[name].terminate(); processes[name].wait(timeout=10)
            p=lab.app(name+'-reinicio','aplicativos/'+entry+'.fé'); lab.wait(p,ports[name],name+'-reinicio')
        for _ in range(100):
            if http('/carteiro/estado')[0]==200: break
            time.sleep(.1)
        assert http('/carteiro/entrada')[0]==200
        assert lab.sql('SELECT id,uid_imap,pasta,tamanho FROM correio_cartas ORDER BY id')==before
        passed('reinício dos aplicativos sem perder IDs, UIDs, pastas ou conteúdo persistido')
        zone=lab.path/'zonas.fé'
        zone.write_text('retorne {zonas={{nome="ensaio.test",registros={{nome="@",tipo="SOA",dados={mestre="ns",responsável="dns",série=1,atualização=3600,novaTentativa=600,expiração=86400,mínimo=300}},{nome="@",tipo="NS",dados="ns"},{nome="ns",tipo="A",dados="127.0.0.1"},{nome="www",tipo="A",dados="192.0.2.10"}}}}}')
        p=lab.app('autoridade','aplicativos/nomes/autoridade.fé',dict(NOMES_ZONAS_ARQUIVO=str(zone),NOMES_AUTORIDADE_ENDERECO='127.0.0.1',NOMES_AUTORIDADE_PORTA=str(ports['autoridade'])))
        lab.wait(p,ports['autoridade'],'autoridade')
        for tcp in (False,True):
            flags,an,answer=dns(ports['autoridade'],'www.ensaio.test',tcp); assert flags&1024 and an==1 and b'\xc0\x00\x02\x0a' in answer
            assert dns(ports['autoridade'],'ausente.ensaio.test',tcp)[0]&15==3
        passed('Nomes autoridade: UDP/TCP, resposta autoritativa e NXDOMAIN')
        prelude='local R=importe "nomes.resolvedor"; local novo=R.novo; R.novo=função(o) o.servidoresRaiz={"127.0.0.1"}; o.portaExterna='+str(ports['autoridade'])+'; retorne novo(o) fim'
        for name,prefix in [('resolvedor','127.0.0.0/8'),('negado','192.0.2.0/24')]:
            p=lab.app(name,'aplicativos/nomes/resolvedor.fé',dict(NOMES_RESOLVEDOR_ENDERECO='127.0.0.1',NOMES_RESOLVEDOR_PORTA=str(ports[name]),NOMES_RESOLVEDOR_PREFIXOS=prefix),prelude)
            lab.wait(p,ports[name],name)
        for tcp in (False,True):
            for _ in range(2):
                flags,an,answer=dns(ports['resolvedor'],'www.ensaio.test',tcp); assert flags&15==0 and an==1,answer
        # Contrato antiamplificação: ACL descarta UDP e fecha TCP, não responde REFUSED.
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as denied:
            denied.settimeout(1); denied.connect(('127.0.0.1',ports['negado']))
            denied.send(struct.pack('!6H',3105,256,1,0,0,0)+b'\x03www\x06ensaio\x04test\0\0\x01\0\x01')
            try: denied.recv(4096); raise AssertionError('ACL respondeu a origem proibida')
            except socket.timeout: pass
        with socket.create_connection(('127.0.0.1',ports['negado']),timeout=3) as denied:
            assert denied.recv(1)==b'', 'ACL TCP deve fechar a conexão'
        passed('Nomes resolvedor: raiz injetada local, cache UDP/TCP, descarte UDP e fechamento TCP por ACL')
        import runpy
        carga=runpy.run_path(str(ROOT/'experimentos/dados-v6/carga.py'))
        carga['execute'](lab,ports,http,context,password,dns)
        for path in lab.path.glob('*.pulso'):
            records=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            assert records and all(x['protocolo']=='PULSO' for x in records)
        passed('PULSO dos processos preserva JSON interoperável')
finally:
    (ROOT/'evidencias').mkdir(exist_ok=True)
    (ROOT/'evidencias/aplicativos5.json').write_text(json.dumps({'passaram':results,'esperados':13},ensure_ascii=False,indent=2)+'\n')
