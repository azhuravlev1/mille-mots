import json, os

words = json.load(open('data/words.json', encoding='utf-8'))
os.makedirs('data/chunks', exist_ok=True)
by = {}
for w in words:
    by.setdefault(w['section'], []).append(w)


def line(w):
    f = w.get('forms') or {}
    extra = ' | '.join(f'{k}={v}' for k, v in f.items() if v)
    also = f" | also-tagged-as={','.join(w['also'])}" if w['also'] else ''
    return f"{w['lemma']} | {w['cgram']}{' | ' + extra if extra else ''}{also}"


plan = {
    'nouns1': by['noun'][:140], 'nouns2': by['noun'][140:280], 'nouns3': by['noun'][280:],
    'verbs1': by['verb'][:150], 'verbs2': by['verb'][150:],
    'adj_adv': by['adj'] + by['adv'],
    'other': by['other'],
}
for name, ws in plan.items():
    with open(f'data/chunks/{name}.txt', 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(line(w) for w in ws) + '\n')
    print(name, len(ws))
