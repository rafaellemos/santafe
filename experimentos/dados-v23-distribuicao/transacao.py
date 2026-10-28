#!/usr/bin/env python3
"""Troca coordenada de arquivos em RÉPLICA PRIVADA, com diário e reversão.

Não possui adaptador para systemd da máquina nem aceita raiz de produção.
Bancos, mensagens, depósitos e certificados em uso não são destinos.
O chamador fornece o supervisor isolado e a verificação de saúde.
"""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile


class Recusa(RuntimeError):
    pass


def syncdir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def regular(path):
    s = path.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
        raise Recusa('Exige arquivo regular sem ligações: ' + str(path))
    return s


def fingerprint(path):
    try:
        s = regular(path)
    except FileNotFoundError:
        return None
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'modo': stat.S_IMODE(s.st_mode)}


def atomic(path, data, mode=0o600):
    fd, tmp = tempfile.mkstemp(prefix='.iba3-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            os.fchmod(f.fileno(), mode)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        syncdir(path.parent)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def private_directory(path):
    s = path.lstat()
    if (not stat.S_ISDIR(s.st_mode) or s.st_uid != os.getuid()
            or stat.S_IMODE(s.st_mode) & 0o077):
        raise Recusa('Exige diretório privado do usuário atual')


def relative(name):
    p = PurePosixPath(name)
    if (not name or p.is_absolute() or '..' in p.parts or str(p) != name
            or '\\' in name or '\0' in name):
        raise Recusa('Caminho inválido')
    return p


class Transacao:
    def __init__(self, root, supervisor, health, hook=lambda name: None):
        # resolve() não pode esconder uma ligação no caminho fornecido.
        self.root = Path(root).absolute()
        if self.root != self.root.resolve():
            raise Recusa('Raiz com ligação simbólica')
        private_directory(self.root)
        marker = self.root/'.replica-iba3'
        regular(marker)
        if marker.read_text() != 'REPLICA_ISOLADA_SEM_PRODUCAO\n':
            raise Recusa('Raiz não reconhecida como réplica')
        self.work = self.root/'.migracao-iba3'
        self.work.mkdir(mode=0o700, exist_ok=True)
        private_directory(self.work)
        self.supervisor, self.health, self.hook = supervisor, health, hook
        self.journal = self.work/'diario.json'

    @contextlib.contextmanager
    def lock(self):
        fd = os.open(self.work/'trava', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            if os.fstat(fd).st_nlink != 1:
                raise Recusa('Trava com ligação')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(fd)

    def target(self, name, create=False):
        p = relative(name)
        # Allowlist deliberadamente curta; nunca var/lib, var/spool ou banco.
        parts = p.parts
        allowed = (parts[:2] == ('usr', 'local') or parts[0] == 'opt'
                   or parts[:2] in (('etc', 'santafe'), ('etc', 'paodocafe')))
        if not allowed or any(x in ('letsencrypt', 'mysql', 'mariadb') for x in parts[:-1]):
            raise Recusa('Destino fora do contrato de código/configuração')
        current = self.root
        for component in parts[:-1]:
            current /= component
            if not current.exists() and not current.is_symlink():
                if not create:
                    # Verifica os ancestrais existentes, mesmo para arquivo novo.
                    continue
                current.mkdir(mode=0o700)
                syncdir(current.parent)
            if current.exists() or current.is_symlink():
                if not stat.S_ISDIR(current.lstat().st_mode):
                    raise Recusa('Ancestral não é diretório regular')
        target = self.root/name
        if target.exists() or target.is_symlink():
            regular(target)
        return target

    def save(self, journal):
        atomic(self.journal, (json.dumps(journal, ensure_ascii=False, indent=2)+'\n').encode())

    def load(self):
        regular(self.journal)
        return json.loads(self.journal.read_text())

    def blob(self, digest):
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise Recusa('Identidade de conteúdo inválida')
        p = self.work/digest
        regular(p)
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise Recusa('Cópia de segurança ou conteúdo novo corrompido')
        return data

    def prepare(self, payload, units):
        payload = Path(payload).resolve()
        private_directory(payload)
        with self.lock():
            if self.journal.exists():
                raise Recusa('Transação já registrada; recupere ou revise antes de outra')
            if not units or len(units) != len(set(units)):
                raise Recusa('Lista de consumidores vazia ou repetida')
            entries = []
            for source in sorted(payload.rglob('*')):
                if source.is_symlink():
                    raise Recusa('Ligação no pacote')
                if source.is_dir():
                    continue
                new = fingerprint(source)
                name = source.relative_to(payload).as_posix()
                target = self.target(name)
                old = fingerprint(target)
                if new == old:
                    continue
                for file, fp in ((source, new), (target, old)):
                    if fp:
                        data = file.read_bytes()
                        if hashlib.sha256(data).hexdigest() != fp['sha256']:
                            raise Recusa('Arquivo mudou durante a preparação')
                        atomic(self.work/fp['sha256'], data)
                entries.append({'nome': name, 'antes': old, 'depois': new})
            if not entries:
                raise Recusa('Nenhum arquivo para trocar')
            active = {u: self.supervisor.active(u) for u in units}
            if any(type(v) is not bool for v in active.values()):
                raise Recusa('Estado de consumidor desconhecido')
            self.save({'schema': 1, 'fase': 'PREPARADA', 'unidades': units,
                       'ativos': active, 'arquivos': entries, 'tocados': []})

    def verify(self, j, field):
        for e in j['arquivos']:
            if fingerprint(self.target(e['nome'])) != e[field]:
                raise Recusa('Arquivo divergiu do plano: ' + e['nome'])
            if e[field]:
                self.blob(e[field]['sha256'])

    def stopped(self, units):
        for unit in reversed(units):
            if self.supervisor.active(unit):
                self.supervisor.stop(unit)
                if self.supervisor.active(unit):
                    raise Recusa('Consumidor não parou: ' + unit)

    def original_states(self, j):
        for u in j['unidades']:
            if j['ativos'][u] and not self.supervisor.active(u):
                self.supervisor.start(u)
            if self.supervisor.active(u) != j['ativos'][u]:
                raise Recusa('Estado do consumidor não foi restaurado: ' + u)

    def revert(self, j):
        # Confere TODAS as cópias e conflitos antes de restaurar qualquer arquivo.
        # Em conflito, mantém consumidores parados e diário intacto para revisão.
        self.stopped(j['unidades'])
        touched = [e for e in j['arquivos'] if e['nome'] in j['tocados']]
        for e in touched:
            current = fingerprint(self.target(e['nome']))
            if current not in (e['antes'], e['depois']):
                raise Recusa('Conflito durante reversão: ' + e['nome'])
            if e['antes']:
                self.blob(e['antes']['sha256'])
        j['fase'] = 'REVERTENDO'
        self.save(j)
        for e in reversed(touched):
            target = self.target(e['nome'], create=True)
            if e['antes']:
                atomic(target, self.blob(e['antes']['sha256']), e['antes']['modo'])
            elif target.exists():
                target.unlink()
                syncdir(target.parent)
            self.hook('reversao:' + e['nome'])
        self.original_states(j)
        self.health('anterior')
        j['fase'] = 'REVERTIDA'
        self.save(j)

    def recover(self):
        with self.lock():
            j = self.load()
            if j['fase'] in ('PREPARADA', 'REVERTIDA', 'CONCLUIDA'):
                return j['fase']
            self.revert(j)
            return 'REVERTIDA'

    def apply(self):
        with self.lock():
            j = self.load()
            if j['fase'] != 'PREPARADA':
                raise Recusa('Recupere a transação antes de aplicar')
            self.verify(j, 'antes')
            # Verifica também o candidato completo antes de parar consumidores.
            for e in j['arquivos']:
                self.blob(e['depois']['sha256'])
            if any(self.supervisor.active(u) != j['ativos'][u] for u in j['unidades']):
                raise Recusa('Estado dos consumidores divergiu do plano')
            j['fase'] = 'PARANDO'
            self.save(j)
            try:
                for u in reversed(j['unidades']):
                    if j['ativos'][u]:
                        self.supervisor.stop(u)
                        if self.supervisor.active(u):
                            raise Recusa('Consumidor não parou: ' + u)
                    self.hook('parou:' + u)
                self.verify(j, 'antes')
                j['fase'] = 'TROCANDO'
                self.save(j)
                for e in j['arquivos']:
                    # Intenção persistida antes da troca: queda entre os dois
                    # passos é recuperada comparando o conteúdo antigo e novo.
                    j['tocados'].append(e['nome'])
                    self.save(j)
                    self.hook('antes:' + e['nome'])
                    atomic(self.target(e['nome'], create=True),
                           self.blob(e['depois']['sha256']), e['depois']['modo'])
                    self.hook('depois:' + e['nome'])
                self.verify(j, 'depois')
                j['fase'] = 'INICIANDO'
                self.save(j)
                self.original_states(j)
                self.hook('iniciou')
                self.health('candidata')
                j['fase'] = 'CONCLUIDA'
                self.save(j)
            except Exception:
                self.revert(j)
                raise

    def reverse_completed(self):
        with self.lock():
            j = self.load()
            if j['fase'] != 'CONCLUIDA':
                raise Recusa('A transação não está concluída')
            self.verify(j, 'depois')
            self.revert(j)
