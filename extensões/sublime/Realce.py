"""Realce embutido usando gramáticas nativas e regiões de primeiro plano.

Mesmo mecanismo visual usado pelo cliente LSP do Sublime para tokens semânticos.
Não depende de LSP, Node, rede ou execução do programa do usuário.
"""
from collections import defaultdict
import time
import sublime
import sublime_plugin
from .bibliotecas.realce_embutido import documentos_embutidos

PREFIXO = "santafe_realce_"
PAINEL = "santafe_realce_virtual"
LIMITE = 400000
ESTADOS = {}
ATIVO = False
CONFIGURACAO = None


def tipo_dos_escopos(escopo):
    scopes = escopo.split()
    if any(s.startswith('comment') for s in scopes):
        return 'comment'
    for s in reversed(scopes):
        for prefixo, tipo in [('entity.name.tag', 'tag'), ('entity.other.attribute-name', 'attribute'),
                ('constant.character', 'entity'), ('string', 'string'), ('constant.numeric', 'number'),
                ('constant.language', 'constant'), ('storage', 'storage'), ('keyword.operator', 'operator'),
                ('keyword', 'keyword'), ('entity.name.function', 'function'), ('entity.name.type', 'type'),
                ('support', 'support'), ('variable.parameter', 'parameter'), ('variable.other.property', 'property'),
                ('variable', 'variable')]:
            if s == prefixo or s.startswith(prefixo + '.'):
                return tipo
    return 'punctuation' if any(s.startswith('punctuation') for s in scopes) else 'text'


def escopo_visual(view, escopo):
    visual = escopo + ' meta.santafe-embedded'
    paleta = view.settings().get('santafe_paleta_embutida', CONFIGURACAO.get('paleta_embutida', 'tema') if CONFIGURACAO else 'tema')
    if paleta == 'suave':
        fundo = view.style().get('background', '#272822').lstrip('#')
        clara = len(fundo) >= 6 and sum(int(fundo[i:i+2], 16) for i in (0, 2, 4)) > 384
        visual += ' meta.santafe-soft-' + ('clara' if clara else 'escura') + '-' + tipo_dos_escopos(escopo)
    return visual


def elegivel(view):
    syntax = view.syntax()
    return bool(syntax and syntax.scope == "source.santafe" and not view.settings().get("is_widget"))


def limpe(view):
    estado = ESTADOS.pop(view.id(), {})
    for chave in estado.get("chaves", []):
        view.erase_regions(chave)


def tokens_nativos(view, fonte, cancelado=lambda: False):
    janela = view.window()
    if not janela or len(fonte) > LIMITE or cancelado():
        return []
    documentos = documentos_embutidos(fonte)
    resultado = []
    if not documentos:
        return resultado
    # Painel oculto, reutilizado somente durante este trabalho no thread principal.
    # Nenhuma aba, arquivo ou preferência do usuário é criada/modificada.
    painel = janela.create_output_panel(PAINEL)
    painel.settings().set("word_wrap", False)
    painel.settings().set("gutter", False)
    inicio = time.monotonic()
    try:
        for documento in documentos:
            if cancelado() or time.monotonic() - inicio > 2:
                return []
            texto, mapa = documento["texto"], documento["mapa"]
            if any(len(linha) > 20000 for linha in texto.split("\n")):
                continue
            painel.set_read_only(False)
            painel.run_command("select_all")
            painel.run_command("left_delete")
            painel.assign_syntax("Packages/HTML/HTML.sublime-syntax" if documento["linguagem"] == "html"
                                 else "Packages/JavaScript/JavaScript.sublime-syntax")
            painel.run_command("append", {"characters": texto})
            painel.set_read_only(True)
            p = 0
            while p < len(mapa):
                if p % 512 == 0 and (cancelado() or time.monotonic() - inicio > 2):
                    return []
                escopo = painel.scope_name(p).strip()
                # extract_scope() inclui subescopos: pular até seu fim omitiria
                # atributos/tokens internos. Agrupar pela pilha exata de cada ponto.
                fim = p + 1
                while fim < len(mapa) and painel.scope_name(fim).strip() == escopo:
                    if fim % 512 == 0 and (cancelado() or time.monotonic() - inicio > 2):
                        return []
                    fim += 1
                anterior = None
                for inicio_fonte, fim_fonte in mapa[p:fim]:
                    if inicio_fonte < 0:
                        anterior = None
                    elif anterior and inicio_fonte <= anterior[1]:
                        anterior[1] = max(anterior[1], fim_fonte)
                    else:
                        anterior = [inicio_fonte, fim_fonte, escopo]
                        resultado.append(anterior)
                p = fim
    finally:
        janela.destroy_output_panel(PAINEL)
    return sorted(resultado, key=lambda t: (t[0], t[1]))


