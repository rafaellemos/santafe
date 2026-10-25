"""VERSIONINFO para binários próprios; não altera DLLs de terceiros."""
from pathlib import Path
import hashlib, json, subprocess, sys

VERSION = '3.0.18.0'

def compile_resource(directory, filename, description, dll=False):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    key=hashlib.sha256((filename+description).encode()).hexdigest()[:12]
    rc=directory/(key+'.rc');obj=directory/(key+'.o')
    values={'CompanyName':'Rafael Alves Lemos','FileDescription':description,
            'FileVersion':VERSION,'InternalName':description,'OriginalFilename':filename,
            'ProductName':'Santafé','ProductVersion':VERSION,
            'LegalCopyright':'Copyright 2025-2026 Rafael Alves Lemos',
            'Comments':'Candidato dados.18; uso exclusivo em homologação.'}
    strings='\n'.join('VALUE '+json.dumps(k)+', '+json.dumps(v,ensure_ascii=False) for k,v in values.items())
    rc.write_text('#pragma code_page(65001)\n#include <winver.h>\n1 VERSIONINFO\n'
       'FILEVERSION 3,0,18,0\nPRODUCTVERSION 3,0,18,0\nFILEFLAGSMASK VS_FFI_FILEFLAGSMASK\n'
       'FILEFLAGS VS_FF_PRERELEASE\nFILEOS VOS_NT_WINDOWS32\nFILETYPE '+('VFT_DLL' if dll else 'VFT_APP')+'\n'
       'FILESUBTYPE 0\nBEGIN\nBLOCK "StringFileInfo"\nBEGIN\nBLOCK "041604B0"\nBEGIN\n'+strings+
       '\nEND\nEND\nBLOCK "VarFileInfo"\nBEGIN\nVALUE "Translation", 0x416, 1200\nEND\nEND\n',encoding='utf-8')
    subprocess.run(['windres','--codepage=65001','-i',str(rc),'-o',str(obj)],check=True)
    return obj

if __name__=='__main__':
    print(compile_resource(sys.argv[1],sys.argv[2],sys.argv[3],len(sys.argv)>4 and sys.argv[4]=='dll'))
