#!/usr/bin/env python3
"""Instância temporária própria; --no-defaults, loopback e sem sudo."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import tempfile

ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados3').is_file()
env={k:os.environ[k] for k in ('PATH','TMPDIR','LANG','LC_ALL') if k in os.environ}
env['GSETTINGS_BACKEND']='memory'
daemon=shutil.which('mariadbd') or '/usr/sbin/mariadbd'
assert Path(daemon).is_file()
assert shutil.disk_usage('/tmp').free >= (2048+128)*1024**2, 'reserva de disco insuficiente para banco descartável'
lab=Path(tempfile.mkdtemp(prefix='santafe-dados3-banco-',dir='/tmp'))
sock=lab/'m.sock'; data=lab/'dados'
with socket.socket() as s:
    s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
log=open(lab/'servidor.log','w')
subprocess.run(['mariadb-install-db','--no-defaults',f'--datadir={data}',
                '--auth-root-authentication-method=normal','--skip-test-db'],
               check=True,stdout=log,stderr=log,env=env)
p=subprocess.Popen([daemon,'--no-defaults',f'--datadir={data}',f'--socket={sock}',
    f'--port={port}','--bind-address=127.0.0.1',f'--pid-file={lab}/pid',
    '--skip-log-bin','--innodb-buffer-pool-size=64M','--innodb-log-file-size=16M','--max-connections=16'],env=env,stdout=log,stderr=log)
results=[]
try:
    def sql(text):
        return subprocess.run(['mariadb','--no-defaults','--protocol=socket',f'--socket={sock}',
                               '-uroot','--batch'],input=text,text=True,capture_output=True,env=env)
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        if p.poll() is not None: raise RuntimeError((lab/'servidor.log').read_text())
        if sock.exists() and sql('SELECT 1').returncode==0: break
        time.sleep(.1)
    else: raise RuntimeError('MariaDB temporário não iniciou')
    setup=sql("CREATE DATABASE dados3 CHARACTER SET utf8mb4; CREATE USER 'ensaio'@'127.0.0.1' IDENTIFIED BY 'somente-laboratorio'; GRANT ALL ON dados3.* TO 'ensaio'@'127.0.0.1';")
    assert setup.returncode==0, setup.stderr
    env.update(SANTAFE_DADOS3_BANCO='isolado', SANTAFE_MARIADB_HOST='127.0.0.1',
        SANTAFE_MARIADB_USUARIO='ensaio',SANTAFE_MARIADB_SENHA='somente-laboratorio',
        SANTAFE_MARIADB_BANCO='dados3',SANTAFE_MARIADB_PORTA=str(port))
    bootstrap='módulo.caminho="bibs/bibf/?.fé;bibs/bibf/?/?.fé"; módulo.caminhoC="bibs/bibc/?/?.so"'
    schema=sql('USE dados3;\n'+(ROOT/'testes/recursos/correio-base-mariadb.sql').read_text()+'\n'+
               (ROOT/'aplicativos/correio/banco/estrutura.sql').read_text())
    assert schema.returncode==0, schema.stderr
    hash_source='local s=importe "segredo"; local r=importe "rede"; s.protejaSenhaAssíncrono("senha exclusiva do ensaio",função(h,falha) garanta(h,falha); mostre(h); r.pareLaço() fim); r.laço()'
    hashed=subprocess.run([str(ROOT/'src/santafé'),'-E','-P','-e',bootstrap,'-e',hash_source],
        cwd=ROOT,env=env,text=True,capture_output=True,check=True,timeout=20).stdout.strip()
    assert hashed.startswith('$argon2id$')
    env['SANTAFE_TESTE_SENHA_HASH']=hashed
    # Começa pelos contratos C; os demais ensaios postais dependem de um esquema
    # e de mensagens de ensaio próprios, não de dados copiados da produção.
    tests=['experimentos/dados-v3/testar-sql-nulo.fé',
           'testes/bibc/teste_mariadb_preparado.fé','testes/bibc/teste_mariadb_piscina.fé',
           'testes/bibc/teste_mariadb_piscina_ociosa.fé','testes/bibc/teste_correio_mariadb.fé',
           'testes/bibc/teste_correio_agência_mariadb.fé',
           'testes/bibc/teste_correio_autenticação_mariadb.fé',
           'testes/bibc/teste_correio_imap_mariadb.fé',
           'testes/bibc/teste_correio_imap_append_mariadb.fé',
           'testes/bibc/teste_correio_quarentena_mariadb.fé',
           'testes/bibc/teste_correio_recuperação_mariadb.fé',
           'testes/bibc/teste_carteiro_conversas_mariadb.fé']
    for test in tests:
        if test.endswith('teste_correio_quarentena_mariadb.fé'):
            seed=sql("USE dados3; INSERT INTO correio_fila (direcao,estado,remetente,destinatarios,conteudo,tamanho,tentativas,proxima_tentativa,criada_em,atualizada_em) VALUES ('saída','pendente','quarentena@teste.local','{inválido','mime',4,0,0,1,1);")
            assert seed.returncode==0,seed.stderr
            for attempt in range(3):
                subprocess.run([str(ROOT/'src/santafé'),'-E','-P','-e',bootstrap,
                    'experimentos/dados-v3/quarentena-prepare.fé'],cwd=ROOT,env=env,check=True,timeout=15)
                state=sql("USE dados3; SELECT falhas_internas,estado FROM correio_fila WHERE remetente='quarentena@teste.local'")
                assert state.returncode==0 and f'{attempt+1}\t' in state.stdout,state.stderr+state.stdout
                if attempt==2: assert '\tquarentena' in state.stdout,state.stdout
                else: assert sql("USE dados3; UPDATE correio_fila SET proxima_tentativa=0 WHERE remetente='quarentena@teste.local'").returncode==0
        if test.endswith('teste_correio_recuperação_mariadb.fé'):
            seed=sql("""USE dados3;
