#!/usr/bin/env python3
"""Transação de gerações somente em laboratório privado (POSIX).

O processo consumidor deve resolver `atual` UMA vez ao iniciar e usar a raiz
resolvida para executável, módulos e recursos. Não é publicador systemd/nginx.
Não migra nem restaura banco, depósitos ou arquivos criados pelo usuário.
"""
import contextlib, fcntl, hashlib, json, os, re, shutil, subprocess, tempfile
from pathlib import Path

def syncdir(path):
    fd=os.open(path,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)

def atomic(path, data):
    fd,tmp=tempfile.mkstemp(prefix='.gravando-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path); syncdir(path.parent)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def new():
    root=Path(tempfile.mkdtemp(prefix='santafe-operacao6-',dir='/tmp'))
    (root/'geracoes').mkdir(); (root/'dados').mkdir()
    atomic(root/'.laboratorio',b'dados.22\n')
    return root

def validate(root):
    root=Path(root).absolute()
    assert root.parent.resolve()==Path('/tmp').resolve() and root.name.startswith('santafe-operacao6-')
    assert not root.is_symlink() and root.stat().st_uid==os.getuid()
    assert root.stat().st_mode&0o077==0, 'laboratório deve ser privado'
    assert (root/'.laboratorio').read_bytes()==b'dados.22\n'
    for name in ('geracoes','dados'):
        assert (root/name).is_dir() and not (root/name).is_symlink()
    return root

@contextlib.contextmanager
def locked(root):
    root=validate(root)
    with (root/'.trava').open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield root

def generation(root, name):
    assert re.fullmatch(r'[a-zA-Z0-9_-]+',name)
    p=root/'geracoes'/name
    assert p.is_dir() and not p.is_symlink()
    return p

def hashes(path):
    result={}
    for p in sorted(path.rglob('*')):
        assert not p.is_symlink(), 'geração não aceita links'
        if p.is_file() and p != path/'manifesto.json':
            result[str(p.relative_to(path))]=[hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode&0o777]
    return result

def seal(path):
    atomic(path/'manifesto.json',json.dumps(hashes(path),sort_keys=True).encode())
    # Arquivos e diretórios persistidos antes de publicar o ponteiro.
    for p in path.rglob('*'):
        if p.is_file():
            with p.open('rb') as f: os.fsync(f.fileno())
    for p in sorted(path.rglob('*'),reverse=True):
        if p.is_dir(): syncdir(p)
    syncdir(path); syncdir(path.parent)

def current(root):
    if not os.path.lexists(root/'atual'): return None
    target=os.readlink(root/'atual')
    assert target.startswith('geracoes/') and target.count('/')==1
    name=target.split('/')[1]; generation(root,name); return name

def switch(root,name):
    generation(root,name)
    temp=root/'.proximo'
    if os.path.lexists(temp): temp.unlink()
    temp.symlink_to('geracoes/'+name)
    os.replace(temp,root/'atual'); syncdir(root)

def recover(root):
    journal=root/'transacao.json'
    if not journal.exists(): return
    info=json.loads(journal.read_text()); old=info['anterior']
    assert old is not None, 'primeira instalação não usa troca'
    generation(root,old)
    assert current(root) in (old,info['nova']), 'ponteiro alterado fora da transação'
    switch(root,old)
    journal.unlink(); syncdir(root)

def activate(root,name,health,fail=None):
    with locked(root) as root:
        recover(root)
        path=generation(root,name)
        assert hashes(path)==json.loads((path/'manifesto.json').read_text()), 'integridade da geração'
        health(path)
        old=current(root)
        if old==name: return
        if old is None: switch(root,name); return
        atomic(root/'transacao.json',json.dumps({'anterior':old,'nova':name}).encode())
        if fail=='antes': os._exit(91)
        switch(root,name)
        if fail=='depois': os._exit(92)
        try:
            health(path)
            if fail=='saude': raise RuntimeError('saúde pós-troca injetada')
        except BaseException:
            recover(root); raise
        (root/'transacao.json').unlink(); syncdir(root)

def stage(root,source,name):
    with locked(root) as root:
        assert re.fullmatch(r'[a-zA-Z0-9_-]+',name)
        prefix=root/'geracoes'/name
        assert not prefix.exists(), 'não sobrescrever geração'
        env={k:os.environ[k] for k in ('PATH','TMPDIR','LANG','LC_ALL') if k in os.environ}
        platform='macosx' if os.uname().sysname=='Darwin' else 'linux'
        for phase in ('bin','sls','pacotes','c','fe','pc'):
            subprocess.run(['bash',str(source/'ferramentas/instalar-arquivos.sh'),phase,str(prefix),platform,'0.0.0-dados.22'],
                           cwd=source,env=env,check=True,capture_output=True,timeout=60)
        seal(prefix)
    return prefix
