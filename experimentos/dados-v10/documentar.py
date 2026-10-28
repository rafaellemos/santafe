from pathlib import Path
import sys
s=Path(sys.argv[1]);assert (s/'.laboratorio-dados10').is_file()
p=s/'docs/CONTRATO-DADOS-ONFE.md';t=p.read_text()
a='O candidato `dados.9` incorpora a correção visual do VS Code sobre `dados.8`, sem alterar seu contrato de delimitadores,'
b='O candidato `dados.10` define a IBA 3 e prepara a migração operacional sobre a base selada dados.9, sem alterar o contrato de delimitadores,'
assert a in t;t=t.replace(a,b)
a='a ABI C provisória ainda os representa como `LUA_TTABLE`, oferecendo `lua_islist` e `lua_createlist`. Esse layout não é compatível com módulos C instalados. O construtor isolado não habilita carregamento dinâmico de módulos.'
b='a IBA 3 ainda os representa como `LUA_TTABLE`, oferecendo `lua_islist` e `lua_createlist`. O carregador dinâmico exige o descritor `SANTAFE_MODULE_ABI` dos módulos recompilados. Não aceita bibliotecas instaladas de outra IBA. O contrato e os limites estão em `experimentos/dados-v10/IBA.md`.'
assert a in t;p.write_text(t.replace(a,b))
p=s/'docs/manual.html';t=p.read_text()
a='Recompile bibliotecas C para a ABI candidata e não reutilize bytecode antigo. Os gates da ABI definitiva e plataformas não ensaiadas permanecem abertos.'
b='Recompile bibliotecas C para a IBA 3 (Interface Binária de Aplicação), com os cabeçalhos candidatos e a declaração SANTAFE_MODULE_ABI em uma unidade de tradução. O SDK instalado fornece a definição SANTAFE_DADOS_EXPERIMENTAL por pkg-config. O carregador confere a identidade santafe-3 antes de chamar o inicializador, mesmo se a biblioteca não usar luaL_checkversion. Isso não isola código nativo: construtores podem executar durante a carga. Bytecode usa assinatura ESC SF3 e formato 0x30; versões anteriores são recusadas. Distribua fontes e não carregue bytecode ou bibliotecas de origem não confiável. A réplica operacional completa e plataformas não ensaiadas continuam sendo critérios de promoção.'
assert a in t;p.write_text(t.replace(a,b))
