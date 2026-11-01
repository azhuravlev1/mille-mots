"""Assemble words + conjugations + annotations, analyse endings, and emit index.html.

Segments: every displayed form is a list of [text, mark] pairs where mark is
  ""  plain text
  "~" stem change (letters that differ from the expected stem)
  n   (int) id of a highlighted pattern; text "" means a highlighted *gap* (nothing added
      where something is expected).
"""
import csv
import difflib
import glob
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

VOWELS = set('aeiouyéèêëàâîïôûùœ')
PERSON_LABELS = ['je', 'tu', 'il/elle', 'nous', 'vous', 'ils/elles']
OE_WORDS = {'oeil', 'coeur', 'soeur', 'oeuvre', 'boeuf', 'oeuf', 'voeu', 'noeud', 'moeurs'}
DUAL_AUX = {'passer', 'sortir', 'monter', 'descendre', 'rentrer', 'retourner', 'remonter'}

# ---------------------------------------------------------------- pattern registry
patterns = {}          # (section, key) -> dict
pattern_list = []


def pat(section, key, label, desc='', example=None):
    k = (section, key)
    if k not in patterns:
        p = {'id': len(pattern_list), 'sec': section, 'key': key, 'label': label,
             'desc': desc, 'n': 0, 'ex': []}
        patterns[k] = p
        pattern_list.append(p)
    p = patterns[k]
    p['n'] += 1
    if example and example not in p['ex'] and len(p['ex']) < 6:
        p['ex'].append(example)
    return p['id']


def plain(text):
    return [[text, '']]


def diff_stem(stem, expected):
    """Segments for `stem`, marking letters inserted/replaced relative to `expected`."""
    if expected is None or stem == expected:
        return [[stem, '']] if stem else []
    segs = []
    sm = difflib.SequenceMatcher(a=expected, b=stem, autojunk=False)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if b2 > b1:
            segs.append([stem[b1:b2], '' if op == 'equal' else '~'])
    return merge(segs)


def merge(segs):
    out = []
    for t, m in segs:
        if out and out[-1][1] == m and m in ('', '~') and t:
            out[-1][0] += t
        elif t or m not in ('', '~'):
            out.append([t, m])
    return out


def seg_ids(segs):
    return {m for _, m in segs if isinstance(m, int)}


# ---------------------------------------------------------------- verbs
NORMAL = {
    'present': [['e', 's'], ['es', 's'], ['e', 't'], ['ons'], ['ez'], ['ent']],
    'imparfait': [['ais'], ['ais'], ['ait'], ['ions'], ['iez'], ['aient']],
    'futur': [['ai'], ['as'], ['a'], ['ons'], ['ez'], ['ont']],
    'conditionnel': [['ais'], ['ais'], ['ait'], ['ions'], ['iez'], ['aient']],
    'subjonctif': [['e'], ['es'], ['e'], ['ions'], ['iez'], ['ent']],
}
IRREG = {
    'present': [['x', 'ai'], ['x'], [], ['mes'], ['tes'], ['ont']],
    'subjonctif': [['s'], ['s'], ['t'], ['ons'], ['ez'], []],
}
EXPECTED_TXT = {
    'present': ['-e / -s', '-es / -s', '-e / -t', '-ons', '-ez', '-ent'],
    'subjonctif': ['-e', '-es', '-e', '-ions', '-iez', '-ent'],
}
TENSE_SHORT = {'present': 'présent', 'subjonctif': 'subjonctif'}


def verb_base(inf):
    if inf.endswith('oir'):
        return inf[:-3]
    if inf.endswith(('er', 'ir', 're')):
        return inf[:-2]
    return inf


def with_pronoun(slot, form):
    pron = PERSON_LABELS[slot].split('/')[0]
    if pron == 'je' and form[:1] in VOWELS | {'h'}:
        return "j'" + form
    return f'{pron} {form}'


def split_ending(form, tense, slot):
    for e in sorted(NORMAL[tense][slot], key=len, reverse=True):
        if form.endswith(e):
            return form[:-len(e)], e, None
    for e in sorted(IRREG.get(tense, [[]] * 6)[slot], key=len, reverse=True):
        if form.endswith(e):
            return form[:-len(e)], e, 'irr'
    return form, '', 'gap'


