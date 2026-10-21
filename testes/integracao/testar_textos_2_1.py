#!/usr/bin/env python3
"""Revisão textual: escopo, deriva, symlinks, idempotência e rollback real."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = load(ROOT / 'operação/publicar-textos-2.1.0.py', 'pub_textos')
T = load(ROOT / 'operação/fechamento-2.0.py', 'transacao_textos')
C = load(ROOT / 'operação/preparar-conjunto.py', 'preparar_textos')


class Textos(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='santafe-textos-teste-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.bundle = self.root / 'bundle'; self.bundle.mkdir()
        self.manual = C.cache((ROOT / 'docs/manual.html').read_text(), '2.1.0')
        self.cli = (ROOT / 'ferramentas/pacotes/cli.fé').read_text()
        self.old_cli = self.cli.replace(
            'Catálogo oficial: ' + P.CATALOG + '\nDisponível na distribuição Santafé 2.1.0; pacote inicial: semver 1.0.0.',
            'O repositório público ainda não foi publicado.')
        self.assertEqual(hashlib.sha256(self.old_cli.encode()).hexdigest(), P.BEFORE_CLI)
        (self.bundle / 'manual.html').write_text(self.manual)
        (self.bundle / 'cli.fé').write_text(self.cli)
        self.targets = []
        for i, name in enumerate(('manual.html', 'manual.html', 'cli.fé')):
            target = self.root / ('target-' + str(i))
            target.write_text('anterior-' + str(i))
            target.chmod(0o640)
            self.targets.append((target, name, P.digest(target)))

    def test_textos_e_logica_preservada(self):
        P.text_checks(self.manual, self.cli, self.old_cli)

    def test_revisao_apenas_uma_frase(self):
        P.check_manual_revision(self.manual)
        with self.assertRaisesRegex(ValueError, 'além da frase'):
            P.check_manual_revision(self.manual + '\n')

    def test_plano_padrao_nao_toca_cli(self):
        a, b = self.targets[0][0], self.targets[1][0]
        a.write_text(self.manual); b.write_text(self.manual)
        with patch.object(P, 'PUBLIC', a), patch.object(P, 'MIRROR', b):
            entries = P.plan(self.bundle, T)
        self.assertEqual([e['target'] for e in entries], [str(a), str(b)])
        self.assertTrue(all(e['source'] == str(self.bundle / 'manual.html') for e in entries))

    def test_logica_modificada_recusada(self):
        with self.assertRaisesRegex(ValueError, 'lógica'):
            P.text_checks(self.manual, self.cli + '\nerro("alterado")', self.old_cli)

    def test_avisos_antigos_recusados(self):
        for phrase in P.STALE:
            with self.subTest(phrase=phrase), self.assertRaises(ValueError):
                P.text_checks(self.manual + phrase, self.cli, self.old_cli)

    def test_deriva_preservada(self):
        self.targets[1][0].write_text('edição alheia')
        with self.assertRaisesRegex(ValueError, 'alterado desde'):
            P.plan(self.bundle, T, self.targets)
        self.assertEqual(self.targets[0][0].read_text(), 'anterior-0')

    def test_link_recusado(self):
        target = self.targets[0][0]
        target.rename(self.root / 'backup-alvo')
        target.symlink_to(self.root / 'backup-alvo')
        with self.assertRaisesRegex(ValueError, 'link simbólico'):
            P.plan(self.bundle, T, self.targets)

    def test_instalacao_idempotencia_e_restauracao(self):
        entries = P.plan(self.bundle, T, self.targets)
        plan = self.root / 'plan.json'; plan.write_text(json.dumps(entries))
        backup = self.root / 'backup'
        T.install(plan, backup)
        again = P.plan(self.bundle, T, self.targets)
        self.assertTrue(all(e['before'] == e['sha256'] for e in again))
        for target, _, _ in self.targets:
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)
        T.rollback(backup)
        for i, (target, _, digest) in enumerate(self.targets):
            self.assertEqual(P.digest(target), digest)
            self.assertEqual(target.read_text(), 'anterior-' + str(i))

    def test_falha_parcial_restaura(self):
        entries = P.plan(self.bundle, T, self.targets)
        plan = self.root / 'plan.json'; plan.write_text(json.dumps(entries))
        backup = self.root / 'backup'
        copy = T.atomic_copy
        def fail_second(src, dst, *args):
            if dst == entries[1]['target']:
                raise OSError('falha simulada de escrita')
            return copy(src, dst, *args)
        with patch.object(T, 'atomic_copy', side_effect=fail_second), self.assertRaises(OSError):
            T.install(plan, backup)
        T.rollback(backup)
        for target, _, digest in self.targets:
            self.assertEqual(P.digest(target), digest)

    def test_edicao_concorrente_recusada_antes_de_escrever(self):
        entries = P.plan(self.bundle, T, self.targets)
        plan = self.root / 'plan.json'; plan.write_text(json.dumps(entries))
        self.targets[2][0].write_text('outro trabalho')
        with self.assertRaisesRegex(ValueError, 'mudou após'):
            T.install(plan, self.root / 'backup')
        self.assertEqual(self.targets[0][0].read_text(), 'anterior-0')
        self.assertFalse((self.root / 'backup').exists())


if __name__ == '__main__':
    import sys
    sys.dont_write_bytecode = True
    unittest.main(verbosity=2)
