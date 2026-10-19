"""Executar com runpy.run_path no console do Sublime real.

O plugin_host usa -O; recompilar cada ensaio com optimize=0 é obrigatório
para manter as asserções. Não muda preferências nem arquivos do usuário.
"""
import os
from pathlib import Path
import tempfile
import sublime

RAIZ = Path(__file__).resolve().parent
SAIDA = Path(os.environ.get('SANTAFE_TESTE_SAIDA') or tempfile.mkdtemp(prefix='santafe-sublime-testes-'))
SAIDA.mkdir(parents=True, exist_ok=True)
for chave, nome in (('REALCE', 'regressao'), ('CONCAT', 'concatenacoes'), ('API', 'api')):
    os.environ['SANTAFE_TESTE_' + chave + '_SAIDA'] = str(SAIDA / ('sublime-' + nome + '.json'))


def execute(nome):
    caminho = RAIZ / nome
    exec(compile(caminho.read_text(), str(caminho), 'exec', optimize=0),
         {'__file__': str(caminho), '__name__': '__test__'})


print('Santafé: relatórios nativos em', str(SAIDA))
execute('verificar_realce.py')
sublime.set_timeout(lambda: execute('verificar_concatenacoes.py'), 1600)
sublime.set_timeout(lambda: execute('verificar_api_paletas.py'), 4500)