def analyse_verb(inf, cj, examples_word):
    t = cj['t']
    base = verb_base(inf)
    pres = t['present']
    second_group = inf.endswith('ir') and pres[3] and pres[3].endswith('issons')

    def stem_of(form, tense, slot):
        return split_ending(form, tense, slot)[0] if form else None

    nous_stem = stem_of(pres[3], 'present', 3)
    ils_stem = stem_of(pres[5], 'present', 5)
    if inf.endswith('re'):
        fut_exp = inf[:-1]
    elif inf.endswith('oir'):
        fut_exp = inf[:-3] + 'r'
    else:
        fut_exp = inf

    def expected_stem(tense, slot):
        if tense == 'present':
            if second_group:
                return base + ('i' if slot < 3 else 'iss')
            return base
        if tense == 'imparfait':
            return nous_stem
        if tense in ('futur', 'conditionnel'):
            return fut_exp
        if tense == 'subjonctif':
            return nous_stem if slot in (3, 4) else ils_stem
        return None

    out = {}
    pats = set()
    for tense, row in t.items():
        cells = []
        for slot, form in enumerate(row):
            if not form:
                cells.append(None)
                continue
            stem, ending, kind = split_ending(form, tense, slot)
            segs = diff_stem(stem, expected_stem(tense, slot))
            if kind is None:
                segs.append([ending, ''])
            elif kind == 'irr':
                pid = pat('verb', f'{tense}:{ending}',
                          f'-{ending}',
                          f'{TENSE_SHORT.get(tense, tense)} {PERSON_LABELS[slot]}: -{ending} instead of '
                          f'{EXPECTED_TXT[tense][slot]}', with_pronoun(slot, form))
                segs.append([ending, pid])
            else:
                pid = pat('verb', f'{tense}:gap', '∅ (nothing added)',
                          f'{TENSE_SHORT.get(tense, tense)}: no ending where '
                          f'{EXPECTED_TXT.get(tense, ["?"] * 6)[slot]} is expected',
                          with_pronoun(slot, form))
                segs.append(['', pid])
            cells.append(merge(segs))
            pats |= seg_ids(segs)
        out[tense] = cells

    pp = cj.get('pp', '')
    pp_segs = []
    if pp:
        for e in ('é', 'i', 'u', 'û'):
            if pp.endswith(e):
                pp_segs = diff_stem(pp[:-1], base) + [[e, '']]
                break
        else:
            for e in ('ert', 'int', 'is', 'it', 'us', 't'):
                if pp.endswith(e):
                    pid = pat('verb', f'pp:{e}', f'-{e}',
                              f'past participle in -{e} (instead of -é / -i / -u)', pp)
                    pp_segs = diff_stem(pp[:-len(e)], base) + [[e, pid]]
                    break
            else:
                pp_segs = plain(pp)
        pp_segs = merge(pp_segs)
        pats |= seg_ids(pp_segs)
    aux = cj.get('aux', 'avoir')
    if inf in DUAL_AUX:
        aux = 'être/avoir'
    stem_changes = any(m == '~' for row in out.values() for c in row if c for _, m in c)
    return {'t': out, 'pp': pp_segs, 'aux': aux}, pats, stem_changes


# ---------------------------------------------------------------- gender / number changes
def tail_split(a, b):
    """Split a→b into (common, a_tail, b_tail), backing off so tails start at a vowel group."""
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    if n == len(a) and n > 0:
        n -= 1
    steps = 0
    while n > 0 and a[n - 1] in VOWELS and steps < 2:
        n -= 1
        steps += 1
    return a[:n], a[n:], b[n:]


