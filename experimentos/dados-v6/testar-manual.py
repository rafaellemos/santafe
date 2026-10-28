#!/usr/bin/env python3
import html, importlib.util, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'docs/validar-manual.py'
spec=importlib.util.spec_from_file_location('manual',p); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
text=(ROOT/'docs/manual.html').read_text(); c=m.Coletor();c.feed(text)
for forbidden in ('numa tabela Santafé remove aquela chave','Números JSON viram sempre','Tabelas sequenciais viram matrizes','local página = --[[html]] [[',
                  'Cada linha vem como uma tabela sequencial de colares', '<code>--[[js]]</code> não é uma anotação reconhecida'):
    assert forbidden not in text,forbidden
for name,code in c.codigos.items():
    if name.startswith('code-dados6-') or name=='code-json-null' or name in {'code-fn-'+str(i) for i in range(102,110)}:
        p=subprocess.run([str(ROOT/'src/santafé'),'-E','-P','-e',html.unescape(code)],capture_output=True,text=True,cwd=ROOT,timeout=10)
        assert p.returncode==0,(name,p.stderr)
        print(name,p.stdout.strip())
subprocess.run(['python3',str(ROOT/'docs/validar-manual.py'),'--fonte',str(ROOT),'--compilador',str(ROOT/'src/santafec')],check=True)