def aplique(view, fonte, versao, tokens):
    if not view.is_valid() or not elegivel(view) or view.change_count() != versao:
        return False
    limpe(view)
    grupos = defaultdict(list)
    for inicio, fim, escopo in tokens:
        if fim > inicio and escopo:
            grupos[escopo].append(sublime.Region(inicio, fim))
    chaves = []
    for indice, (escopo, regioes) in enumerate(grupos.items()):
        chave = PREFIXO + str(indice)
        # Sem DRAW_NO_FILL: o Sublime aplica o foreground do escopo ao texto.
        # Sem NO_UNDO em builds antigos: constante só foi adicionada em 4132.
        flags = sublime.DRAW_NO_OUTLINE | getattr(sublime, "NO_UNDO", 0)
        visual = escopo_visual(view, escopo)
        # Sem fundo explícito o Sublime inverte foreground/background. Os temas
        # nativos recebem uma regra transparente no pacote; temas particulares
        # podem definir a mesma regra, sem alterar suas cores de primeiro plano.
        if view.style_for_scope(visual).get("background") == view.style_for_scope(escopo).get("background"):
            continue
        view.add_regions(chave, regioes, visual, flags=flags)
        chaves.append(chave)
    ESTADOS[view.id()] = dict(versao=versao, tokens=tokens, chaves=chaves)
    return True


def atualize(view, versao=None):
    if not ATIVO or not view.is_valid():
        return
    if not elegivel(view) or view.size() > LIMITE:
        limpe(view)
        return
    versao = view.change_count() if versao is None else versao
    if versao != view.change_count():
        return
    fonte = view.substr(sublime.Region(0, view.size()))
    try:
        tokens = tokens_nativos(view, fonte, lambda: not view.is_valid() or view.change_count() != versao)
        aplique(view, fonte, versao, tokens)
    except Exception as erro:
        limpe(view)
        print("Santafé: realce embutido indisponível; realce básico preservado: {}".format(erro))


class SantafeRealceListener(sublime_plugin.EventListener):
    def agende(self, view):
        if not elegivel(view):
            if view.id() in ESTADOS:
                limpe(view)
            return
        versao = view.change_count()
        # Remover cores obsoletas imediatamente; digitação rápida cancela versões.
        limpe(view)
        sublime.set_timeout(lambda: atualize(view, versao), 250)

    def on_modified(self, view):
        self.agende(view)

    def on_load(self, view):
        self.agende(view)

    def on_activated(self, view):
        estado = ESTADOS.get(view.id())
        if not estado or estado["versao"] != view.change_count() or not elegivel(view):
            self.agende(view)

    def on_close(self, view):
        ESTADOS.pop(view.id(), None)

    def on_post_text_command(self, view, command_name, args):
        if command_name in ("set_file_type", "set_syntax_file"):
            self.agende(view)


def plugin_loaded():
    global ATIVO, CONFIGURACAO
    ATIVO = True
    CONFIGURACAO = sublime.load_settings('Santafe.sublime-settings')
    CONFIGURACAO.add_on_change('santafe-paleta', redesenhe)
    redesenhe()


def redesenhe():
    for janela in sublime.windows():
        for view in janela.views():
            if elegivel(view):
                sublime.set_timeout(lambda view=view: atualize(view), 0)


def plugin_unloaded():
    global ATIVO
    ATIVO = False
    if CONFIGURACAO:
        CONFIGURACAO.clear_on_change('santafe-paleta')
    for janela in sublime.windows():
        for view in janela.views():
            limpe(view)


class SantafePaletaEmbutidaCommand(sublime_plugin.WindowCommand):
    def run(self):
        def escolha(indice):
            if indice >= 0:
                config = sublime.load_settings('Santafe.sublime-settings')
                config.set('paleta_embutida', ('tema', 'suave')[indice])
                sublime.save_settings('Santafe.sublime-settings')
        self.window.show_quick_panel(['Acompanhar o tema', 'Paleta suave para HTML e JavaScript'], escolha)
