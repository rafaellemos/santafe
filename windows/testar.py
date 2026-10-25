#!/usr/bin/env python3
"""Bateria inicial em Windows nativo. Nunca equivale a homologação completa."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('fonte',type=Path)
    parser.add_argument('trabalho',type=Path)
    args = parser.parse_args()
    if sys.platform != 'win32':
        raise SystemExit('Esta bateria exige Python Windows nativo; macOS, WSL e MSYS Python não contam.')
    sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace')
    root=args.fonte.resolve(); work=args.trabalho.resolve()
    if not (root/'PREPARACAO-WINDOWS.json').is_file() or work.exists():
        raise SystemExit('Exige preparação validada e trabalho novo')
    work.mkdir(parents=True)
    result={'plataforma':platform.platform(),'python':sys.version,'candidato':'dados.16',
            'testes':[], 'resultado':'em_execucao', 'suporte_windows_completo':False,
            'pendencias':['SLS e gerenciador: consultar bateria complementar ferramentas/resultado.json',
                         'Bibliotecas C: DLL/IBA dinâmica e dependências',
                         'Instalação, atualização e reversão nativas',
                         'Persistência atômica ONFÉ em NTFS',
                         'Integração visual dos editores no Windows']}
    def save():
        (work/'resultado.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def run(name,cmd,cwd,stdin=None,expected=0,timeout=90):
        start=time.monotonic()
        proc=subprocess.run([str(v) for v in cmd],cwd=cwd,input=stdin,
                            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        log=proc.stdout[:8*1024*1024]
        (work/(name+'.log')).write_bytes(log)
        if len(proc.stdout)>len(log):raise RuntimeError('saída excedeu limite: '+name)
        passed=proc.returncode==expected if expected is not None else proc.returncode==1
        result['testes'].append({'nome':name,'codigo':proc.returncode,'passou':passed,
                                'segundos':round(time.monotonic()-start,3)})
        print(('PASSOU ' if passed else 'FALHOU ')+name,flush=True)
        if not passed:
            print(log[-16000:].decode('utf-8',errors='replace'),flush=True)
        save()
        if not passed:raise RuntimeError(name+': código inesperado '+str(proc.returncode))
        return proc.stdout
    def sf(name,code,binary,cwd,expected=0):
        return run(name,[binary,'-E','-P','-'],cwd,code.encode('utf-8'),expected)
    try:
        run('compilador',['gcc','--version'],root)
        for name,flags in [('estavel',''),('candidato','-DSANTAFE_DADOS_EXPERIMENTAL -DLUA_USE_APICHECK')]:
            stage=work/name;shutil.copytree(root,stage)
            run('compilar-'+name,['make','-C','src','mingw','MYCFLAGS='+flags],stage,timeout=600)
            exe=stage/'src/santafe.exe'; data=exe.read_bytes()
            pe=struct.unpack_from('<I',data,0x3c)[0]
            if data[:2]!=b'MZ' or data[pe:pe+4]!=b'PE\0\0' or struct.unpack_from('<H',data,pe+4)[0]!=0x8664:
                raise RuntimeError('não é executável PE x86_64')
            imports=run('importacoes-'+name,['objdump','-p',exe],stage).lower()
            if b'msys-2.0.dll' in imports or b'cygwin1.dll' in imports:
                raise RuntimeError('binário depende de emulação POSIX')
            run('versao-'+name,[exe,'-v'],stage)
        cand=work/'candidato';stable=work/'estavel';exe=cand/'src/santafe.exe';old=stable/'src/santafe.exe'
        # Continuar os ensaios independentes para mostrar mais de uma limitação.
        cases=[]
        for name,file in [('contrato',HERE/'contrato.fé'),
                          ('listas-nulos',cand/'experimentos/dados-v1/testar.fé'),
                          ('onfe',cand/'experimentos/dados-v1/testar-onfe.fé')]:
            cases.append((name,lambda n=name,f=file: sf(n,f.read_text(encoding='utf-8'),exe,cand)))
        cases.append(('iba-estatica',lambda: (
            run('compilar-iba',['gcc','-DSANTAFE_DADOS_EXPERIMENTAL','-DLUA_USE_WINDOWS',
                '-I'+str(cand/'src'),HERE/'iba.c',cand/'src/libsantafe.a','-lm','-lws2_32','-o',work/'iba.exe'],cand),
            run('executar-iba',[work/'iba.exe'],cand))))
        from dll import test as test_dll
        cases.append(('iba-dinamica',lambda:test_dll(cand,work,run,sf)))
        def bytecode():
            file=work/'simples.fe';file.write_text('mostre(42)\n',encoding='utf-8')
            for name,tree in [('estavel',stable),('candidato',cand)]:
                run('bytecode-compilar-'+name,[tree/'src/santafec.exe','-o',work/(name+'.bin'),file],tree)
                run('bytecode-executar-'+name,[tree/'src/santafe.exe','-E','-P',work/(name+'.bin')],tree)
            run('bytecode-recusa-antigo',[exe,'-E','-P',work/'estavel.bin'],cand,expected=None)
            run('bytecode-recusa-novo',[old,'-E','-P',work/'candidato.bin'],stable,expected=None)
        cases.append(('bytecode',bytecode))
        def paths():
            for name in ('pasta com espacos','ação-漢字-🟢'):
                p=work/name;p.mkdir();f=p/'arquivo.fe';f.write_text('mostre("CAMINHO_OK")\n',encoding='utf-8')
                output=run('caminho-'+str(len(name)),[exe,'-E','-P',f],p)
                if b'CAMINHO_OK' not in output:raise RuntimeError('caminho não executado')
            run('argumento-unicode',[exe,'-E','-P','-', 'José'],cand,b'garanta(arg[1]=="Jos\xc3\xa9")')
        cases.append(('caminhos-argumentos',paths))
        failures=[]
        for name,fn in cases:
            try:fn()
            except Exception as exc:failures.append({'grupo':name,'falha':str(exc)})
        result['falhas']=failures
        result['resultado']='falhou' if failures else 'passou_escopo_parcial'
        save();print(json.dumps(result,ensure_ascii=True,indent=2),flush=True)
        return 1 if failures else 0
    except Exception as exc:
        result['resultado']='falhou';result['falha']=str(exc);save()
        print(json.dumps(result,ensure_ascii=True,indent=2),flush=True)
        return 1

if __name__=='__main__':raise SystemExit(main())
