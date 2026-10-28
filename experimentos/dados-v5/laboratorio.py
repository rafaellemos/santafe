"""Infraestrutura exclusiva de ensaio; nunca lê ambientes operacionais."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]

def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

class Lab:
    def __init__(self):
        assert (ROOT/'.laboratorio-dados5').is_file(), 'somente árvore candidata'
        assert shutil.disk_usage('/tmp').free >= (2048+128)*1024**2, 'reserva de disco insuficiente para banco descartável'
        self.path = Path(tempfile.mkdtemp(prefix='santafe-apps5-', dir='/tmp'))
        self.env = {k: os.environ[k] for k in ('PATH', 'TMPDIR', 'LANG', 'LC_ALL') if k in os.environ}
        self.env['GSETTINGS_BACKEND'] = 'memory'
        self.processes = []
        self.handles = []
        self.bootstrap = ('módulo.caminho="'+str(ROOT)+'/bibs/bibf/?.fé;'+str(ROOT)+'/bibs/bibf/?/?.fé"; '
                          'módulo.caminhoC="'+str(ROOT)+'/bibs/bibc/?/?.so"')
    def __enter__(self): return self
    def __exit__(self, *args):
        for p in reversed(self.processes):
            if p.poll() is None:
                p.terminate()
                try: p.wait(timeout=10)
                except subprocess.TimeoutExpired: p.kill(); p.wait()
        for h in self.handles: h.close()
        print('Laboratório encerrado; logs:', self.path, flush=True)
    def run(self, args, **kwargs):
        result = subprocess.run(args, cwd=ROOT, env=self.env, text=True, capture_output=True,
                                timeout=40, **kwargs)
        if result.returncode:
            raise RuntimeError(str(args)+'\n'+result.stdout+result.stderr)
        return result
    def sf(self, code):
        return self.run([str(ROOT/'src/santafé'), '-E', '-P', '-e', self.bootstrap, '-e', code]).stdout.strip()
    def start(self, name, args, extra=None):
        h = open(self.path/(name+'.log'), 'w'); self.handles.append(h)
        p = subprocess.Popen(args, cwd=ROOT, env=dict(self.env, **(extra or {})), stdout=h, stderr=h)
        self.processes.append(p)
        return p
    def app(self, name, entry, extra=None, prelude=''):
        return self.start(name, [str(ROOT/'src/santafé'), '-E', '-P', '-e', self.bootstrap,
                                '-e', prelude or 'local ensaio=verdadeiro', str(ROOT/entry)], extra)
    def wait(self, p, number, name):
        deadline = time.monotonic()+25
        while time.monotonic()<deadline:
            assert p.poll() is None, (self.path/(name+'.log')).read_text()
            try:
                with socket.create_connection(('127.0.0.1', number), timeout=.2): return
            except OSError: time.sleep(.1)
        raise AssertionError('porta não iniciou: '+name+'\n'+(self.path/(name+'.log')).read_text())
    def database(self):
        self.sock = self.path/'m.sock'
        self.dbtmp = self.path/'temporarios-db'
        self.dbtmp.mkdir(mode=0o700)
        dbport = port()
        self.run(['mariadb-install-db', '--no-defaults', f'--tmpdir={self.dbtmp}', f'--datadir={self.path}/dados',
                  '--auth-root-authentication-method=normal', '--skip-test-db'])
        p = self.start('mariadb', [shutil.which('mariadbd') or '/usr/sbin/mariadbd', '--no-defaults',
            f'--tmpdir={self.dbtmp}', f'--datadir={self.path}/dados', f'--socket={self.sock}', f'--port={dbport}',
            '--bind-address=127.0.0.1', f'--pid-file={self.path}/pid', '--skip-log-bin',
            '--innodb-buffer-pool-size=64M', '--innodb-log-file-size=16M', '--max-connections=40'])
        self.wait(p, dbport, 'mariadb')
        assert Path(self.sql('SELECT @@tmpdir;', False)).resolve()==self.dbtmp.resolve()
        self.sql("CREATE DATABASE apps5 CHARACTER SET utf8mb4; CREATE USER 'ensaio'@'127.0.0.1' IDENTIFIED BY 'somente-laboratorio'; GRANT ALL ON apps5.* TO 'ensaio'@'127.0.0.1';", False)
        self.sql((ROOT/'testes/recursos/correio-base-mariadb.sql').read_text()+'\n'+(ROOT/'aplicativos/correio/banco/estrutura.sql').read_text())
        self.env.update(SANTAFE_MARIADB_HOST='127.0.0.1', SANTAFE_MARIADB_PORTA=str(dbport),
            SANTAFE_MARIADB_USUARIO='ensaio', SANTAFE_MARIADB_SENHA='somente-laboratorio',
            SANTAFE_MARIADB_BANCO='apps5', CORREIO_PISCINA_MINIMA='1', CORREIO_PISCINA_MAXIMA='3')
    def sql(self, text, use=True):
        return self.run(['mariadb', '--no-defaults', '--protocol=socket', f'--socket={self.sock}',
                         '-uroot', '--batch', '--skip-column-names'], input=('USE apps5;\n' if use else '')+text).stdout.strip()
