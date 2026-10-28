#!/usr/bin/env python3
"""Ensaia falhas/quedas reais do publicador privado; não usa systemd do host."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from transacao import Transacao, Recusa, atomic, fingerprint


class Supervisor:
    def __init__(self, path):
        self.path = path
        self.events = []
        self.fail_start = None
        self.mutate_stop = None

    def states(self):
        return json.loads(self.path.read_text())

    def active(self, name):
        return self.states()[name]

    def change(self, name, value):
        d = self.states()
        d[name] = value
        atomic(self.path, json.dumps(d).encode())
        self.events.append(('start' if value else 'stop', name))

    def start(self, name):
        if self.fail_start == name:
            self.fail_start = None
            raise RuntimeError('Falha de início injetada')
        self.change(name, True)

    def stop(self, name):
        self.change(name, False)
        if self.mutate_stop:
            f, self.mutate_stop = self.mutate_stop, None
            f()


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='santafe-transacao23-')
        self.lab = Path(self.temp.name).resolve()
        self.root = self.lab/'replica'
        self.payload = self.lab/'pacote'
        for p in (self.root, self.payload):
            p.mkdir(mode=0o700)
        (self.root/'.replica-iba3').write_text('REPLICA_ISOLADA_SEM_PRODUCAO\n')
        self.unit_path = self.lab/'unidades.json'
        self.states = {'correio': True, 'carteiro': True, 'fila': False}
        self.unit_path.write_text(json.dumps(self.states))
        self.supervisor = Supervisor(self.unit_path)
        self.old = {'usr/local/bin/santafé': b'IBA2', 'opt/carteiro/pagina.fé': b'ANTIGA'}
        self.new = {'usr/local/bin/santafé': b'IBA3', 'opt/carteiro/pagina.fé': b'NOVA',
                    'usr/local/lib/santafé/3.0/bibc/nova.so': b'NATIVO3'}
        for base, contents in ((self.root, self.old), (self.payload, self.new)):
            for n, data in contents.items():
                p = base/n
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
                p.chmod(0o755 if n.endswith('santafé') else 0o640)
        (self.root/'var/lib/correio').mkdir(parents=True)
        self.message = self.root/'var/lib/correio/mensagem'
        self.message.write_bytes(b'RECEBIDA_ANTES')
        self.fail_health = False
        self.tx = Transacao(self.root, self.supervisor, self.health)

    def tearDown(self):
        self.temp.cleanup()

    def health(self, generation):
        if generation == 'candidata' and self.fail_health:
            self.message.write_bytes(b'RECEBIDA_DEPOIS')
            raise RuntimeError('Saúde falhou')
        expected = self.new if generation == 'candidata' else self.old
        for name, data in expected.items():
            self.assertEqual((self.root/name).read_bytes(), data)

    def prepare(self):
        self.tx.prepare(self.payload, list(self.states))

    def assert_old(self):
        for name, data in self.old.items():
            self.assertEqual((self.root/name).read_bytes(), data)
        self.assertFalse((self.root/'usr/local/lib/santafé/3.0/bibc/nova.so').exists())
        self.assertEqual(self.supervisor.states(), self.states)

    def test_success_and_reverse_preserve_messages_and_modes(self):
        self.prepare()
        before = {n: fingerprint(self.root/n) for n in self.old}
        self.tx.apply()
        self.assertEqual(self.tx.load()['fase'], 'CONCLUIDA')
        self.assertEqual(self.supervisor.events[:2], [('stop', 'carteiro'), ('stop', 'correio')])
        self.assertEqual(self.supervisor.events[2:], [('start', 'correio'), ('start', 'carteiro')])
        self.message.write_bytes(b'RECEBIDA_DEPOIS')
        self.tx.reverse_completed()
        self.assert_old()
        self.assertEqual(before, {n: fingerprint(self.root/n) for n in self.old})
        self.assertEqual(self.message.read_bytes(), b'RECEBIDA_DEPOIS')
        self.assertEqual(self.tx.recover(), 'REVERTIDA')

    def test_health_failure_never_restores_database(self):
        self.prepare()
        self.fail_health = True
        with self.assertRaisesRegex(RuntimeError, 'Saúde'):
            self.tx.apply()
        self.assert_old()
        self.assertEqual(self.message.read_bytes(), b'RECEBIDA_DEPOIS')

    def test_failure_start_restores_prior_active_set(self):
        self.prepare()
        self.supervisor.fail_start = 'carteiro'
        with self.assertRaisesRegex(RuntimeError, 'início'):
            self.tx.apply()
        self.assert_old()

    def test_source_drift_before_stop(self):
        self.prepare()
        (self.root/'opt/carteiro/pagina.fé').write_bytes(b'EDICAO')
        with self.assertRaisesRegex(Recusa, 'divergiu'):
            self.tx.apply()
        self.assertEqual(self.supervisor.events, [])

    def test_state_drift_before_stop(self):
        self.prepare()
        self.supervisor.change('fila', True)
        with self.assertRaisesRegex(Recusa, 'Estado'):
            self.tx.apply()
        self.assertEqual(self.supervisor.states(), {**self.states, 'fila': True})

    def test_drift_during_stop_preserves_operator_edit(self):
        self.prepare()
        changed = self.root/'opt/carteiro/pagina.fé'
        self.supervisor.mutate_stop = lambda: changed.write_bytes(b'EDICAO')
        # Saúde da versão anterior detectará a edição. Nunca a sobrescreve.
        with self.assertRaises((Recusa, AssertionError)):
            self.tx.apply()
        self.assertEqual(changed.read_bytes(), b'EDICAO')
        self.assertEqual((self.root/'usr/local/bin/santafé').read_bytes(), b'IBA2')

    def test_corrupt_payload_before_stop(self):
        self.prepare()
        e = self.tx.load()['arquivos'][0]
        (self.tx.work/e['depois']['sha256']).write_bytes(b'CORROMPIDO')
        with self.assertRaisesRegex(Recusa, 'corrompido'):
            self.tx.apply()
        self.assertEqual(self.supervisor.events, [])

    def test_corrupt_backup_blocks_reversal_without_partial_restore(self):
        self.prepare()
        self.tx.apply()
        e = next(e for e in self.tx.load()['arquivos'] if e['antes'])
        (self.tx.work/e['antes']['sha256']).write_bytes(b'CORROMPIDO')
        with self.assertRaisesRegex(Recusa, 'corrompido'):
            self.tx.reverse_completed()
        for name, data in self.new.items():
            self.assertEqual((self.root/name).read_bytes(), data)
        self.assertFalse(any(self.supervisor.states().values()))

    def test_external_edit_after_success_blocks_reversal(self):
        self.prepare()
        self.tx.apply()
        p = self.root/'usr/local/bin/santafé'
        p.write_bytes(b'ALTERACAO_EXTERNA')
        with self.assertRaises(Recusa):
            self.tx.reverse_completed()
        self.assertEqual(p.read_bytes(), b'ALTERACAO_EXTERNA')

    def test_lock(self):
        self.prepare()
        with self.tx.lock(), self.assertRaises(BlockingIOError):
            self.tx.apply()
        self.assert_old()

    def test_forbidden_data_destination(self):
        p = self.payload/'var/lib/correio/mensagem'
        p.parent.mkdir(parents=True)
        p.write_bytes(b'NAO_ESCREVER')
        with self.assertRaises(Recusa):
            self.prepare()
        self.assertFalse(self.tx.journal.exists())
        self.assertEqual(self.message.read_bytes(), b'RECEBIDA_ANTES')

    def test_symlink_ancestor(self):
        p = self.root/'usr/local/lib'
        p.symlink_to(self.lab)
        with self.assertRaises(Recusa):
            self.prepare()

    def test_hardlink_target(self):
        os.link(self.root/'usr/local/bin/santafé', self.lab/'alheio')
        with self.assertRaises(Recusa):
            self.prepare()

    def test_repeated_prepare_refused(self):
        self.prepare()
        with self.assertRaises(Recusa):
            self.prepare()

    def test_crash_recovery_each_boundary(self):
        points = ['parou:fila', 'parou:carteiro', 'parou:correio', 'iniciou']
        points += [kind + ':' + name for name in self.new for kind in ('antes', 'depois')]
        for point in points:
            with self.subTest(point=point):
                # Cada execução usa uma réplica e diário novos.
                case = Tests('test_success_and_reverse_preserve_messages_and_modes')
                case.setUp()
                try:
                    case.prepare()
                    pid = os.fork()
                    if not pid:
                        case.tx.hook = lambda p: os._exit(73) if p == point else None
                        case.tx.apply()
                        os._exit(99)
                    _, code = os.waitpid(pid, 0)
                    self.assertEqual(os.WEXITSTATUS(code), 73)
                    case.tx.recover()
                    case.assert_old()
                    self.assertEqual(case.message.read_bytes(), b'RECEBIDA_ANTES')
                finally:
                    case.tearDown()


if __name__ == '__main__':
    unittest.main(verbosity=2)
