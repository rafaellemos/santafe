#!/usr/bin/env python3
"""Revisão textual 2.1.0-r2: somente manual e espelho, com rollback.

Executado pelo lançador que confere os hashes e copia a entrega para diretório
privado. Não modifica downloads, snapshots, serviços, bancos ou catálogos.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import urllib.request

SNAPSHOT = Path('/home/rafael/santafe-fonte/versoes/2.1.0')
PREFIX = Path('/usr/local')
TOOLS = Path('share/santafé/1.0/ferramentas/pacotes')
PUBLIC = Path('/var/www/santafé.dev.br/estático/manual/index.html')
MIRROR = Path('/home/rafael/santafe-fonte/site-sfdev/manual.html')
CLI = PREFIX / TOOLS / 'cli.fé'
REVISION = '2.1.0-textos-r2'
BEFORE_MANUAL = '42f164c505026a16198bfaebc7389a6bd71b24dafb2030b8cfa5309d86078a04'
BEFORE_CLI = '8fcc899c0d72a312b554f2b689fb5021e3db3d4007a59106801c4a5ae4824965'
CATALOG = 'https://xn--santaf-gva.dev.br/est%C3%A1tico/bibliotecas/v1/'
URL = 'https://xn--santaf-gva.dev.br/est%C3%A1tico/manual/'
STALE = ('Correção em desenvolvimento, ainda não publicada',
         'O candidato SLS 1.0.0', 'extensões candidatas',
         'Recursos do candidato:', 'Gerenciador e catálogo candidatos',
         'núcleo estável 2.0.3', 'API em desenvolvimento, ainda não publicada',
         'VS Code 1.0.6 e Sublime 1.0.13',
         'O repositório público ainda não foi publicado.',
         'API nova, ainda em desenvolvimento.')


def check_manual_revision(manual):
    """Prova que a revisão muda apenas a frase de depure.analise."""
    new = 'Disponível desde a Santafé 2.1.0. O diagnóstico contém'
    old = 'API nova, ainda em desenvolvimento. O diagnóstico contém'
    if manual.count(new) != 1:
        raise ValueError('Nota de depure.analise ausente ou duplicada')
    prior = manual.replace(new, old)
    if hashlib.sha256(prior.encode('utf-8')).hexdigest() != BEFORE_MANUAL:
        raise ValueError('Revisão contém alterações além da frase de depure.analise')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment():
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('LUA_', 'SANTAFE_', 'PYTHON'))}
    env.update(GSETTINGS_BACKEND='memory', PYTHONDONTWRITEBYTECODE='1')
    return env


def run(args, cwd='/tmp', capture=False):
    return subprocess.run(list(map(str, args)), cwd=cwd, env=environment(),
                          check=True, timeout=180, text=True,
                          stdout=subprocess.PIPE if capture else None)


def text_checks(manual, cli, old_cli):
    for text in (manual, cli):
        for phrase in STALE:
            if phrase in text:
                raise ValueError('Aviso antigo presente: ' + phrase)
    for phrase in ('SLS 1.0.0 foi homologado e publicado',
                   'gerenciador de bibliotecas 1.0.0',
                   'VS Code 1.1.0 e Sublime 1.1.0', 'semver 1.0.0',
                   '/estático/wasm/2.1.0/'):
        if phrase not in manual:
            raise ValueError('Texto esperado ausente: ' + phrase)
    if CATALOG not in cli or 'Santafé Bibliotecas 1.0.0' not in cli:
        raise ValueError('Ajuda sem versão/catálogo correto')
    pattern = r'mostre\(\[\[Santafé Bibliotecas.*?\]\]\)'
    if len(re.findall(pattern, cli, re.S)) != 1 or len(re.findall(pattern, old_cli, re.S)) != 1:
        raise ValueError('Bloco de ajuda inesperado')
    if re.sub(pattern, '<AJUDA>', cli, flags=re.S) != re.sub(pattern, '<AJUDA>', old_cli, flags=re.S):
        raise ValueError('A revisão não pode modificar a lógica do gerenciador')


def plan(bundle, transaction, targets=None):
    # A lista de destinos não vem do manifesto recebido. targets só é usado
    # pelo teste unitário; a interface de publicação não aceita essa opção.
    entries = []
    targets = targets or ((PUBLIC, 'manual.html', BEFORE_MANUAL),
                          (MIRROR, 'manual.html', BEFORE_MANUAL))
    for target, filename, expected in targets:
        transaction.safe_destination(target)
        if not target.is_file():
            raise ValueError('Destino ausente: ' + str(target))
        before, after = digest(target), digest(bundle / filename)
        if before not in (expected, after):
            raise ValueError('Destino alterado desde a auditoria; preservado: ' + str(target))
        info = target.stat()
        import pwd, grp
        entries.append(dict(source=str(bundle / filename), target=str(target),
                            sha256=after, before=before, mode=stat.S_IMODE(info.st_mode),
                            owner=pwd.getpwuid(info.st_uid).pw_name + ':' + grp.getgrgid(info.st_gid).gr_name,
                            old_mode=stat.S_IMODE(info.st_mode), old_uid=info.st_uid, old_gid=info.st_gid))
    return entries


def preflight(bundle, work):
    print('==> Validando a correção pontual, exemplos e contratos sem alterar produção', flush=True)
    version = run([PREFIX / 'bin/santafé', '-E', '-P', '-v'], capture=True).stdout
    if 'Santafé 2.1.0 ' not in version:
        raise ValueError('Esta revisão exige núcleo 2.1.0 instalado')
    old_cli = (SNAPSHOT / 'ferramentas/pacotes/cli.fé').read_text()
    manual = (bundle / 'manual.html').read_text()
    check_manual_revision(manual)
    text_checks(manual, (bundle / 'cli.fé').read_text(), old_cli)
    validator = load(SNAPSHOT / 'docs/validar-manual.py', 'manual_textos')
    old, new = validator.Coletor(), validator.Coletor()
    old.feed((SNAPSHOT / 'docs/manual.html').read_text())
    new.feed((bundle / 'manual.html').read_text())
    if old.codigos != new.codigos or old.ids != new.ids:
        raise ValueError('A revisão textual alterou exemplos ou IDs')
    run(['python3', SNAPSHOT / 'docs/validar-manual.py', bundle / 'manual.html',
         '--fonte', SNAPSHOT, '--compilador', PREFIX / 'bin/santafec'])
    run([PREFIX / 'bin/santafec', '-p', bundle / 'cli.fé'])
    # Copia o núcleo existente, sem instalar ou compilar; só o CLI recebe a
    # revisão. Não reutiliza um symlink que pudesse apontar para produção.
    isolated = work / 'prefixo isolado'
    (isolated / 'bin').mkdir(parents=True)
    shutil.copy2(PREFIX / 'bin/santafé', isolated / 'bin/santafé')
    shutil.copytree(PREFIX / TOOLS, isolated / TOOLS)
    shutil.copyfile(bundle / 'cli.fé', isolated / TOOLS / 'cli.fé')
    for command in ('instale', 'empacote', 'catalogo'):
        help_text = run([isolated / 'bin/santafé', command, '--ajuda'], capture=True).stdout
        if CATALOG not in help_text or 'ainda não foi publicado' in help_text:
            raise ValueError('Ajuda incorreta: ' + command)
    run(['python3', SNAPSHOT / 'testes/integracao/testar_pacotes_cli.py',
         '--binario', isolated / 'bin/santafé'])
    print('TEXTOS_2_1_0_R2_PREFLIGHT_OK', flush=True)


def check_public(expected):
    # Confere a URL normal e a URL sem cache; não confunde conteúdo em cache
    # de ferramenta de busca com a resposta HTTPS do portal.
    for suffix in ('', '?revisao=' + REVISION + '-' + expected[:12]):
        req = urllib.request.Request(URL + suffix, headers={'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read(4 * 1024 * 1024)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Manual HTTPS não corresponde ao instalado')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('publicar', '--preflight'), nargs='?', default='publicar')
    # Aceita --preflight como opção sem depender de posições do argparse.
    parser.add_argument('--preflight', dest='preflight', action='store_true')
    args = parser.parse_args()
    preview = args.preflight or args.mode == '--preflight'
    if not preview and os.geteuid() != 0:
        raise SystemExit('Use sudo bash para publicar; --preflight não exige sudo.')
    sys_path = Path(__file__).resolve().parent
    transaction = load(sys_path / 'transacao.py', 'transacao_textos')
    lock = None
    if not preview:
        lock = open('/run/lock/santafe-conjunto.lock', 'a')
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    with tempfile.TemporaryDirectory(prefix='santafe-textos-ensaio-') as directory:
        work = Path(directory)
        entries = plan(sys_path, transaction)
        preflight(sys_path, work)
        if preview:
            print('Nenhum arquivo operacional foi trocado; nenhum serviço reiniciado.')
            return
        plan_file = work / 'plan.json'
        plan_file.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n')
        if all(e['before'] == e['sha256'] for e in entries):
            transaction.verify(plan_file)
            check_public(entries[0]['sha256'])
            print('Revisão textual já instalada e validada; nenhuma troca necessária.')
            return
        backup = Path(tempfile.mkdtemp(prefix='santafe-textos-2.1.0-r2-', dir='/var/backups')) / 'transacao'
        print('Cópia reversível: ' + str(backup), flush=True)
        def interrupted(signum, frame):
            raise KeyboardInterrupt('Publicação interrompida')
        signal.signal(signal.SIGTERM, interrupted)
        try:
            transaction.install(plan_file, backup)
            # Guarda a revisão exata junto do backup, sem editar o snapshot
            # imutável ou rotular um novo release de núcleo.
            for name in ('manual.html', 'cli.fé', 'manifesto.json', 'transacao.py'):
                shutil.copy2(sys_path / name, backup / ('novo-' + name))
            for command in ('instale', 'empacote', 'catalogo'):
                if CATALOG not in run([PREFIX / 'bin/santafé', command, '--ajuda'], capture=True).stdout:
                    raise ValueError('Ajuda instalada divergente')
            transaction.verify(plan_file)
            check_public(entries[0]['sha256'])
        except BaseException:
            # A restauração usa os arquivos anteriores e metadados gravados
            # antes da primeira troca. Falhas de rollback não são ocultadas.
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            if (backup / 'touched.json').exists():
                transaction.rollback(backup)
            raise
        print('Manual corrigido e validado: ' + REVISION + '.')
        print('Ajuda do gerenciador preservada; apenas manual e espelho foram trocados.')
        print('Downloads e snapshots imutáveis preservados. Nenhum serviço reiniciado.')
        print('Cópia de segurança: ' + str(backup))


if __name__ == '__main__':
    import sys
    sys.dont_write_bytecode = True
    main()