INSERT INTO correio_fila (direcao,estado,remetente,destinatarios,conteudo,tamanho,tentativas,proxima_tentativa,criada_em,atualizada_em,bilhete,arrendada_ate)
VALUES ('saída','processando','recuperacao@teste.local','["destino@exemplo.org"]','mensagem',8,0,0,1,1,'reserva-carta-expirada',0);
SET @fila=LAST_INSERT_ID();
INSERT INTO correio_avisos_entrega (fila_id,tipo,estado,detalhes,tentativas,proxima_tentativa,bilhete,arrendada_ate,criada_em,atualizada_em)
VALUES (@fila,'atraso','processando','{"falha":"ensaio"}',0,0,'reserva-aviso-expirada',0,1,1);""")
            assert seed.returncode==0,seed.stderr
        try:
            run=subprocess.run([str(ROOT/'src/santafé'),'-E','-P','-e',bootstrap,test],
                cwd=ROOT,env=env,text=True,capture_output=True,timeout=40)
            status='PASSOU' if run.returncode==0 else 'FALHOU'
            output=run.stdout+run.stderr
        except subprocess.TimeoutExpired:
            status='FALHOU'; output='tempo limite'
        results.append(dict(teste=test,estado=status,saida=output))
        print(status,test,flush=True)
        print(output,flush=True)
        if test.endswith('teste_correio_quarentena_mariadb.fé') and status=='PASSOU':
            state=sql("USE dados3; SELECT falhas_internas,estado FROM correio_fila WHERE remetente='quarentena@teste.local'")
            assert '0\tpendente' in state.stdout,state.stdout
        if test.endswith('teste_correio_recuperação_mariadb.fé') and status=='PASSOU':
            state=sql("USE dados3; SELECT COUNT(*) FROM correio_fila WHERE remetente='recuperacao@teste.local' AND estado='pendente' AND bilhete IS NULL AND arrendada_ate IS NULL")
            assert state.stdout.strip().endswith('\n1'),state.stdout
    (ROOT/'evidencias/mariadb.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
finally:
    p.terminate()
    try: p.wait(timeout=15)
    except subprocess.TimeoutExpired: p.kill(); p.wait()
    log.close()
    print('Banco temporário parado; evidências preservadas em',lab,flush=True)
raise SystemExit(any(r['estado']!='PASSOU' for r in results))
