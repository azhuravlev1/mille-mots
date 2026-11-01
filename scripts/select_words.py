"""Pick the ~1000 most frequent French lemmas from Lexique 3.83 and extract their forms.

Output: data/words.json  (list of {lemma, section, cgram, freq, rank, forms})
"""
import csv
import collections
import json

N = 1000
SECTION = {
    'NOM': 'noun', 'VER': 'verb', 'AUX': 'verb', 'ADJ': 'adj', 'ADV': 'adv',
}
SKIP_CGRAM = {'LIA'}
SKIP_LEMMAS = {
    'nouvelle',  # feminine of nouveau, listed as its own ADJ lemma
    'quoi',      # mis-tagged ADJ
    'ok', 'ouais', 'hein', 'est-ce que', 'allier', 'pincer', "d'autres", "l'un",
}
# Lexique lists each determiner form as its own lemma; fold them into one paradigm entry.
PARADIGMS = {
    'le': {'ms': 'le', 'fs': 'la', 'mp': 'les', 'fp': 'les'},
    'un': {'ms': 'un', 'fs': 'une', 'mp': 'des', 'fp': 'des'},
    'mon': {'ms': 'mon', 'fs': 'ma', 'mp': 'mes', 'fp': 'mes'},
    'ton': {'ms': 'ton', 'fs': 'ta', 'mp': 'tes', 'fp': 'tes'},
    'son': {'ms': 'son', 'fs': 'sa', 'mp': 'ses', 'fp': 'ses'},
    'notre': {'ms': 'notre', 'fs': 'notre', 'mp': 'nos', 'fp': 'nos'},
    'votre': {'ms': 'votre', 'fs': 'votre', 'mp': 'vos', 'fp': 'vos'},
    'leur': {'ms': 'leur', 'fs': 'leur', 'mp': 'leurs', 'fp': 'leurs'},
    'ce': {'ms': 'ce', 'fs': 'cette', 'mp': 'ces', 'fp': 'ces', 'ms2': 'cet'},
    'quel': {'ms': 'quel', 'fs': 'quelle', 'mp': 'quels', 'fp': 'quelles'},
    'celui': {'ms': 'celui', 'fs': 'celle', 'mp': 'ceux', 'fp': 'celles'},
    'aucun': {'ms': 'aucun', 'fs': 'aucune', 'mp': 'aucuns', 'fp': 'aucunes'},
    'tel': {'ms': 'tel', 'fs': 'telle', 'mp': 'tels', 'fp': 'telles'},
    'lequel': {'ms': 'lequel', 'fs': 'laquelle', 'mp': 'lesquels', 'fp': 'lesquelles'},
    'certain': None, 'tout': None, 'autre': None, 'quelque': None,
    'au': {'ms': 'au', 'fs': 'à la', 'mp': 'aux', 'fp': 'aux'},
    'du': {'ms': 'du', 'fs': 'de la', 'mp': 'des', 'fp': 'des'},
}
FOLDED = {
    'la', 'les', 'une', 'des', 'ma', 'mes', 'ta', 'tes', 'sa', 'ses', 'nos', 'vos', 'leurs',
    'cette', 'ces', 'cet', 'quelle', 'celle', 'ceux', 'celles', 'aucune', 'telle', 'laquelle',
    'aux', 'certains', 'toute', 'tous', 'autres', 'quelques',
}
SECTION_OVERRIDE = {'peu': 'adv', 'personne': 'other', 'rien': 'other'}

rows = list(csv.DictReader(open('data/Lexique383.tsv', encoding='utf-8'), delimiter='\t'))


def freq(r):
    return float(r['freqfilms2']) + float(r['freqlivres'])


lemfreq = collections.defaultdict(float)
cgrams = collections.defaultdict(lambda: collections.defaultdict(float))
by_lemma = collections.defaultdict(list)
for r in rows:
    lem, cg = r['lemme'], r['cgram']
    if not lem or lem.endswith("'") or cg in SKIP_CGRAM or lem in SKIP_LEMMAS or lem in FOLDED:
        continue
    if len(lem) == 1 and cg == 'NOM':
        continue
    f = float(r['freqlemfilms2']) + float(r['freqlemlivres'])
    cgrams[lem][cg] = max(cgrams[lem][cg], f)
    by_lemma[(lem, cg)].append(r)

entries = []
for lem, cgs in cgrams.items():
    # verbs: fold AUX into VER
    if 'AUX' in cgs:
        cgs['VER'] = max(cgs.get('VER', 0), cgs['AUX'])
        del cgs['AUX']
    best_cg = max(cgs, key=cgs.get)
    total = cgs[best_cg]
    section = SECTION_OVERRIDE.get(lem) or SECTION.get(best_cg, 'other')
    other_classes = sorted(c for c in cgs if c != best_cg and cgs[c] > 5)
    entries.append({'lemma': lem, 'cgram': best_cg, 'section': section,
                    'freq': round(total, 2), 'also': other_classes})

entries.sort(key=lambda e: -e['freq'])
entries = entries[:N]
for i, e in enumerate(entries, 1):
    e['rank'] = i


def pick(rs, **cond):
    best = None
    for r in rs:
        if all(r[k] in v for k, v in cond.items()):
            if best is None or freq(r) > freq(best):
                best = r
    return best['ortho'] if best else None


for e in entries:
    lem = e['lemma']
    if PARADIGMS.get(lem):
        e['forms'] = PARADIGMS[lem]
    elif e['section'] == 'noun':
        rs = by_lemma[(lem, 'NOM')]
        base = [r for r in rs if r['ortho'] == lem]
        genders = collections.Counter()
        for r in base:
            genders[r['genre']] += freq(r) + 0.01
        genders.pop('', None)
        if not genders:
            for r in rs:
                if r['genre']:
                    genders[r['genre']] += freq(r) + 0.01
        g = genders.most_common(1)[0][0] if genders else ''
        forms = {'gender': g}
        pl = pick([r for r in rs if r['ortho'] != lem], nombre={'p'}, genre={g, ''})
        if pl:
            forms['pl'] = pl
        if g == 'm':
            fem = pick([r for r in rs if r['ortho'] != lem], genre={'f'}, nombre={'s', ''})
            if fem:
                forms['fem'] = fem
        e['forms'] = forms
    elif e['section'] == 'adj':
        rs = by_lemma[(lem, 'ADJ')]
        fs = pick([r for r in rs if r['ortho'] != lem], genre={'f'}, nombre={'s', ''}) or lem
        mp = pick([r for r in rs if r['ortho'] != fs], genre={'m', ''}, nombre={'p'})
        if not mp:
            mp = lem if lem[-1] in 'sx' else lem + 's'
        fp = pick(rs, genre={'f', ''}, nombre={'p'}) if fs != lem else mp
        if not fp or fp == mp and fs != lem:
            fp = fs + 's'
        e['forms'] = {'ms': lem, 'fs': fs, 'mp': mp, 'fp': fp}

json.dump(entries, open('data/words.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(collections.Counter(e['section'] for e in entries))
print(collections.Counter(e['cgram'] for e in entries if e['section'] == 'other'))
