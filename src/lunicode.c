/*
** UTF-8 decoding and extended grapheme-cluster counting (UAX #29).
** See Copyright Notice in lua.h
*/

#include "lprefix.h"


#include "lunicode.h"


/* Grapheme_Cluster_Break values used by the UAX #29 rules below. */
enum {
  GCB_OTHER,
  GCB_CR,
  GCB_LF,
  GCB_CONTROL,
  GCB_EXTEND,
  GCB_ZWJ,
  GCB_RI,
  GCB_PREPEND,
  GCB_SPACINGMARK,
  GCB_L,
  GCB_V,
  GCB_T,
  GCB_LV,
  GCB_LVT
};
enum { INCB_NONE, INCB_CONSONANT, INCB_EXTEND, INCB_LINKER };
#include "lunicode-ranges.h"


/*
** Decode a single UTF-8 sequence without reading beyond 'end'.
** This deliberately accepts neither overlong sequences nor UTF-16
** surrogate values.
*/
static int utf8decode (const char **position, const char *end,
                       unsigned int *codepoint) {
  const unsigned char *s = (const unsigned char *)*position;
  unsigned int c;
  unsigned int result;
  int following;
  int i;

  if ((const char *)s >= end)
    return 0;
  c = s[0];
  if (c <= 0x7F) {
    *position = (const char *)s + 1;
    *codepoint = c;
    return 1;
  }
  if (c >= 0xC2 && c <= 0xDF) {
    result = c & 0x1F;
    following = 1;
  }
  else if (c >= 0xE0 && c <= 0xEF) {
    result = c & 0x0F;
    following = 2;
  }
  else if (c >= 0xF0 && c <= 0xF4) {
    result = c & 0x07;
    following = 3;
  }
  else
    return 0;

  if (end - (const char *)s <= following)
    return 0;
  for (i = 1; i <= following; i++) {
    c = s[i];
    if ((c & 0xC0) != 0x80)
      return 0;
    result = (result << 6) | (c & 0x3F);
  }
  if ((following == 2 && result < 0x800) ||
      (following == 3 && result < 0x10000) ||
      result > 0x10FFFF ||
      (result >= 0xD800 && result <= 0xDFFF))
    return 0;

  *position = (const char *)s + following + 1;
  *codepoint = result;
  return 1;
}


static int between (unsigned int c, unsigned int first, unsigned int last) {
  return c >= first && c <= last;
}


/* Lookup in the sorted Unicode-property ranges generated for the core. */
static int property (unsigned int c, const luaU_Range *ranges, size_t count) {
  size_t lo = 0;
  while (lo < count) {
    size_t mid = lo + (count - lo) / 2;
    if (c < ranges[mid].first) count = mid;
    else if (c > ranges[mid].last) lo = mid + 1;
    else return ranges[mid].property;
  }
  return 0;
}


size_t luaU_identifier (const char *s, size_t length) {
  const char *position = s;
  const char *end = s + length;
  size_t result = 0;
  while (position < end) {
    unsigned int c;
    int kind;
    if (!utf8decode(&position, end, &c)) break;
    /* ASCII fast path; classification never depends on the process locale. */
    if (c < 0x80)
      kind = (c == '_' || between(c, 'A', 'Z') || between(c, 'a', 'z'))
             ? 1 : between(c, '0', '9') ? 2 : 0;
    else
      kind = property(c, luaU_identifier_ranges,
                      sizeof(luaU_identifier_ranges) / sizeof(luaU_identifier_ranges[0]));
    if (kind == 0 || (result == 0 && kind != 1)) break;
    result = (size_t)(position - s);
  }
  return result;
}


static int graphemeproperty (unsigned int c) {
  unsigned int hangul;
  if (between(c, 0xAC00, 0xD7A3)) {
    hangul = c - 0xAC00;
    return (hangul % 28 == 0) ? GCB_LV : GCB_LVT;
  }
  return property(c, luaU_gcb_ranges,
                  sizeof(luaU_gcb_ranges) / sizeof(luaU_gcb_ranges[0]));
}


static int iscontrol (int property) {
  return property == GCB_CR || property == GCB_LF || property == GCB_CONTROL;
}


static int nobreak (int previous, int current, int zwj_after_extended_pictographic,
                    int regional_indicators, int ep, int conjunct) {
  if (previous == GCB_CR && current == GCB_LF) return 1;  /* GB3 */
  if (iscontrol(previous) || iscontrol(current)) return 0;  /* GB4/GB5 */
  if (previous == GCB_L &&
      (current == GCB_L || current == GCB_V || current == GCB_LV ||
       current == GCB_LVT)) return 1;  /* GB6 */
  if ((previous == GCB_LV || previous == GCB_V) &&
      (current == GCB_V || current == GCB_T)) return 1;  /* GB7 */
  if ((previous == GCB_LVT || previous == GCB_T) && current == GCB_T) return 1;  /* GB8 */
  if (current == GCB_EXTEND || current == GCB_ZWJ ||
      current == GCB_SPACINGMARK) return 1;  /* GB9/GB9a */
  if (previous == GCB_PREPEND) return 1;  /* GB9b */
  if (conjunct) return 1;  /* GB9c: InCB consonant/linker sequence */
  if (zwj_after_extended_pictographic && ep)
    return 1;  /* GB11 */
  if (previous == GCB_RI && current == GCB_RI && (regional_indicators & 1))
    return 1;  /* GB12/GB13 */
  return 0;
}


int luaU_graphemes (const char *s, size_t length, size_t *count,
                     size_t *invalid) {
  const char *position = s;
  const char *end = s + length;
  int previous = GCB_OTHER;
  int have_previous = 0;
  int extended_pictographic_run = 0;
  int zwj_after_extended_pictographic = 0;
  int regional_indicators = 0;
  int indic_run = 0;
  size_t result = 0;

  while (position < end) {
    const char *start = position;
    unsigned int codepoint;
    int current;
    int no_break;
    int ep, incb;

    if (!utf8decode(&position, end, &codepoint)) {
      if (invalid != NULL) *invalid = (size_t)(start - s) + 1;
      return 0;
    }
    current = graphemeproperty(codepoint);
    ep = property(codepoint, luaU_ep_ranges,
                  sizeof(luaU_ep_ranges) / sizeof(luaU_ep_ranges[0]));
    incb = property(codepoint, luaU_incb_ranges,
                    sizeof(luaU_incb_ranges) / sizeof(luaU_incb_ranges[0]));
    no_break = have_previous && nobreak(previous, current,
                                        zwj_after_extended_pictographic,
                                        regional_indicators, ep,
                                        indic_run == 2 && incb == INCB_CONSONANT);
    if (!no_break) result++;

    if (current == GCB_RI)
      regional_indicators = (previous == GCB_RI) ? !regional_indicators : 1;
    else
      regional_indicators = 0;

    if (incb == INCB_CONSONANT) indic_run = 1;
    else if (incb == INCB_LINKER && indic_run) indic_run = 2;
    else if (incb != INCB_EXTEND) indic_run = 0;

    if (ep) {
      extended_pictographic_run = 1;
      zwj_after_extended_pictographic = 0;
    }
    else if (current == GCB_EXTEND && extended_pictographic_run) {
      zwj_after_extended_pictographic = 0;
    }
    else if (current == GCB_ZWJ) {
      zwj_after_extended_pictographic = extended_pictographic_run;
      extended_pictographic_run = 0;
    }
    else {
      extended_pictographic_run = 0;
      zwj_after_extended_pictographic = 0;
    }
    previous = current;
    have_previous = 1;
  }
  if (count != NULL) *count = result;
  return 1;
}
