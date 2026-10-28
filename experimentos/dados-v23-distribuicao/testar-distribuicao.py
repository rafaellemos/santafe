#!/usr/bin/env python3
"""Instalação IBA3 real + troca coordenada 2.1→3→2.1 em prefixo privado."""
import argparse
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import tempfile

from transacao import Transacao

ROOT = Path(__file__).resolve().parents[2]


class Processes:
    """Consumidores reais do núcleo, sem serviços, rede ou dados do host."""
    def __init__(self, root):
        self.root = root
        self.children = {}
        self.versions = {}

    def active(self, name):
        p = self.children.get(name)
        return p is not None and p.poll() is None

    def start(self, name):
        assert not self.active(name)
        prefix = self.root/'usr/local'
        binary = prefix/'bin/santafé'
        version = subprocess.check_output([str(binary), '-E', '-P', '-v'], text=True)
        boot = ''
        if '3.0.0' in version:
            paths = str(prefix) + '/share/santafé/3.0/bibf/?.fé'
            cpaths = str(prefix) + '/lib/santafé/3.0/bibc/?.so'
            boot = 'módulo.caminho='+json.dumps(paths, ensure_ascii=False)+'; '
            boot += 'módulo.caminhoC='+json.dumps(cpaths, ensure_ascii=False)+'; '
            boot += 'garanta(importe "arquivo"); garanta(importe "correio.imap"); '
            boot += 'garanta(tipo([nulo])=="lista"); '
        code = boot + 'mostre("PRONTO"); es.esvazie(); es.leia()'
        proc = subprocess.Popen([str(binary), '-E', '-P', '-e', code],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, cwd=self.root)
        self.children[name] = proc
        self.versions[name] = version
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            if not selector.select(15) or proc.stdout.readline() != b'PRONTO\n':
                self.stop(name)
                raise RuntimeError('Consumidor não ficou pronto: ' + name)

    def stop(self, name):
        p = self.children[name]
        if p.poll() is None:
            p.stdin.close()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.terminate()
                p.wait(timeout=5)
        p.stdout.close()
        p.stderr.close()

    def close(self):
        for name in list(self.children):
            self.stop(name)


def main(stable):
    assert (ROOT/'.laboratorio-dados23').is_file()
    version = subprocess.check_output([str(stable), '-E', '-P', '-v'], text=True)
    assert '2.1.0' in version
    results = []
    with tempfile.TemporaryDirectory(prefix='santafe-distribuicao23-') as temp:
        lab = Path(temp).resolve()
        payload = lab/'pacote'
        payload.mkdir(mode=0o700)
        prefix = payload/'usr/local'
        platform = 'macosx' if sys.platform == 'darwin' else 'linux'
        for part in ('bin', 'sls', 'pacotes', 'c', 'fe', 'pc'):
            subprocess.run(['bash', str(ROOT/'ferramentas/instalar-arquivos.sh'),
                            part, str(prefix), platform, '3.0.0'],
                           cwd=ROOT, check=True, timeout=45)
        assert not (prefix/'share/santafé/1.0').exists()
        assert '-DSANTAFE_DADOS' not in (prefix/'lib/pkgconfig/santafe.pc').read_text()
        # A tentativa de compilar um SDK com o contrato desligado deve falhar.
        src = lab/'sdk.c'
        src.write_text('#include "lua.h"\nint main(void){return SANTAFE_ABI_MAJOR!=3;}\n')
        good = subprocess.run(['cc', '-I'+str(prefix/'include'), str(src), '-o', str(lab/'sdk')], capture_output=True)
        assert good.returncode == 0, good.stderr
        assert subprocess.run([str(lab/'sdk')]).returncode == 0
        bad = subprocess.run(['cc', '-DSANTAFE_DADOS_V3=0', '-I'+str(prefix/'include'), str(src), '-o', str(lab/'nao')], capture_output=True)
        assert bad.returncode != 0 and b'exige SANTAFE_DADOS_V3=1' in bad.stderr
        results.append('SDK padrão IBA3, sem opção privada; contrato desligado recusado')

        for failure in (False, True):
            root = lab/('replica-falha' if failure else 'replica')
            root.mkdir(mode=0o700)
            (root/'.replica-iba3').write_text('REPLICA_ISOLADA_SEM_PRODUCAO\n')
            oldbin = root/'usr/local/bin/santafé'
            oldbin.parent.mkdir(parents=True)
            shutil.copy2(stable, oldbin)
            oldsha = __import__('hashlib').sha256(oldbin.read_bytes()).hexdigest()
            data = root/'var/lib/correio/mensagem'
            data.parent.mkdir(parents=True)
            data.write_bytes(b'ANTES')
            supervisor = Processes(root)
            try:
                supervisor.start('consumidor-a')
                supervisor.start('consumidor-b')
                def health(generation):
                    expected = '3.0.0' if generation == 'candidata' else '2.1.0'
                    for name in ('consumidor-a', 'consumidor-b'):
                        assert supervisor.active(name)
                        assert expected in supervisor.versions[name]
                    assert not supervisor.active('fila-inativa')
                    if generation == 'candidata':
                        # Dado posterior à captura deve sobreviver à reversão.
                        data.write_bytes(b'DEPOIS')
                        helptext = subprocess.check_output([str(oldbin), 'instale', '--ajuda'], cwd=root, text=True)
                        assert '3.0.0' in helptext and '1.1.0' in helptext
                        if failure:
                            raise RuntimeError('Saúde injetada após início real')
                tx = Transacao(root, supervisor, health)
                tx.prepare(payload, ['consumidor-a', 'consumidor-b', 'fila-inativa'])
                if failure:
                    try:
                        tx.apply()
                    except RuntimeError as e:
                        assert str(e) == 'Saúde injetada após início real'
                    else:
                        raise AssertionError('Não exercitou a falha')
                else:
                    tx.apply()
                    assert tx.load()['fase'] == 'CONCLUIDA'
                    tx.reverse_completed()
                assert tx.load()['fase'] == 'REVERTIDA'
                assert __import__('hashlib').sha256(oldbin.read_bytes()).hexdigest() == oldsha
                assert data.read_bytes() == b'DEPOIS'
                assert not (root/'usr/local/lib/santafé/3.0/bibc/rede.so').exists()
                results.append(('falha de saúde' if failure else 'migração e reversão explícita') +
                               ': dois processos reais, fila inativa, módulos, ajuda e novos dados preservados')
            finally:
                supervisor.close()
            assert all(p.poll() is not None for p in supervisor.children.values())
        results.append('nenhum processo filho remanescente')
    report = {'resultado': 'PASSOU', 'grupos': results, 'sistema': sys.platform,
              'limites': 'Consumidores reais do núcleo; não é a réplica completa de bancos/aplicativos ou systemd.'}
    (ROOT/'evidencias').mkdir(exist_ok=True)
    (ROOT/'evidencias/distribuicao23.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    for name in results:
        print('PASSOU', name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('estavel', type=Path)
    main(parser.parse_args().estavel.resolve())
