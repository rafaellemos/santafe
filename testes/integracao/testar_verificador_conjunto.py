#!/usr/bin/env python3
"""Testa o gate real sem promover revisões independentes a um conjunto homologado.

As fixtures contêm somente metadados; não são distribuições nem evidência de
homologação de um novo conjunto. O verificador operacional continua inalterado.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
EDITORS = (('vscode', 'package.json'), ('sublime', 'package-metadata.json'))


class GateConjunto(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='santafe-gate-conjunto-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in ('operação/verificar-conjunto.py', 'operação/conjunto-versoes.json',
                         'src/lua.h', 'Makefile', 'ferramentas/sls/sls.fé',
                         'docs/HOMOLOGACAO-CONJUNTA.json'):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        proof = json.loads((self.root / 'docs/HOMOLOGACAO-CONJUNTA.json').read_text())
        # Fixture coerente com as evidências históricas, não promoção do fonte
        # atual. O teste do checkout real abaixo exige a recusa dessa promoção.
        self.versions = {'formato': 1, 'estado': 'homologado', 'gates_pendentes': [],
                         **{key: proof[key] for key in ('nucleo', 'sls', 'bibliotecas', 'vscode', 'sublime')}}
        self.write('operação/conjunto-versoes.json', self.versions)
        for name, manifest in EDITORS:
            # Metadado de teste, não um pacote novo disfarçado de versão antiga.
            self.write('extensões/' + name + '/' + manifest, {'version': self.versions[name]})

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def run_gate(self, preflight=False, root=None):
        command = [sys.executable, str((root or self.root) / 'operação/verificar-conjunto.py')]
        if preflight:
            command.append('--preflight')
        return subprocess.run(command, capture_output=True, text=True, timeout=15)

    def assert_rejected(self, message, preflight=False):
        result = self.run_gate(preflight)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(message, result.stderr)

    def test_metadados_historicos_coerentes(self):
        for preflight in (False, True):
            result = self.run_gate(preflight)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_editor_divergente_recusado_em_ambos_os_modos(self):
        for name, manifest in EDITORS:
            relative = 'extensões/' + name + '/' + manifest
            self.write(relative, {'version': '99.99.99'})
            for preflight in (False, True):
                self.assert_rejected(name + ' divergente', preflight)
            self.write(relative, {'version': self.versions[name]})

    def test_versoes_nucleo_e_sls_continuam_obrigatorias(self):
        for name, message in (('nucleo', 'não corresponde'), ('sls', 'SLS ainda não promovido')):
            changed = dict(self.versions, **{name: '99.99.99'})
            self.write('operação/conjunto-versoes.json', changed)
            self.assert_rejected(message, True)
            self.write('operação/conjunto-versoes.json', self.versions)

    def test_evidencia_de_outra_versao_recusada(self):
        proof = json.loads((self.root / 'docs/HOMOLOGACAO-CONJUNTA.json').read_text())
        proof['vscode'] = '99.99.99'
        self.write('docs/HOMOLOGACAO-CONJUNTA.json', proof)
        self.assert_rejected('evidências de outras versões')

    def test_evidencia_ausente_recusada(self):
        (self.root / 'docs/HOMOLOGACAO-CONJUNTA.json').unlink()
        self.assert_rejected('registro de evidências finais ausente')

    def test_gate_nao_executado_nao_e_aprovacao(self):
        proof = json.loads((self.root / 'docs/HOMOLOGACAO-CONJUNTA.json').read_text())
        for gate in ('macos', 'debian', 'wasm', 'vscode_host', 'sublime_host',
                     'visual', 'publicador', 'distribuicao'):
            changed = dict(proof)
            changed[gate] = {'resultado': 'pendente', 'evidencia': 'não executado'}
            self.write('docs/HOMOLOGACAO-CONJUNTA.json', changed)
            self.assert_rejected('evidência não comprovada: ' + gate)

    def test_preflight_nao_promove_candidato(self):
        changed = dict(self.versions, estado='candidato', gates_pendentes=['teste não executado'])
        self.write('operação/conjunto-versoes.json', changed)
        self.assert_rejected('homologação pendente')
        result = self.run_gate(True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'operação/conjunto-versoes.json').read_text()), changed)

    def test_checkout_real_nao_revalida_automaticamente_novos_editores(self):
        current = json.loads((ROOT / 'operação/conjunto-versoes.json').read_text())
        for name, manifest in EDITORS:
            actual = json.loads((ROOT / 'extensões' / name / manifest).read_text())['version']
            self.assertEqual(actual, current[name])
        result = self.run_gate(True, ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        if any(current[key] != self.versions[key] for key in ('nucleo', 'sls', 'bibliotecas', 'vscode', 'sublime')):
            self.assertNotEqual(current['estado'], 'homologado')
            self.assertTrue(current['gates_pendentes'])
            result = self.run_gate(False, ROOT)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('homologação pendente', result.stderr)
            self.assertIn('evidências de outras versões', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
