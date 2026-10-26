"""Entrada no console próprio do ensaio: KEY_EVENT UTF-16, nunca UI do operador."""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import platform
import subprocess as sp
import sys
import threading


def ensaiar(exe, destino):
    k = c.WinDLL('kernel32', use_last_error=True)
    class Char(c.Union):
        _fields_ = [('UnicodeChar', w.WCHAR), ('AsciiChar', c.c_char)]
    class Key(c.Structure):
        _fields_ = [('down', w.BOOL), ('repeat', w.WORD), ('vk', w.WORD),
                    ('scan', w.WORD), ('char', Char), ('state', w.DWORD)]
    class Event(c.Union):
        _fields_ = [('key', Key), ('padding', c.c_byte * 16)]
    class Record(c.Structure):
        _fields_ = [('kind', w.WORD), ('event', Event)]
    assert c.sizeof(Record) == 20
    for name, args, result in (
        ('GetStdHandle', [w.DWORD], w.HANDLE),
        ('GetConsoleMode', [w.HANDLE, c.POINTER(w.DWORD)], w.BOOL),
        ('GetConsoleCP', [], w.UINT), ('GetConsoleOutputCP', [], w.UINT),
        ('SetConsoleCP', [w.UINT], w.BOOL), ('SetConsoleOutputCP', [w.UINT], w.BOOL),
        ('FlushConsoleInputBuffer', [w.HANDLE], w.BOOL),
        ('WriteConsoleInputW', [w.HANDLE, c.POINTER(Record), w.DWORD, c.POINTER(w.DWORD)], w.BOOL),
        ('GenerateConsoleCtrlEvent', [w.DWORD, w.DWORD], w.BOOL),
    ):
        fn = getattr(k, name); fn.argtypes = args; fn.restype = result
    inp = k.GetStdHandle(-10)
    mode = w.DWORD()
    assert k.GetConsoleMode(inp, c.byref(mode)), 'exige console próprio real'
    original = (k.GetConsoleCP(), k.GetConsoleOutputCP())
    report = {'candidato': 'dados.21-preparacao', 'sistema': platform.platform(),
              'origem': 'KEY_EVENT UTF16 em console exclusivo criado pelo ensaio',
              'visual_aprovado': False, 'resultado': 'em_execucao', 'testes': []}
    def salvar():
        destino.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    def escrever(texto):
        raw = texto.encode('utf-16-le', 'surrogatepass')
        units = [int.from_bytes(raw[i:i+2], 'little') for i in range(0, len(raw), 2)]
        records = (Record * (2 * len(units)))()
        for i, unit in enumerate(units):
            for j in range(2):
                rec = records[i * 2 + j]; rec.kind = 1
                rec.event.key.down = not j; rec.event.key.repeat = 1
                rec.event.key.vk = 13 if unit == 13 else (90 if unit == 26 else (67 if unit == 3 else 0))
                rec.event.key.char.UnicodeChar = chr(unit)
                rec.event.key.state = 8 if unit in (3,26) else 0
        written = w.DWORD()
        assert k.WriteConsoleInputW(inp, records, len(records), c.byref(written))
        assert written.value == len(records)
    def caso(nome, texto, argumentos, esperado, cp=850, status=0, ausente=None):
        assert k.FlushConsoleInputBuffer(inp)
        assert k.SetConsoleCP(cp) and k.SetConsoleOutputCP(cp)
        p = sp.Popen([str(exe), '-E', '-P', *argumentos], stdout=sp.PIPE, stderr=sp.PIPE)
        try:
            escrever(texto)
            out, err = p.communicate(timeout=15)
        except BaseException:
            p.kill(); p.communicate(); raise
        received = out.decode('utf-8', 'strict').replace('\r\n', '\n')
        assert p.returncode == status, (nome, p.returncode, err.decode('utf-8', 'backslashreplace'))
        assert esperado in received, (nome, 'esperado', esperado, 'recebido', received[:400], 'erro', err[:400])
        if ausente is not None: assert ausente not in received, (nome,'executou entrada truncada')
        assert (k.GetConsoleCP(), k.GetConsoleOutputCP()) == (cp, cp), nome+' alterou console'
        report['testes'].append({'nome': nome, 'passou': True}); salvar()
    def interromper(evento, codigo=None, tecla=False):
        # O console é exclusivo deste processo-filho e do interpretador; nunca
        # envia sinal ao console do runner ou a aplicativos do operador.
        Handler = c.WINFUNCTYPE(w.BOOL, w.DWORD)
        events = []
        def sinal(event):
            events.append(event)
            return True
        handler = Handler(sinal)
        k.SetConsoleCtrlHandler.argtypes = [Handler, w.BOOL]
        k.SetConsoleCtrlHandler.restype = w.BOOL
        # MSYS2/runner pode ter herdado o atributo de ignorar Ctrl+C. Remover
        # somente neste console novo antes de criar o processo sob teste.
        assert k.SetConsoleCtrlHandler(Handler(), False)
        assert k.SetConsoleCtrlHandler(handler, True)
        assert k.FlushConsoleInputBuffer(inp)
        assert k.SetConsoleCP(850) and k.SetConsoleOutputCP(850)
        args = ['-i'] if codigo is None else ['-e', 'mostre("PRONTO"); es.esvazie(); '+codigo]
        p = sp.Popen([str(exe), '-E', '-P', *args], stdout=sp.PIPE,
                     stderr=None if codigo is None else sp.PIPE)
        ready = threading.Event(); output = bytearray()
        marker = 'SantaFé> '.encode() if codigo is None else b'PRONTO\r\n'
        def ler():
            while True:
                b = p.stdout.read(1)
                if not b: break
                output.extend(b)
                if output.endswith(marker): ready.set()
        reader = threading.Thread(target=ler, daemon=True); reader.start()
        try:
            assert ready.wait(10), 'interpretador não chegou ao prompt'
            if tecla: escrever('\x03')
            else: assert k.GenerateConsoleCtrlEvent(evento, 0)
            try:
                assert p.wait(timeout=10) != 0, 'interrupção não encerrou a leitura'
            except sp.TimeoutExpired:
                raise AssertionError({'interrupcao': 'tecla' if tecla else 'evento',
                                      'codigo': codigo, 'sinais_no_console': events})
            reader.join(timeout=5)
            assert not reader.is_alive(), 'leitor órfão no ensaio'
            if codigo is not None:
                assert b'interrompido' in p.stderr.read(), 'SIGINT não preservou o diagnóstico do interpretador'
            assert (k.GetConsoleCP(), k.GetConsoleOutputCP()) == (850,850), 'interrupção não restaurou console'
            nome = 'interrupcao-'+str(evento)+'-restaura' if codigo is None else 'interrompe-programa-'+codigo
            if tecla: nome += '-tecla'
            report['testes'].append({'nome': nome, 'passou': True}); salvar()
        finally:
            if p.poll() is None: p.kill(); p.wait(timeout=5)
            reader.join(timeout=5); p.stdout.close()
            if p.stderr is not None: p.stderr.close()
            k.SetConsoleCtrlHandler(handler, False)
    try:
        for cp in (850, 1252, 65001):
            caso('repl-acento-'+str(cp), 'ã=3 mostre("RESULTADO",ã)\rso.saia(0)\r', ['-i'], 'RESULTADO\t3\n', cp)
        caso('repl-nfd-emoji', 'cafe\u0301="ação 🟢" mostre("RESULTADO",cafe\u0301)\rso.saia(0)\r', ['-i'], 'RESULTADO\tação 🟢\n')
        caso('leia-linha-nfc-nfd', 'ação cafe\u0301 🟢\r', ['-e', 'mostre("RESULTADO",es.leia())'], 'RESULTADO\tação cafe\u0301 🟢\n')
        caso('leia-octetos', 'ã\r', ['-e', 'local a=es.leia(1); local b=es.leia(1); mostre("RESULTADO",a..b,es.leia())'], 'RESULTADO\tã\t\n')
        caso('leia-numero-retorno-byte', '42ação\r', ['-e', 'local a=es.leia("*número"); mostre("RESULTADO",a,es.leia())'], 'RESULTADO\t42\tação\n')
        long = 'a'*9000+'ação 🟢'
        caso('repl-linha-longa', 'mostre("RESULTADO",#"'+long+'")\rso.saia(0)\r', ['-i'], 'RESULTADO\t'+str(len(long.encode()))+'\n')
        boundary = 'a'*255+'🟢ã'
        caso('leia-par-utf16', boundary+'\r', ['-e', 'local a=es.leia(); mostre("RESULTADO",#a,a)'], 'RESULTADO\t'+str(len(boundary.encode()))+'\t'+boundary+'\n')
        caso('leia-ctrlz', '\x1a\r', ['-e', 'mostre("RESULTADO",es.leia()==inexistente)'], 'RESULTADO\tverdadeiro\n')
        caso('programa-stdin-unicode', 'local ã=3; mostre("RESULTADO",ã,"ação 🟢")\r\x1a\r', ['-'], 'RESULTADO\t3\tação 🟢\n')
        caso('repl-recusa-linha-truncada', 'mostre("NAO_EXECUTAR") --'+'a'*17000+'\r', ['-i'], 'SantaFé> ', status=1, ausente='NAO_EXECUTAR')
        caso('leia-recusa-linha-truncada', 'a'*17000+'\r', ['-e', 'local valor,motivo=es.leia(); mostre("RESULTADO",valor==inexistente,motivo~=inexistente)'], 'RESULTADO\tverdadeiro\tverdadeiro\n')
        interromper(0)
        interromper(1)
        interromper(0, 'enquanto verdadeiro início fim')
        interromper(0, 'es.leia()')
        interromper(0, 'es.leia()', tecla=True)
        report['resultado'] = 'passou_entrada_console'; salvar(); return 0
    except Exception as exc:
        report['resultado'] = 'falhou'; report['falha'] = repr(exc); salvar(); return 1
    finally:
        k.FlushConsoleInputBuffer(inp)
        k.SetConsoleCP(original[0]); k.SetConsoleOutputCP(original[1])


if __name__ == '__main__':
    if sys.platform != 'win32':
        raise SystemExit('Exige Python Windows nativo')
    exe, destino = [Path(p).resolve() for p in sys.argv[1:3]]
    if '--console-filho' in sys.argv[3:]:
        raise SystemExit(ensaiar(exe, destino))
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    destino.parent.mkdir(parents=True, exist_ok=True)
    start = sp.STARTUPINFO(); start.dwFlags |= sp.STARTF_USESHOWWINDOW; start.wShowWindow = 0
    p = sp.run([sys.executable, str(Path(__file__).resolve()), str(exe), str(destino), '--console-filho'],
               creationflags=sp.CREATE_NEW_CONSOLE, startupinfo=start, timeout=240)
    if destino.exists(): print(destino.read_text(encoding='utf-8'), flush=True)
    raise SystemExit(p.returncode)
