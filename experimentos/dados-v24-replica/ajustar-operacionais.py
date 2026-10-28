#!/usr/bin/env python3
"""Ajustes semânticos restritos à captura auditada; saída privada, sem instalação."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

EXPECTED = {
    'opt/sfdev.fé': '27eb5bbd815b2855f192e7193ddbfa7dde0dff38d87b841a43e4f069bc25f03f',
    'opt/paodocafe/paodocafe.fé': 'b049e79cf23f93766eae6cd44b6e4c0ccf041a2ffdf2635dc8f8641e78a5bb30',
    'opt/santafe-nomes/autoridade.fé': '2b1c84e9dbf8d0f4b16b1b3cdc228d9222e17ea561d3357088faa29f4fe8e5f9',
    'opt/santafe-dns/autoritativo.fé': 'b2a1cc0d7964f395b45c1423a6b7adf29385959cc5f3d9411938123e12bb99b8',
}


def adjust(name, text):
    changes = []
    replacements = []
    if name == 'opt/sfdev.fé':
        replacements = [
            ('    piscina = nulo,\n    falhaDoBanco = nulo,\n    resumoIsca = nulo,\n', '',
             'campos inicialmente ausentes continuam ausentes'),
            ('comunidade.limites[chaveAntiga] = nulo', 'tabela.apague(comunidade.limites, chaveAntiga)',
             'limite expirado remove a chave'),
            ('comunidade.falhaDoBanco = nulo', 'tabela.apague(comunidade, "falhaDoBanco")',
             'limpeza da falha remove o campo'),
        ]
    elif name == 'opt/paodocafe/paodocafe.fé':
        replacements = [('se estado.pronto então estado.falha = nulo fim',
                         'se estado.pronto então tabela.apague(estado, "falha") fim',
                         'prontidão remove a falha; não inclui falha:null')]
    else:
        assert text.count('chavePrivada = nulo') == 1
        changes.append('atribuição à variável preservada; libera a referência, não remove campo de tabela')
    for old, new, reason in replacements:
        if text.count(old) != 1:
            raise ValueError('Trecho mudou; exige nova revisão: ' + name)
        text = text.replace(old, new)
        changes.append(reason)
    return text, changes


def main(audit, candidate):
    audit = audit.absolute()
    assert audit == audit.resolve() and audit.parent == Path('/var/tmp')
    assert audit.name.startswith('santafe-auditoria23-')
    assert audit.stat().st_uid == os.getuid() and not audit.stat().st_mode & 0o077
    os.umask(0o077)
    output = Path(tempfile.mkdtemp(prefix='santafe-ajustes23-', dir='/var/tmp'))
    results = []
    for name, digest in EXPECTED.items():
        source = audit/'convertidos'/name
        data = source.read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, 'Origem mudou: ' + name
        text, reasons = adjust(name, data.decode())
        target = output/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        p = subprocess.run([str(candidate/'src/santafec'), '-p', str(target)], capture_output=True, timeout=30)
        assert p.returncode == 0, 'Ajuste não compila: ' + name
        results.append({'arquivo': name, 'antes': digest,
                        'depois': hashlib.sha256(target.read_bytes()).hexdigest(), 'revisao': reasons})
    report = {'resultado': 'AJUSTES_PREPARADOS_E_COMPILADOS', 'arquivos': results,
              'aplicativos_executados': False, 'producao_alterada': False,
              'limite': 'Aplicar junto das demais adaptações operacionais e ensaiar a réplica completa antes de publicar.'}
    (output/'resultado.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print('AJUSTES23_PRIVADOS', output)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('auditoria', type=Path)
    p.add_argument('candidato', type=Path)
    args = p.parse_args()
    main(args.auditoria, args.candidato.resolve())