def change_segs(section, kind, src, dst, normal_add, label_word):
    """Segments for dst derived from src; highlight when it isn't the normal +e / +s."""
    if dst == src + normal_add:
        return [[src, ''], [normal_add, '']], None
    if dst == src:
        if normal_add == 'e' and src.endswith('e'):
            return plain(dst), None
        if normal_add == 's' and src[-1:] in ('s', 'x', 'z'):
            return plain(dst), None
        pid = pat(section, f'{kind}:gap', '∅ (unchanged)',
                  f'{KIND_TXT[kind]}: nothing added where +{normal_add} is expected', label_word)
        return [[dst, ''], ['', pid]], pid
    if kind == 'pl' and dst.lower() == src.lower() + 'x':
        pid = pat(section, 'pl:+x', '+x', 'plural in -x instead of -s (-eau, -eu, some -ou)', label_word)
        return [[dst[:-1], ''], ['x', pid]], pid
    if '-' in src and kind == 'pl':
        pid = pat(section, 'pl:compound', 'compound', 'plural: compound noun, each part agrees', label_word)
        return [[dst, pid]], pid
    common, a_t, b_t = tail_split(src.lower(), dst.lower())
    common = dst[:len(common)]
    b_t = dst[len(common):]
    irregular = src[:1].lower() != dst[:1].lower() or (
        not dst.lower().startswith(src.lower()) and len(b_t) > 0.8 * len(dst))
    if irregular:
        pid = pat(section, f'{kind}:irr', 'irregular', f'{KIND_TXT[kind]}: completely irregular',
                  label_word)
        return [[dst, pid]], pid
    pid = pat(section, f'{kind}:{a_t}→{b_t}', f'-{a_t} → -{b_t}',
              f'{KIND_TXT[kind]}: -{a_t} becomes -{b_t}', label_word)
    return ([[common, '']] if common else []) + [[b_t, pid]], pid


KIND_TXT = {'fem': 'feminine', 'pl': 'plural', 'fpl': 'feminine plural'}


PREFIX_FAMILY = {'r': 're', 'ré': 're', 'res': 're', 'em': 'en', 'ap': 'a', 'ac': 'a', 'at': 'a',
                 'ar': 'a', 'de': 'dé', 'dés': 'dé', 'im': 'in', 'il': 'in', 'ir': 'in'}
PREFIX_VARIANTS = {'re': 're- / r-', 'en': 'en- / em-', 'a': 'a- / ap- / ac-', 'dé': 'dé- / de-',
                   'in': 'in- / im-'}


def derivation_segs(section, word, der, headword_for_label):
    """Underline prefix/suffix of a derived word. Returns segments and pattern ids."""
    if not der:
        return plain(word), set()
    pre = (der.get('prefix') or '').strip('-')
    suf = (der.get('suffix') or '').strip('-')
    body = word
    segs_pre, segs_suf = [], []
    pids = set()
    from_pos = der.get('fromPos', '')
    if pre and body.startswith(pre):
        fam = PREFIX_FAMILY.get(pre, pre)
        variants = PREFIX_VARIANTS.get(fam, f'{fam}-')
        pid = pat(section, f'pre:{fam}', variants, f'prefix {variants}', headword_for_label)
        segs_pre = [[pre, pid]]
        body = body[len(pre):]
        pids.add(pid)
    if suf == '∅':
        pid = pat(section, 'suf:∅', '∅ (bare stem)',
                  f'formed from a {from_pos or "word"} with nothing added', headword_for_label)
        segs_suf = [['', pid]]
        pids.add(pid)
    elif suf and body.endswith(suf) and len(body) > len(suf):
        key = f'suf:{suf}'
        pid = pat(section, key, f'-{suf}', f'suffix -{suf}', headword_for_label)
        segs_suf = [[suf, pid]]
        body = body[:-len(suf)]
        pids.add(pid)
    elif suf:
        print(f'  ! suffix "{suf}" does not match "{word}"', file=sys.stderr)
    return segs_pre + [[body, '']] + segs_suf, pids


# ---------------------------------------------------------------- adverbs in -ment
def adverb_segs(adv, base_ms, base_fs):
    if not adv.endswith('ment') or not base_ms:
        return plain(adv), set()
    stem = adv[:-4]
    if base_fs and stem == base_fs:
        return [[stem, ''], ['ment', '']], set()
    if base_ms.endswith(('ant', 'ent')) and adv.endswith(('amment', 'emment')):
        suf = adv[-6:]
        pid = pat('adv', f'suf:{suf}', f'-{suf}',
                  f'adjectives in -{suf[:2]}nt → -{suf} (not -{suf[:2]}nte + ment)', adv)
        return [[adv[:-6], ''], [suf, pid]], {pid}
    if stem == base_ms and base_fs and base_fs != base_ms:
        pid = pat('adv', 'gap', '∅ (no feminine -e)',
                  'built on the masculine: the feminine -e is missing before -ment', adv)
        return [[stem, ''], ['', pid], ['ment', '']], {pid}
    if base_fs and base_fs.endswith('e') and stem == base_fs[:-1] + 'é':
        pid = pat('adv', 'suf:ément', '-ément', 'feminine -e becomes -é before -ment', adv)
        return [[stem[:-1], ''], ['é', pid], ['ment', '']], {pid}
    if stem == base_ms:
        return [[stem, ''], ['ment', '']], set()
    common, _, b_t = tail_split(base_fs or base_ms, stem)
    pid = pat('adv', 'irr', 'irregular', 'irregular -ment formation', adv)
    return [[common, ''], [b_t, pid], ['ment', '']], {pid}


