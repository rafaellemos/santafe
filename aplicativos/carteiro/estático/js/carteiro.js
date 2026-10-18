(function () {
  "use strict";

  const menus = Array.from(document.querySelectorAll("details.carteiro-menu"));
  const detalhesPostais = Array.from(
    document.querySelectorAll("details.carteiro-carta-detalhes")
  );

  function fecheMenus(exceto) {
    menus.forEach(function (menu) {
      if (menu !== exceto) menu.removeAttribute("open");
    });
  }

  menus.forEach(function (menu) {
    menu.addEventListener("toggle", function () {
      if (menu.open) fecheMenus(menu);
    });
  });

  function fecheDetalhesPostais(exceto) {
    detalhesPostais.forEach(function (detalhes) {
      if (detalhes !== exceto) detalhes.removeAttribute("open");
    });
  }

  detalhesPostais.forEach(function (detalhes) {
    detalhes.addEventListener("toggle", function () {
      if (detalhes.open) fecheDetalhesPostais(detalhes);
    });
  });

  document.addEventListener("click", function (evento) {
    if (!evento.target.closest("details.carteiro-menu")) fecheMenus();
    if (!evento.target.closest("details.carteiro-carta-detalhes")) {
      fecheDetalhesPostais();
    }
  });

  document.addEventListener("keydown", function (evento) {
    if (evento.key === "Escape") {
      fecheMenus();
      fecheDetalhesPostais();
    }
  });

  document.querySelectorAll('form[action="/carteiro/enviar"]').forEach(function (formulário) {
    formulário.addEventListener("submit", function () {
      const botão = formulário.querySelector('button[type="submit"]');
      if (!botão || botão.disabled) return;
      botão.disabled = true;
      botão.innerHTML = '<i class="material-icons left">hourglass_empty</i>Colocando na fila…';
    });
  });

  document.querySelectorAll("form[data-confirma]").forEach(function (formulário) {
    formulário.addEventListener("submit", function (evento) {
      if (!window.confirm(formulário.dataset.confirma)) evento.preventDefault();
    });
  });

  document.querySelectorAll("form[data-seleção-em-lote]").forEach(function (formulário) {
    const todas = formulário.querySelector("[data-selecionar-todas]");
    const cartas = Array.from(formulário.querySelectorAll("[data-carta]"));
    const ações = formulário.querySelector("[data-ações-selecionadas]");
    const açãoDoLote = formulário.querySelector("[data-acao-lote]");
    const escopo = formulário.querySelector("[data-escopo-seleção]");
    const aviso = formulário.querySelector("[data-seleção-global]");
    const avisoDaPágina = aviso && aviso.querySelector("[data-aviso-página]");
    const avisoTotal = aviso && aviso.querySelector("[data-aviso-total]");
    const selecionarEscopo = aviso && aviso.querySelector("[data-selecionar-escopo]");
    const limparEscopo = aviso && aviso.querySelector("[data-limpar-escopo]");

    function useEscopoDaPágina() {
      escopo.value = "pagina";
    }

    function atualize() {
      const quantidade = cartas.filter(function (carta) { return carta.checked; }).length;
      todas.checked = quantidade > 0 && quantidade === cartas.length;
      todas.indeterminate = quantidade > 0 && quantidade < cartas.length;
      ações.hidden = quantidade === 0;
      ações.setAttribute("aria-hidden", quantidade === 0 ? "true" : "false");
      const páginaInteira = quantidade > 0 && quantidade === cartas.length;
      aviso.hidden = !páginaInteira;
      if (!páginaInteira) useEscopoDaPágina();
      const tudo = escopo.value === "todas";
      avisoDaPágina.hidden = tudo;
      avisoTotal.hidden = !tudo;
      selecionarEscopo.hidden = tudo || Number(aviso.dataset.total) <= cartas.length;
      limparEscopo.hidden = !tudo;
    }

    todas.addEventListener("change", function () {
      useEscopoDaPágina();
      cartas.forEach(function (carta) { carta.checked = todas.checked; });
      atualize();
    });
    cartas.forEach(function (carta) {
      carta.addEventListener("change", function () {
        useEscopoDaPágina();
        atualize();
      });
    });

    formulário.querySelectorAll("[data-selecionar]").forEach(function (opção) {
      opção.addEventListener("click", function () {
        const modo = opção.dataset.selecionar;
        useEscopoDaPágina();
        cartas.forEach(function (carta) {
          if (modo === "todas") carta.checked = true;
          if (modo === "nenhuma") carta.checked = false;
          if (modo === "lidas") carta.checked = carta.dataset.lida === "verdadeiro";
          if (modo === "não-lidas") carta.checked = carta.dataset.lida !== "verdadeiro";
        });
        fecheMenus();
        atualize();
      });
    });

    if (selecionarEscopo) selecionarEscopo.addEventListener("click", function () {
      escopo.value = "todas";
      atualize();
    });
    if (limparEscopo) limparEscopo.addEventListener("click", function () {
      useEscopoDaPágina();
      cartas.forEach(function (carta) { carta.checked = false; });
      atualize();
    });

    formulário.querySelectorAll("[data-executar-acao]").forEach(function (botão) {
      botão.addEventListener("click", function () {
        const quantidade = cartas.filter(function (carta) { return carta.checked; }).length;
        if (quantidade === 0 || !açãoDoLote) return;
        const ação = botão.value;
        açãoDoLote.value = ação;
        fecheMenus();
        if (typeof formulário.requestSubmit === "function") formulário.requestSubmit();
        else formulário.submit();
      });
    });

    formulário.addEventListener("submit", function (evento) {
      const quantidade = cartas.filter(function (carta) { return carta.checked; }).length;
      if (quantidade === 0 || !açãoDoLote || açãoDoLote.value === "") {
        evento.preventDefault();
        return;
      }
      formulário.querySelectorAll("[data-executar-acao]").forEach(function (botão) {
        botão.disabled = true;
      });
    });
    atualize();
  });

  function alterneCarta(cartão, abrir) {
    const corpo = cartão.querySelector("[data-corpo-carta]");
    const alternador = cartão.querySelector("[data-alternar-carta]");
    if (cartão.hasAttribute("data-carta-fixa")) {
      if (corpo) corpo.hidden = false;
      cartão.classList.add("aberta");
      return;
    }
    if (!corpo || !alternador) return;
    corpo.hidden = !abrir;
    cartão.classList.toggle("aberta", abrir);
    alternador.setAttribute("aria-expanded", abrir ? "true" : "false");
  }

  const cartões = Array.from(document.querySelectorAll("[data-carta-conversa]"));
  cartões.forEach(function (cartão) {
    const alternador = cartão.querySelector("[data-alternar-carta]");
    if (!alternador) return;
    alternador.addEventListener("click", function (evento) {
      if (evento.target.closest("[data-não-alternar]")) return;
      alterneCarta(cartão, alternador.getAttribute("aria-expanded") !== "true");
      atualizeControlesDaConversa();
    });
    alternador.addEventListener("keydown", function (evento) {
      if (evento.key !== "Enter" && evento.key !== " ") return;
      if (evento.target.closest("[data-não-alternar]")) return;
      evento.preventDefault();
      alterneCarta(cartão, alternador.getAttribute("aria-expanded") !== "true");
      atualizeControlesDaConversa();
    });
  });

  const cartõesAlternáveis = cartões.filter(function (cartão) {
    return !cartão.hasAttribute("data-carta-fixa");
  });

  function atualizeControlesDaConversa() {
    const algumaAberta = cartõesAlternáveis.some(function (cartão) {
      return cartão.classList.contains("aberta");
    });
    const algumaFechada = cartõesAlternáveis.some(function (cartão) {
      return !cartão.classList.contains("aberta");
    });
    document.querySelectorAll("[data-expandir-conversa]").forEach(function (botão) {
      botão.hidden = !algumaFechada;
    });
    document.querySelectorAll("[data-recolher-conversa]").forEach(function (botão) {
      botão.hidden = !algumaAberta;
    });
  }

  document.querySelectorAll("[data-expandir-conversa]").forEach(function (botão) {
    botão.addEventListener("click", function () {
      cartõesAlternáveis.forEach(function (cartão) {
        alterneCarta(cartão, true);
      });
      atualizeControlesDaConversa();
    });
  });

  document.querySelectorAll("[data-recolher-conversa]").forEach(function (botão) {
    botão.addEventListener("click", function () {
      cartõesAlternáveis.forEach(function (cartão) {
        alterneCarta(cartão, false);
      });
      atualizeControlesDaConversa();
    });
  });

  atualizeControlesDaConversa();

  document.querySelectorAll('form[action="/carteiro/enviar"]').forEach(function (formulário) {
    const texto = formulário.querySelector("[data-campo-texto]");
    const seçãoTexto = formulário.querySelector("[data-compositor-texto]");
    const seçãoHTML = formulário.querySelector("[data-compositor-html]");
    const editor = formulário.querySelector("[data-editor-html]");
    const campoHTML = formulário.querySelector("[data-editor-html-campo]");
    const modos = Array.from(formulário.querySelectorAll("[data-modo-compositor]"));
    if (!texto || !seçãoTexto || !seçãoHTML || !editor || !campoHTML) return;
    let modoAtual = campoHTML.value.trim() !== "" ? "html" : "texto";

    function textoComoHTML(valor) {
      const fragmento = document.createDocumentFragment();
      String(valor || "").split(/\n{2,}/).forEach(function (parágrafo) {
        const p = document.createElement("p");
        p.textContent = parágrafo;
        fragmento.appendChild(p);
      });
      const recipiente = document.createElement("div");
      recipiente.appendChild(fragmento);
      return recipiente.innerHTML;
    }

    function sincronizeHTML() {
      campoHTML.value = editor.innerHTML.trim();
      texto.value = editor.innerText.replace(/\n{3,}/g, "\n\n").trim();
    }

    function useModo(modo) {
      const html = modo === "html";
      if (html && editor.innerHTML.trim() === "" && texto.value.trim() !== "") {
        editor.innerHTML = textoComoHTML(texto.value);
      }
      if (!html) sincronizeHTML();
      seçãoTexto.hidden = html;
      seçãoHTML.hidden = !html;
      modoAtual = modo;
      modos.forEach(function (botão) {
        const ativo = botão.dataset.modoCompositor === modo;
        botão.classList.toggle("ativo", ativo);
        botão.setAttribute("aria-pressed", ativo ? "true" : "false");
      });
      if (html) {
        sincronizeHTML();
        editor.focus();
      } else texto.focus();
    }

    modos.forEach(function (botão) {
      botão.addEventListener("click", function () {
        useModo(botão.dataset.modoCompositor);
      });
    });
    seçãoHTML.querySelectorAll("[data-comando-editor]").forEach(function (botão) {
      botão.addEventListener("mousedown", function (evento) {
        evento.preventDefault();
      });
      botão.addEventListener("click", function () {
        editor.focus();
        document.execCommand(
          botão.dataset.comandoEditor,
          false,
          botão.dataset.valorEditor || null
        );
        sincronizeHTML();
      });
    });
    editor.addEventListener("input", sincronizeHTML);
    editor.addEventListener("paste", function (evento) {
      evento.preventDefault();
      const colar = (evento.clipboardData || window.clipboardData).getData("text/plain");
      document.execCommand("insertText", false, colar);
    });
    formulário.addEventListener("submit", function () {
      if (modoAtual === "html") sincronizeHTML();
      else campoHTML.value = "";
    });
    if (campoHTML.value.trim() !== "") useModo("html");
  });

  const visualizador = document.querySelector("[data-visualizador-anexo]");
  if (visualizador) {
    const quadro = visualizador.querySelector("[data-visualizador-quadro]");
    const imagem = visualizador.querySelector("[data-visualizador-imagem]");
    const título = visualizador.querySelector("[data-visualizador-título]");
    const baixar = visualizador.querySelector("[data-visualizador-baixar]");
    const imprimir = visualizador.querySelector("[data-imprimir-visualizador]");
    const cabeçalho = visualizador.querySelector(":scope > header");
    const rodapé = visualizador.querySelector(":scope > footer");
    let urlAtual = "";

    function useModoDoVisualizador(modo) {
      visualizador.classList.toggle("imagem", modo === "imagem");
      visualizador.classList.toggle("documento", modo !== "imagem");
      if (modo !== "imagem") {
        visualizador.style.removeProperty("--carteiro-visualizador-largura");
        visualizador.style.removeProperty("--carteiro-visualizador-altura");
        visualizador.style.removeProperty("--carteiro-visualizador-altura-imagem");
      }
    }

    function ajusteVisualizadorDaImagem() {
      if (!visualizador.classList.contains("imagem") ||
          !imagem.naturalWidth || !imagem.naturalHeight) return;
      const vista = window.visualViewport;
      const larguraDaTela = vista ? vista.width : window.innerWidth;
      const alturaDaTela = vista ? vista.height : window.innerHeight;
      const margem = larguraDaTela <= 520 ? 0 : 32;
      const larguraMáxima = Math.max(1, larguraDaTela - margem);
      const alturaExternaMáxima = Math.max(1, alturaDaTela - margem);
      const alturaDoCromo = cabeçalho.getBoundingClientRect().height +
        rodapé.getBoundingClientRect().height;
      const alturaMáxima = Math.max(1, alturaExternaMáxima - alturaDoCromo);
      const escala = Math.min(
        larguraMáxima / imagem.naturalWidth,
        alturaMáxima / imagem.naturalHeight
      );
      const largura = Math.max(1, Math.round(imagem.naturalWidth * escala));
      const altura = Math.max(1, Math.round(imagem.naturalHeight * escala));
      visualizador.style.setProperty(
        "--carteiro-visualizador-largura", largura + "px");
      visualizador.style.setProperty(
        "--carteiro-visualizador-altura", (altura + alturaDoCromo) + "px");
      visualizador.style.setProperty(
        "--carteiro-visualizador-altura-imagem", altura + "px");
    }

    function fecheVisualizador() {
      if (typeof visualizador.close === "function" && visualizador.open) {
        visualizador.close();
      } else visualizador.removeAttribute("open");
      urlAtual = "";
      quadro.removeAttribute("src");
      quadro.hidden = false;
      imagem.removeAttribute("src");
      imagem.alt = "";
      imagem.hidden = true;
      useModoDoVisualizador("documento");
    }

    function abraVisualizador(botão) {
      urlAtual = botão.dataset.anexoUrl || "";
      if (!urlAtual) return;
      const nome = botão.dataset.anexoNome || "Visualização do anexo";
      const tipo = (botão.dataset.anexoTipo || "").toLowerCase();
      título.textContent = nome;
      baixar.href = botão.dataset.anexoBaixar || urlAtual;
      if (tipo.startsWith("image/")) {
        useModoDoVisualizador("imagem");
        quadro.removeAttribute("src");
        quadro.hidden = true;
        imagem.src = urlAtual;
        imagem.alt = nome;
        imagem.hidden = false;
      } else {
        imagem.removeAttribute("src");
        imagem.alt = "";
        imagem.hidden = true;
        useModoDoVisualizador("documento");
        quadro.src = urlAtual;
        quadro.hidden = false;
      }
      if (typeof visualizador.showModal === "function") visualizador.showModal();
      else visualizador.setAttribute("open", "");
      if (tipo.startsWith("image/") && imagem.complete) {
        window.requestAnimationFrame(ajusteVisualizadorDaImagem);
      }
    }

    imagem.addEventListener("load", ajusteVisualizadorDaImagem);
    window.addEventListener("resize", ajusteVisualizadorDaImagem);
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", ajusteVisualizadorDaImagem);
    }

    document.querySelectorAll("[data-visualizar-anexo]").forEach(function (botão) {
      if (botão === visualizador) return;
      botão.addEventListener("click", function (evento) {
        evento.preventDefault();
        evento.stopPropagation();
        abraVisualizador(botão);
      });
    });
    visualizador.querySelectorAll("[data-fechar-visualizador]").forEach(function (botão) {
      botão.addEventListener("click", fecheVisualizador);
    });
    visualizador.addEventListener("click", function (evento) {
      if (evento.target === visualizador) fecheVisualizador();
    });
    visualizador.addEventListener("cancel", function (evento) {
      evento.preventDefault();
      fecheVisualizador();
    });
    imprimir.addEventListener("click", function () {
      if (!urlAtual) return;
      const janela = window.open(urlAtual, "_blank", "noopener");
      if (!janela) return;
      janela.addEventListener("load", function () {
        window.setTimeout(function () { janela.print(); }, 120);
      }, { once: true });
    });
  }

  document.querySelectorAll("[data-imprimir-anexo]").forEach(function (botão) {
    botão.addEventListener("click", function () {
      const url = botão.dataset.anexoUrl;
      if (!url) return;
      const janela = window.open(url, "_blank", "noopener");
      if (!janela) return;
      janela.addEventListener("load", function () {
        window.setTimeout(function () { janela.print(); }, 120);
      }, { once: true });
    });
  });

  document.querySelectorAll("a[data-imprimir-carta]").forEach(function (ligação) {
    ligação.addEventListener("click", function (evento) {
      evento.preventDefault();
      fecheMenus();
      const janela = window.open(ligação.href, "_blank");
      if (!janela) {
        window.location.href = ligação.href;
        return;
      }
      janela.addEventListener("load", function () {
        window.setTimeout(function () { janela.print(); }, 80);
      }, { once: true });
    });
  });
})();
