/* Extensão do realçador do manual SOMENTE para o candidato de dados. */
(function (P) {
  if (!P || !P.languages['santafé']) return;
  var base = P.languages['santafé'];
  // [[...]] já não é colar, mas comentários --[[...]] continuam iguais.
  if (Array.isArray(base.string)) {
    base.string = base.string.filter(function (r) {
      return !(r.pattern && r.pattern.source.startsWith('\\['));
    });
  }
  var g = P.languages.insertBefore('santafé', 'template-string', {
    'raw-string': {pattern: /\[(=+)\[[\s\S]*?\]\1\]/u, greedy: true, alias: 'string'}
  });
  var template = g['template-string'];
  if (template && template.inside) {
    template.inside['interpolation-variable'] = {
      pattern: /[®Ⓡ][\p{L}_][\p{L}\p{M}\p{N}_]*/u,
      greedy: true, alias: ['variable', 'variable-2']
    };
    template.inside.interpolation.inside.expression.inside = g;
  }
  P.languages.santafe = g;
})(window.Prism);