# ---------------------------------------------------------------- pronunciation
# Lexique phoneme -> learner respelling. Easy sounds use plain English letters; sounds that
# exist in neither English nor Russian get a marked symbol that is explained in the key.
PHON = {
    'a': 'a', 'i': 'ee', 'e': 'ay', 'E': 'eh', 'o': 'oh', 'O': 'o', 'u': 'oo', '°': 'uh',
    'y': 'ü', '2': 'eu', '9': 'eu', '@': 'ã', '§': 'õ', '5': 'ẽ', '1': 'ẽ',
    'j': 'y', 'w': 'w', '8': 'ü',
    'R': 'r', 'S': 'sh', 'Z': 'zh', 'N': 'ny', 'G': 'ng',
    'p': 'p', 't': 't', 'k': 'k', 'b': 'b', 'd': 'd', 'g': 'g', 'f': 'f', 's': 's', 'v': 'v',
    'z': 'z', 'm': 'm', 'n': 'n', 'l': 'l',
    'A': 'ahy',   # a + j  (travail): avoid reading "ay" as in "day"
}


def respell(syll):
    """'b§-ZuR' -> 'bõ·zhoor'."""
    out = []
    for syl in syll.split('-'):
        syl = syl.replace('aj', 'A')
        out.append(''.join(PHON.get(c, c) for c in syl))
    return '·'.join(out)


