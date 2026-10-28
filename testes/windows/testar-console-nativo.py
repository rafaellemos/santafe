"""Ensaia o CLI em um console Windows próprio; não usa o console do operador."""
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import platform
import subprocess as sp
import sys


def ensaiar(exe, destino):
    k = c.WinDLL('kernel32', use_last_error=True)
    class Coord(c.Structure):
        _fields_ = [('X', w.SHORT), ('Y', w.SHORT)]
    class Rect(c.Structure):
        _fields_ = [('Left', w.SHORT), ('Top', w.SHORT), ('Right', w.SHORT), ('Bottom', w.SHORT)]
    class Info(c.Structure):
        _fields_ = [('size', Coord), ('cursor', Coord), ('attrs', w.WORD), ('window', Rect), ('maximum', Coord)]
    for name, args, result in (
        ('GetStdHandle', [w.DWORD], w.HANDLE),
        ('GetConsoleMode', [w.HANDLE, c.POINTER(w.DWORD)], w.BOOL),
        ('GetConsoleCP', [], w.UINT), ('GetConsoleOutputCP', [], w.UINT),
        ('SetConsoleCP', [w.UINT], w.BOOL), ('SetConsoleOutputCP', [w.UINT], w.BOOL),
        ('GetConsoleScreenBufferInfo', [w.HANDLE, c.POINTER(Info)], w.BOOL),
        ('FillConsoleOutputCharacterW', [w.HANDLE, w.WCHAR, w.DWORD, Coord, c.POINTER(w.DWORD)], w.BOOL),
        ('SetConsoleCursorPosition', [w.HANDLE, Coord], w.BOOL),
        ('ReadConsoleOutputCharacterW', [w.HANDLE, w.LPWSTR, w.DWORD, Coord, c.POINTER(w.DWORD)], w.BOOL),
    ):
        fn = getattr(k, name); fn.argtypes = args; fn.restype = result
    out = k.GetStdHandle(-11)
    mode = w.DWORD()
    assert k.GetConsoleMode(out, c.byref(mode)), 'exige console real próprio'
    original = (k.GetConsoleCP(), k.GetConsoleOutputCP())
    report = {'candidato': 'dados.25', 'sistema': platform.platform(),
              'console_real': True, 'testes': [], 'resultado': 'em_execucao',
              'visual_aprovado': False, 'entrada_interativa_aprovada': False}
    def salvar():
        destino.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    def pagina(cp):
        assert k.SetConsoleCP(cp) and k.SetConsoleOutputCP(cp)
        info = Info(); n = w.DWORD()
        assert k.GetConsoleScreenBufferInfo(out, c.byref(info))
        assert k.FillConsoleOutputCharacterW(out, ' ', info.size.X * info.size.Y, Coord(0, 0), c.byref(n))
        assert k.SetConsoleCursorPosition(out, Coord(0, 0))
    def texto():
        info = Info(); n = w.DWORD()
        assert k.GetConsoleScreenBufferInfo(out, c.byref(info))
        buf = c.create_unicode_buffer(info.size.X * info.size.Y + 1)
        assert k.ReadConsoleOutputCharacterW(out, buf, len(buf)-1, Coord(0, 0), c.byref(n))
        return buf[:n.value].encode('utf-16-le', 'surrogatepass').decode('utf-16-le')
    def executar(nome, cp, argumentos, esperado=0, trecho=None, bytes_saida=None, **opcoes):
        pagina(cp)
        p = sp.run([str(exe), '-E', '-P', *argumentos], timeout=30, **opcoes)
        assert p.returncode == esperado, (nome, p.returncode)
        assert (k.GetConsoleCP(), k.GetConsoleOutputCP()) == (cp, cp), nome+' alterou console'
        if trecho is not None:
            recebido = texto()
            assert trecho in recebido, (nome, 'conteudo_console', recebido.rstrip()[:1200])
        if bytes_saida is not None:
            assert p.stdout == bytes_saida, nome+' alterou bytes redirecionados'
        if opcoes.get('stderr') == sp.PIPE:
            assert not p.stderr, nome+' produziu erro inesperado'
        report['testes'].append({'nome': nome, 'passou': True}); salvar()
        return p
    try:
        for cp in (850, 1252, 65001):
            executar('versao-'+str(cp), cp, ['-v'], trecho='Santafé 3.0.0')
        f = destino.parent/'acentos.fe'
        f.write_text('mostre("ação José cafe\u0301")\n', encoding='utf-8')
        executar('texto-nfc-nfd', 850, [str(f)], trecho='ação José cafe\u0301')
        f.write_text('erro("falha ação")\n', encoding='utf-8')
        executar('erro-restaura', 850, [str(f)], esperado=1, trecho='falha ação')
        f.write_text('so.saia(7)\n', encoding='utf-8')
        executar('saida-explicita-restaura', 850, [str(f)], esperado=7)
        f.write_text('mostre("ação José")\n', encoding='utf-8')
        executar('todos-pipes', 850, [str(f)], input=b'', stdout=sp.PIPE, stderr=sp.PIPE,
                 bytes_saida='ação José\r\n'.encode('utf-8'))
        executar('saida-pipe-erro-console', 850, [str(f)], stdout=sp.PIPE,
                 bytes_saida='ação José\r\n'.encode('utf-8'))
        executar('entrada-pipe-saida-console', 850, ['-'], input='mostre("ação José")'.encode('utf-8'), trecho='ação José')
        report['resultado'] = 'passou_escopo_console'; salvar()
        return 0
    except Exception as exc:
        report['resultado'] = 'falhou'; report['falha'] = repr(exc); salvar(); return 1
    finally:
        k.SetConsoleCP(original[0]); k.SetConsoleOutputCP(original[1])


if __name__ == '__main__':
    if sys.platform != 'win32':
        raise SystemExit('Exige Python Windows nativo')
    exe, destino = map(lambda s: Path(s).resolve(), sys.argv[1:3])
    if len(sys.argv) > 3 and sys.argv[3] == '--console-filho':
        raise SystemExit(ensaiar(exe, destino))
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    destino.parent.mkdir(parents=True, exist_ok=True)
    start = sp.STARTUPINFO(); start.dwFlags |= sp.STARTF_USESHOWWINDOW; start.wShowWindow = 0
    # O filho tem seu próprio console. Não recebe chaves, rede, projetos ou credenciais.
    p = sp.run([sys.executable, str(Path(__file__).resolve()), str(exe), str(destino), '--console-filho'],
               creationflags=sp.CREATE_NEW_CONSOLE, startupinfo=start, timeout=180)
    if destino.exists():
        print(destino.read_text(encoding='utf-8'), flush=True)
    raise SystemExit(p.returncode)
