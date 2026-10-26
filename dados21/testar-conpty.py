"""Ensaio de protocolo ConPTY próprio, sem controlar a área de trabalho.

O byte ETX no canal VT percorre o caminho do Windows Terminal, diferente de
WriteConsoleInputW/GenerateConsoleCtrlEvent. Nenhum teclado global é injetado.
"""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

k = c.WinDLL('kernel32', use_last_error=True)
class Coord(c.Structure):
    _fields_ = [('X', w.SHORT), ('Y', w.SHORT)]
class Startup(c.Structure):
    _fields_ = [('cb', w.DWORD), ('reserved', w.LPWSTR), ('desktop', w.LPWSTR),
                ('title', w.LPWSTR), ('x', w.DWORD), ('y', w.DWORD),
                ('cx', w.DWORD), ('cy', w.DWORD), ('charsx', w.DWORD),
                ('charsy', w.DWORD), ('fill', w.DWORD), ('flags', w.DWORD),
                ('show', w.WORD), ('cbReserved', w.WORD), ('lpReserved', c.c_void_p),
                ('stdin', w.HANDLE), ('stdout', w.HANDLE), ('stderr', w.HANDLE)]
class StartupEx(c.Structure):
    _fields_ = [('startup', Startup), ('attributes', c.c_void_p)]
class Process(c.Structure):
    _fields_ = [('process', w.HANDLE), ('thread', w.HANDLE), ('pid', w.DWORD), ('tid', w.DWORD)]
def signature(name, args, result=w.BOOL):
    f=getattr(k,name); f.argtypes=args; f.restype=result; return f
pipe=signature('CreatePipe',[c.POINTER(w.HANDLE),c.POINTER(w.HANDLE),c.c_void_p,w.DWORD])
create=signature('CreatePseudoConsole',[Coord,w.HANDLE,w.HANDLE,w.DWORD,c.POINTER(w.HANDLE)],w.LONG)
closepty=signature('ClosePseudoConsole',[w.HANDLE],None)
close=signature('CloseHandle',[w.HANDLE])
init=signature('InitializeProcThreadAttributeList',[c.c_void_p,w.DWORD,w.DWORD,c.POINTER(c.c_size_t)])
attribute=signature('UpdateProcThreadAttribute',[c.c_void_p,w.DWORD,c.c_size_t,c.c_void_p,c.c_size_t,c.c_void_p,c.c_void_p])
delattr=signature('DeleteProcThreadAttributeList',[c.c_void_p],None)
start=signature('CreateProcessW',[w.LPCWSTR,w.LPWSTR,c.c_void_p,c.c_void_p,w.BOOL,w.DWORD,c.c_void_p,w.LPCWSTR,c.POINTER(StartupEx),c.POINTER(Process)])
read=signature('ReadFile',[w.HANDLE,c.c_void_p,w.DWORD,c.POINTER(w.DWORD),c.c_void_p])
write=signature('WriteFile',[w.HANDLE,c.c_void_p,w.DWORD,c.POINTER(w.DWORD),c.c_void_p])
wait=signature('WaitForSingleObject',[w.HANDLE,w.DWORD],w.DWORD)
exitcode=signature('GetExitCodeProcess',[w.HANDLE,c.POINTER(w.DWORD)])
terminate=signature('TerminateProcess',[w.HANDLE,w.UINT])
def check(value):
    if not value: raise c.WinError(c.get_last_error())