# ---------------------------------------------------------------- load everything
def load_lexique(words):
    """Feminine adjective forms by lemma, and the phonetic syllabification of each headword."""
    want = {w['lemma']: w['cgram'] for w in words}
    fem, best, pron, pron_score = {}, {}, {}, {}
    with open('data/Lexique383.tsv', encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            f = float(r['freqfilms2']) + float(r['freqlivres'])
            o = r['ortho']
            if o in want and r['lemme'] == o and r['syll']:
                cg = want[o]
                score = f + (1000 if r['cgram'] == cg or (cg == 'VER' and r['cgram'] == 'AUX') else 0)
                if score > pron_score.get(o, -1):
                    pron_score[o] = score
                    pron[o] = respell(r['syll'])
            if not r['cgram'].startswith('ADJ') or r['genre'] != 'f' or r['nombre'] not in ('s', ''):
                continue
            if f >= best.get(r['lemme'], -1):
                best[r['lemme']] = f
                fem[r['lemme']] = o
    return fem, pron


def main():
    words = json.load(open('data/words.json', encoding='utf-8'))
    conj = json.load(open('data/conj.json', encoding='utf-8'))
    ann = {}
    for path in sorted(glob.glob('annotations/*.json')):
        for a in json.load(open(path, encoding='utf-8')):
            ann[a['w']] = a
    lex_fem, pron = load_lexique(words)
    adj_forms = {w['lemma']: w.get('forms') or {} for w in words if w['section'] in ('adj', 'other')}

    missing = [w['lemma'] for w in words if w['lemma'] not in ann]
    if missing:
        print(f'  ! {len(missing)} words without annotation, e.g. {missing[:8]}', file=sys.stderr)

    sections = defaultdict(list)
    n_stem_change = 0
    for w in words:
        a = ann.get(w['lemma'], {})
        if a.get('drop'):
            continue
        sec = w['section']
        lem = w['lemma']
        disp = a.get('display') or (lem.replace('oe', 'œ') if lem in OE_WORDS else lem)
        e = {'lem': lem, 'w': disp, 'rank': w['rank'], 'en': a.get('en', ''), 'sim': a.get('sim', 'none')}
        if lem in pron:
            e['pr'] = pron[lem]
        for k in ('note', 'ru', 'faux', 'ru_like', 'ex', 'pron', 'before', 'grp', 'cls', 'sub'):
            if a.get(k):
                e[k] = a[k]
        der = a.get('der')
        if der:
            e['der'] = {k: der[k] for k in ('from', 'fromPos', 'prefix', 'suffix') if der.get(k)}
        pats = set()

        if sec == 'verb':
            cj = conj.get(lem)
            if cj:
                v, p, changed = analyse_verb(lem, cj, lem)
                e.update(v)
                pats |= p
                n_stem_change += changed
            e['head'], dp = derivation_segs('verb', disp, der, disp)
            pats |= dp
        elif sec == 'noun':
            forms = w.get('forms', {})
            g = a.get('g') or forms.get('gender') or ''
            e['g'] = g
            e['head'], dp = derivation_segs('noun', disp, der, disp)
            pats |= dp
            if a.get('pl') and a['pl'] != disp:
                segs, pid = change_segs('noun', 'pl', disp, a['pl'], 's', f'{disp} → {a["pl"]}')
                e['pl'] = segs
                if pid is not None:
                    pats.add(pid)
            fem = a.get('fem') if 'fem' in a else None
            if fem:
                segs, pid = change_segs('noun', 'fem', disp, fem, 'e', f'{disp} → {fem}')
                e['fem'] = segs
                if pid is not None:
                    pats.add(pid)
        elif sec == 'adj':
            f = a.get('forms') or w.get('forms') or {}
            ms, fs, mp, fp = (f.get(k, '') for k in ('ms', 'fs', 'mp', 'fp'))
            e['head'], dp = derivation_segs('adj', ms or disp, der, disp)
            pats |= dp
            fs_s, p1 = change_segs('adj', 'fem', ms, fs, 'e', f'{ms} → {fs}')
            mp_s, p2 = change_segs('adj', 'pl', ms, mp, 's', f'{ms} → {mp}')
            fp_s, p3 = change_segs('adj', 'fpl', fs, fp, 's', f'{fs} → {fp}')
            e['forms'] = {'ms': e['head'], 'fs': fs_s, 'mp': mp_s, 'fp': fp_s}
            pats |= {p for p in (p1, p2, p3) if p is not None}
            if not der:
                e['origin'] = 'base'
            elif der.get('fromPos') in ('noun', 'verb'):
                e['origin'] = der['fromPos']
            else:
                e['origin'] = 'other'
        elif sec == 'adv':
            base = (der or {}).get('from')
            if base and der.get('suffix', '').strip('-') == 'ment':
                bf = (adj_forms.get(base, {}).get('fs') or lex_fem.get(base)
                      or (base if base.endswith('e') else base + 'e'))
                e['head'], p = adverb_segs(disp, base, bf)
                e['origin'] = 'ment'
            else:
                e['head'], p = derivation_segs('adv', disp, der, disp)
                e['origin'] = 'derived' if der else 'base'
            pats |= p
        else:
            f = w.get('forms')
            if f:
                e['forms'] = {k: v for k, v in f.items()}
            e['head'] = plain(disp)
        e['pats'] = sorted(pats)
        sections[sec].append(e)

    assign_colors()
    data = {'sections': sections, 'patterns': pattern_list, 'persons': PERSON_LABELS,
            'stats': {k: len(v) for k, v in sections.items()}}
    js = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    tpl = open('src/template.html', encoding='utf-8').read()
    css = open('src/style.css', encoding='utf-8').read()
    app = open('src/app.js', encoding='utf-8').read()
    html = (tpl.replace('/*STYLE*/', css)
               .replace('/*DATA*/', js.replace('</', '<\\/'))
               .replace('/*APP*/', app))
    open('index.html', 'w', encoding='utf-8').write(html)
    print({k: len(v) for k, v in sections.items()}, 'patterns:', len(pattern_list),
          'verbs with stem changes:', n_stem_change)


# Distinct, print-safe colours; the most frequent patterns get the most distinct ones.
PALETTE = [
    '#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4', '#0fa3b1', '#d6249f', '#8aa100',
    '#9a6324', '#800000', '#000075', '#ff6f91', '#2e8b57', '#b8860b', '#5f4bb6', '#c71585',
    '#008080', '#e07a5f', '#6b8e23', '#1e90ff', '#a0522d', '#7b2cbf', '#d62828', '#2a9d8f',
]
STYLES = ['solid', 'double', 'dashed']


def assign_colors():
    by_sec = defaultdict(list)
    for p in pattern_list:
        by_sec[p['sec']].append(p)
    for sec, ps in by_sec.items():
        ps.sort(key=lambda p: -p['n'])
        for i, p in enumerate(ps):
            p['color'] = PALETTE[i % len(PALETTE)]
            p['style'] = STYLES[(i // len(PALETTE)) % len(STYLES)]


if __name__ == '__main__':
    main()
