"""Generate conjugations for every verb in data/words.json using verbecc.

Output: data/conj.json  {infinitive: {aux, pp, t: {tense: [je, tu, il, nous, vous, ils]}}}
"""
import json
import logging
import re

from verbecc import CompleteConjugator, LangCodeISO639_1

logging.disable(logging.WARNING)

TENSES = {
    'present': ('indicatif', 'présent'),
    'imparfait': ('indicatif', 'imparfait'),
    'futur': ('indicatif', 'futur-simple'),
    'conditionnel': ('conditionnel', 'présent'),
    'subjonctif': ('subjonctif', 'présent'),
}
PERSONS = [('1', 's'), ('2', 's'), ('3', 's'), ('1', 'p'), ('2', 'p'), ('3', 'p')]
PRON_RE = re.compile(r"^(qu'|que )?(j'|je |tu |il |elle |on |nous |vous |ils |elles )")

conj = CompleteConjugator(LangCodeISO639_1.fr)
words = json.load(open('data/words.json', encoding='utf-8'))
out = {}
for w in words:
    if w['section'] != 'verb':
        continue
    inf = w['lemma']
    try:
        d = json.loads(str(conj.conjugate(inf)))
    except Exception as ex:  # noqa: BLE001
        print('FAIL', inf, ex)
        continue
    moods = d['moods']
    res = {'t': {}}
    for key, (mood, tense) in TENSES.items():
        cells = moods.get(mood, {}).get(tense, [])
        row = []
        for p, n in PERSONS:
            cand = [c for c in cells if c.get('p') == p and c.get('n') == n and c.get('g', 'm') == 'm']
            if cand and cand[0]['c']:
                row.append(PRON_RE.sub('', cand[0]['c'][0]))
            else:
                row.append(None)
        res['t'][key] = row
    pc = moods.get('indicatif', {}).get('passé-composé', [])
    pc3 = [c for c in pc if c.get('p') == '3' and c.get('n') == 's' and c.get('g', 'm') == 'm' and c['c']]
    if pc3:
        parts = PRON_RE.sub('', pc3[0]['c'][0]).split(' ')
        res['aux'] = 'être' if parts[0] == 'est' else 'avoir'
        res['pp'] = parts[-1]
    out[inf] = res

if 'falloir' in out:
    only_il = lambda f: [None, None, f, None, None, None]  # noqa: E731
    out['falloir']['t'] = {
        'present': only_il('faut'), 'imparfait': only_il('fallait'), 'futur': only_il('faudra'),
        'conditionnel': only_il('faudrait'), 'subjonctif': only_il('faille'),
    }

json.dump(out, open('data/conj.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(out), 'verbs')
for v in ['être', 'avoir', 'aller', 'pouvoir', 'falloir', 'venir', 'mourir', 'faire']:
    print(v, out.get(v))