class Session:
    def __init__(self, exe):
        self.handles=[]; self.pty=w.HANDLE(); self.process=Process()
        self.condition=threading.Condition(); self.output=bytearray(); self.errors=[]
        self.attributes=None; self.reader=None; self.peers=[]
        try:
            ir,iw,orr,ow=[w.HANDLE() for _ in range(4)]
            check(pipe(c.byref(ir),c.byref(iw),None,0)); self.handles += [ir,iw]
            check(pipe(c.byref(orr),c.byref(ow),None,0)); self.handles += [orr,ow]
            self.input=iw; self.output_handle=orr; self.peers=[ir,ow]
            hr=create(Coord(180,50),ir,ow,0,c.byref(self.pty)); assert hr==0, hex(hr & 0xffffffff)
            self.reader=threading.Thread(target=self.drain,daemon=True); self.reader.start()
            n=c.c_size_t(); init(None,1,0,c.byref(n)); assert n.value
            self.attributes=c.create_string_buffer(n.value)
            check(init(self.attributes,1,0,c.byref(n)))
            check(attribute(self.attributes,0,0x00020016,self.pty,c.sizeof(w.HANDLE),None,None))
            si=StartupEx(); si.startup.cb=c.sizeof(si); si.attributes=c.cast(self.attributes,c.c_void_p)
            # ConPTY deve substituir os pipes redirecionados do runner.
            # Microsoft Terminal discussão15814: STARTF_USESTDHANDLES+NULL.
            si.startup.flags=0x100
            cmd=c.create_unicode_buffer(subprocess.list2cmdline([str(exe),'-E','-P','-i']))
            check(start(str(exe),cmd,None,None,False,0x00080000,None,None,c.byref(si),c.byref(self.process)))
            close(self.process.thread); self.process.thread=None
            for h in self.peers: close(h); self.handles.remove(h)
            self.peers=[]
        except BaseException:
            self.finish(); raise
    def drain(self):
        buf=c.create_string_buffer(4096); n=w.DWORD()
        while read(self.output_handle,buf,len(buf),c.byref(n),None) and n.value:
            with self.condition:
                self.output.extend(buf.raw[:n.value])
                if len(self.output)>2_000_000:
                    self.errors.append('saída excedeu limite'); del self.output[:-10000]
                self.condition.notify_all()
    def plain(self):
        text=self.output.decode('utf-8',errors='replace')
        text=re.sub(r'\x1b\][^\x07]*(?:\x07|\x1b\\)','',text)
        return re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',text)
    def expect(self, marker):
        with self.condition:
            ok=self.condition.wait_for(lambda: marker in self.plain() or self.errors,timeout=15)
            assert ok and not self.errors, (marker,self.plain()[-1800:],self.errors)
    def send(self, text):
        data=text.encode('utf-8'); n=w.DWORD()
        check(write(self.input,data,len(data),c.byref(n),None)); assert n.value==len(data)
    def finish(self):
        if self.process.process:
            if wait(self.process.process,0)!=0:
                # Apenas o processo próprio de teste, em caso de falha/prazo.
                check(terminate(self.process.process,99)); assert wait(self.process.process,5000)==0
            close(self.process.process); self.process.process=None
        if self.attributes: delattr(self.attributes); self.attributes=None
        for h in self.peers: close(h); self.handles.remove(h)
        self.peers=[]
        if self.pty:
            closepty(self.pty); self.pty=w.HANDLE()
        if self.reader:
            self.reader.join(5); assert not self.reader.is_alive(), 'leitor ConPTY órfão'
        for h in self.handles: close(h)
        self.handles=[]

def main():
    exe=Path(sys.argv[1]).resolve(); destination=Path(sys.argv[2]); destination.parent.mkdir(parents=True,exist_ok=True)
    report={'tipo':'ConPTY isolado, sem interface gráfica','testes':[], 'resultado':'em_execucao'}
    try:
        for number in range(10):
            session=Session(exe)
            try:
                session.expect('SantaFé> ')
                session.send('mostre("LE".."NDO"); es.esvazie(); es.leia()\r')
                session.expect('LENDO')
                time.sleep(.1) # alcançar a leitura bloqueante do caso
                session.send('\x03')
                session.expect('interrompido!')
                session.send('ã=3; mostre("RE".."CUPEROU"..ã)\r')
                session.expect('RECUPEROU3')
                session.send('so.saia(0)\r')
                assert wait(session.process.process,10000)==0
                rc=w.DWORD(); check(exitcode(session.process.process,c.byref(rc))); assert rc.value==0,rc.value
                report['testes'].append({'nome':'ctrl-c-leitura-retomada-unicode','repeticao':number,'passou':True})
            finally: session.finish()
        report['resultado']='passou'; return 0
    except Exception as exc:
        report['resultado']='falhou'; report['falha']=repr(exc); return 1
    finally:
        destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__': sys.exit(main())
