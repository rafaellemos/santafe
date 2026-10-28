#!/usr/bin/env python3
"""Resumo verificável do erro sintético, sem exportar a mensagem HTML."""
from pathlib import Path
import argparse,hashlib,html,json,re
p=argparse.ArgumentParser()
p.add_argument('laboratorio',type=Path)
p.add_argument('log',type=Path)
p.add_argument('destino',type=Path)
a=p.parse_args()
lab=a.laboratorio.resolve()
assert lab.parent==Path('/tmp') and lab.name.startswith('santafe-apps5-')
bodies=list(lab.glob('http-falha-*.html'))
assert bodies and "('HTTP carga', 503," in a.log.read_text()
rows=[]
for f in bodies:
 raw=f.read_bytes();text=html.unescape(raw.decode('utf-8'))
 assert re.search(r"Error on delete of '/tmp/#sql-temptable-[^']+\.MAI' \(Errcode: 2",text)
 rows.append({'sha256':hashlib.sha256(raw).hexdigest(),'octetos':len(raw),
              'http':503,'errno':2,'tipo_arquivo':'temporário SQL MAI',
              'diretorio_compartilhado':'/tmp','conteudo_html_exportado':False})
out={'resultado':'REPRODUZIDO','sintetico':True,'capturas':rows,
     'ocorrencia_original_dados10_confirmada':False,
     'limite':'A captura dados.10 não guardou o erro. Esta evidência é da reprodução dados.12.',
     'fontes':['https://raw.githubusercontent.com/MariaDB/server/10.11/sql/sql_base.cc',
               'https://raw.githubusercontent.com/MariaDB/server/10.11/sql/mysqld.cc']}
a.destino.parent.mkdir(parents=True,exist_ok=True)
a.destino.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('DIAGNOSTICO503_EXPORTADO',len(rows),'captura(s); HTML permanece no laboratório')
