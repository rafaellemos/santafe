#!/usr/bin/env python3
"""Clona kit para staging; adapta SOMENTE namespace e acrescenta harness.

Não modifica o kit selado nem instala no perfil. A cópia posterior deve ser
feita só para Packages/SantafeDados9Host<id>, sem sobrepor pastas existentes.
"""
import argparse, hashlib, json, shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('laboratorio',type=Path);p.add_argument('--kit',type=Path);args=p.parse_args()
root=Path(__file__).resolve().parents[3];lab=args.laboratorio.resolve()
assert lab.name.startswith('santafe-dados8-host-') and lab.is_dir()
name='SantafeDados9Host'+lab.name.split('-')[-1]
out=lab/name;out.mkdir()
kit=args.kit.resolve() if args.kit else root/'dist/candidato-dados-v9/editores/SantafeDados'
scope='source.santafe-dados9-host-'+lab.name.split('-')[-1]
hashes={}
for rel in ['Realce.py','realce_embutido.py','Santafe-Dados.sublime-syntax','ONFE.tmLanguage','paletas.json','.python-version','SantafeDados.sublime-settings']:
    src=kit/rel;hashes[rel]=hashlib.sha256(src.read_bytes()).hexdigest()
    text=src.read_text().replace('source.santafe-dados',scope)
    if rel=='Realce.py':
        text=text.replace('SantafeDadosRealceListener',name+'RealceListener').replace('SantafeDadosPaletaEmbutidaCommand',name+'PaletaEmbutidaCommand')
        text=text.replace('santafe_dados_realce_',name.lower()+'_realce_').replace('santafe_dados_realce_virtual',name.lower()+'_virtual')
        text=text.replace('SantafeDados.sublime-settings',name+'.sublime-settings')
    (out/(name+'.sublime-settings' if rel=='SantafeDados.sublime-settings' else rel)).write_text(text)
scheme=json.loads((kit/'ColorSchemes/Monokai.sublime-color-scheme').read_text().replace('source.santafe-dados',scope))
scheme['extends']='Packages/Color Scheme - Default/Monokai.sublime-color-scheme'
(out/'Dados9Host.sublime-color-scheme').write_text(json.dumps(scheme,ensure_ascii=False,indent=2))
(out/'laboratorio.json').write_text(json.dumps({'diretorio':str(lab),'scope':scope,'hashes':hashes},ensure_ascii=False,indent=2))
shutil.copyfile(Path(__file__).parent/'SublimeHost.py',out/'SublimeHost.py')
(lab/'dados9.sublime-project').write_text(json.dumps({'folders':[{'path':str(lab)}],'settings':{'font_size':15}},indent=2))
print(out)
