#!/usr/bin/env python3
from pathlib import Path
import shutil, json
ROOT=Path(__file__).resolve().parents[2]
assert (ROOT/'.laboratorio-dados7').is_file()
for name in ('atomico.h','atomico-lua.h'):
    shutil.copy2(ROOT/'experimentos/dados-v7'/name,ROOT/'bibs/bibc/arquivo'/name)
p=ROOT/'bibs/bibc/arquivo/arquivo.c'; t=p.read_text(); anchor='static const luaL_Reg arquivo_funções[] = {'
assert t.count(anchor)==1
t=t.replace('#define _POSIX_C_SOURCE 200809L','#define _POSIX_C_SOURCE 200809L\n#ifdef __APPLE__\n#define _DARWIN_C_SOURCE 1\n#endif')
t=t.replace(anchor,'#include "atomico-lua.h"\n\n'+anchor+'\n    {"graveAtômico", l_at_grave},\n    {"graveAtômicoAssíncrono", l_at_grave_async},')
p.write_text(t)
p=ROOT/'experimentos/dados-v5/testar-instalacao.py'; t=p.read_text()
anchor="    run([str(binary),'-E','-P','-e',bootstrap,'-e',code],cwd=lab)"
assert t.count(anchor)==1
t=t.replace(anchor,'    code+=\'; local O=importe "onfé"; local ok,f,s=O.grave("persistencia-instalada.onfé",{v=nulo,itens=[]}); garanta(ok e s=="durável"); local v=O.carregue("persistencia-instalada.onfé"); garanta(tabela.temChave(v,"v") e tipo(v.itens)=="lista")\'\n'+anchor)
anchor="    assert not (prefix/'share/santafé/1.0/ferramentas/sls/onfé.fé').exists()"
assert t.count(anchor)==1
t=t.replace(anchor,anchor+"\n    assert not (prefix/'share/santafé/1.0/bibf/onfé.fé').exists()")
p.write_text(t)
p=ROOT/'bibs/bibc/arquivo/Makefile'; t=p.read_text().replace('arquivo.o: arquivo.c','arquivo.o: arquivo.c atomico.h atomico-lua.h'); p.write_text(t)
original=(ROOT/'experimentos/dados-v1/onfé.fé').read_text()
assert original.endswith('retorne O\n')
t=original[:-len('retorne O\n')]+(ROOT/'experimentos/dados-v7/persistencia.fé').read_text()+'\nretorne O\n'
for name in ('experimentos/dados-v1/onfé.fé','ferramentas/sls/onfé.fé','bibs/bibf/onfé.fé'):
    (ROOT/name).write_text(t)
p=ROOT/'docs/CONTRATO-DADOS-ONFE.md'
p.write_text(p.read_text()+'\n\n## Decisão dados.7\n\nListas sem metatabelas são o contrato desta versão, não uma promessa pendente.\nObjetos com comportamento continuam sendo tabelas; podem conter listas.\nPersistência: veja experimentos/dados-v7/PERSISTENCIA.md.\n')
for name in ('experimentos/dados-v6/testar-operacao.py','experimentos/dados-v6/operacao.py'):
    p=ROOT/name; p.write_text(p.read_text().replace('dados.6','dados.7'))
p=ROOT/'docs/manual.html'; t=p.read_text().replace('candidato dados.6','candidato dados.7').replace('Candidato dados.6','Candidato dados.7').replace('candidato-dados.6/','candidato-dados.7/')
t=t.replace('Listas ainda não admitem metatabelas.','Listas não admitem metatabelas nesta versão, por decisão de contrato. Objetos com comportamento podem ser tabelas que contêm listas.')
t=t.replace('O módulo do candidato fica junto ao SLS; ainda não é um pacote publicado.','O módulo do candidato também é instalado em bibf e carregado por importe "onfé"; ainda não é uma versão publicada.')
old='A API de persistência ONFÉ ainda precisa de homologação específica. Não prometa gravação atômica usando um arquivo aberto diretamente para escrita.'
assert old in t
t=t.replace(old,'A persistência candidata usa onfé.grave e onfé.graveAssíncrono, descritas abaixo. Não prometa gravação atômica usando um arquivo aberto diretamente para escrita.')
block=(ROOT/'experimentos/dados-v7/manual.html').read_text()
anchor='<h4>Migração operacional</h4>'; assert t.count(anchor)==1
p.write_text(t.replace(anchor,block+'\n'+anchor))
p=ROOT/'ferramentas/sls/api-publica.json'; api=json.loads(p.read_text())
items=[('onfé.grave','caminho, dado','Grava ONFÉ por substituição atômica; retorna ok, falha, estado. Síncrono.'),
       ('onfé.graveAssíncrono','caminho, dado, tratador [, contexto]','Agenda E/S. Tratador recebe ok, falha, estado, contexto; estados inalterado/publicado/durável.'),
       ('onfé.cod','dado','Serializa dados sem executá-los; limita a 4 MiB.'),
       ('onfé.decod','texto','Decodifica dados ONFÉ sem executar programas.'),
       ('onfé.carregue','caminho','Lê e decodifica um arquivo ONFÉ sob controle da aplicação.'),
       ('onfé.paraJSON','dado','Converte dados para JSON comum; recusa chaves não textuais.'),
       ('onfé.deJSON','texto','Decodifica JSON preservando listas e nulos.'),
       ('arquivo.graveAtômico','caminho, conteúdo','Grava bytes por substituição atômica; retorna ok, falha, estado.'),
       ('arquivo.graveAtômicoAssíncrono','caminho, conteúdo, tratador [, contexto]','Grava bytes sem bloquear o laço; tratador recebe ok, falha, estado, contexto.')]
for label,args,doc in items:
    assert not any(i['rótulo']==label for i in api['itens'])
    api['itens'].append({'rótulo':label,'assinatura':label+'('+args+')','documentação':doc,'categoria':'Dados / persistência',
        'origem':'bibs/bibf/onfé.fé' if label.startswith('onfé.') else 'bibs/bibc/arquivo/arquivo.c'})
api['itens'].sort(key=lambda x:x['rótulo'])
p.write_text(json.dumps(api,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'docs/API-PUBLICA-FE.tsv'
p.write_text(p.read_text()+''.join(label+'|bibs/bibf/onfé.fé\n' for label,_,_ in items if label.startswith('onfé.')))
p=ROOT/'experimentos/dados-v3/testar-wasm.js'; t=p.read_text(); anchor='const deadline=setTimeout'
assert anchor in t
t=t.replace(anchor,'cases.push(\'local O=executeArquivo("/onfé.fé"); local ok,f=proteja(O.grave,"/nao-gravar.onfé",{}); garanta(não ok e f:procure("indisponível",1,verdadeiro)); garanta(es.abra("/nao-gravar.onfé","rb")==nulo)\');\n'+anchor)
p.write_text(t)
