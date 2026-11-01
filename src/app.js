(function () {
  'use strict';
  const D = JSON.parse(document.getElementById('data').textContent);
  const P = D.patterns;
  const app = document.getElementById('app');
  const $ = (id) => document.getElementById(id);

  const SECTIONS = [
    { id: 'noun', title: 'Nouns', fr: 'les noms' },
    { id: 'verb', title: 'Verbs', fr: 'les verbes' },
    { id: 'adj', title: 'Adjectives', fr: 'les adjectifs' },
    { id: 'adv', title: 'Adverbs', fr: 'les adverbes' },
    { id: 'other', title: 'Other words', fr: 'les mots-outils' },
  ];
  const SIM = [
    ['same', 'Identical to English', 'Same spelling, same meaning: free vocabulary.'],
    ['close', 'Almost like English', 'Spelled a little differently, meaning very close.'],
    ['faux', 'Faux amis', 'Look English, but the meaning shifted. Watch out.'],
    ['ru', 'Like Russian', 'No English hook, but a Russian one.'],
    ['none', 'No shortcut', 'Nothing to lean on; these just need learning.'],
  ];
  const SIM_BADGE = { same: ['EN =', 'Same as English'], close: ['EN ≈', 'Close to English'], faux: ['faux ami', 'False friend'], ru: ['RU ≈', 'Similar to Russian'] };
  const SECTION_INTRO = {
    noun: 'Grouped by how much English or Russian helps. Derived nouns have the suffix that built them underlined; every distinct suffix has its own colour. Irregular plurals and feminines are highlighted too.',
    verb: 'Pronouns on top, one row per tense; the header gives the passé composé recipe (auxiliary + participle). The usual endings (-e/-s, -es/-s, -e/-t, -ons, -ez, -ent…) stay plain; anything else is underlined in colour, and a coloured box marks an ending that is missing. Dotted underline = the stem itself changed.',
    adj: 'Grouped by where the adjective comes from. Derivation suffixes are always underlined. For gender/number, the normal +e / +s stays plain; every other change gets its own colour.',
    adv: 'The normal recipe is feminine adjective + -ment (lente → lentement), left plain. Deviations are coloured; the box marks a missing feminine -e. The remaining adverbs are grouped by what they express.',
    other: 'The glue of the language: articles, determiners, pronouns, prepositions, conjunctions, numbers.',
  };
  const TENSES = [
    ['present', 'présent'], ['pc', 'passé c.'], ['imparfait', 'imparfait'],
    ['futur', 'futur'], ['conditionnel', 'condit.', true], ['subjonctif', 'subj.', true],
  ];
  const AUX = {
    avoir: ['ai', 'as', 'a', 'avons', 'avez', 'ont'],
    'être': ['suis', 'es', 'est', 'sommes', 'êtes', 'sont'],
  };
  const ADV_GRP = [
    ['time', 'Time', 'when?'], ['place', 'Place', 'where?'], ['manner', 'Manner', 'how?'],
    ['degree', 'Degree & quantity', 'how much?'], ['negation', 'Negation', ''],
    ['affirmation', 'Affirmation & doubt', ''], ['question', 'Question words', ''], ['linking', 'Linking & sequencing', ''],
  ];
  const ADJ_ORIGIN = [
    ['base', 'Basic adjectives', 'Not formed from another word.'],
    ['noun', 'Formed from a noun', 'noun + suffix'],
    ['verb', 'Formed from a verb', 'mostly participles: -é, -i, -u, -ant, or -able'],
    ['other', 'Other formations', 'prefixes (in-, im-…) or from other adjectives'],
  ];
  const OTHER_CLS = [
    ['article', 'Articles'], ['determiner', 'Determiners'], ['pronoun', 'Pronouns'],
    ['preposition', 'Prepositions'], ['conjunction', 'Conjunctions'], ['number', 'Numbers'], ['interjection', 'Interjections & set phrases'],
  ];
  const GROUP_OPTIONS = {
    noun: [['sim', 'similarity'], ['suffix', 'suffix'], ['gender', 'gender'], ['flat', 'no groups']],
    verb: [['sim', 'similarity'], ['type', 'conjugation type'], ['flat', 'no groups']],
    adj: [['origin', 'formation'], ['sim', 'similarity'], ['flat', 'no groups']],
    adv: [['origin', 'formation / meaning'], ['sim', 'similarity'], ['flat', 'no groups']],
    other: [['cls', 'word class'], ['flat', 'no groups']],
  };

  const PHONE = window.matchMedia('(max-width: 760px)').matches;
  // Long keys start collapsed on phones (except in print view, where everything is shown).
  const keyOpen = () => (state.mode === 'print' || !PHONE ? ' open' : '');
  const store = {
    get(k, d) { try { const v = localStorage.getItem('mm:' + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('mm:' + k, JSON.stringify(v)); } catch (e) { /* private mode */ } },
  };
  const state = {
    mode: store.get('mode', PHONE ? 'learn' : 'print'),
    groupBy: store.get('groupBy', {}),
    sort: store.get('sort', 'rank'),
    quiz: false, hideKnown: store.get('hideKnown', false), q: '', pat: null,
  };
  const known = new Set(store.get('known', []));

  // ---------------------------------------------------------------- helpers
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const pstyle = (id) => `--c:${P[id].color};--s:${P[id].style}`;
  const ptitle = (id) => esc(`${P[id].label}: ${P[id].desc}`);

  function segs(list) {
    if (!list) return '';
    return list.map(([t, m]) => {
      if (m === '') return esc(t);
      if (m === '~') return `<span class="stem" title="stem change">${esc(t)}</span>`;
      if (t === '') return `<span class="hl gap" data-p="${m}" style="${pstyle(m)}" title="${ptitle(m)}"></span>`;
      const whole = list.length === 1 ? ' whole' : '';
      return `<span class="hl${whole}" data-p="${m}" style="${pstyle(m)}" title="${ptitle(m)}">${esc(t)}</span>`;
    }).join('');
  }
  const segText = (list) => (list || []).map((s) => s[0]).join('');
  const hasStemChange = (e) => e.t && Object.values(e.t).some((row) => row.some((c) => c && c.some((s) => s[1] === '~')));

  function badge(e) {
    const b = SIM_BADGE[e.sim];
    return b ? `<span class="badge b-${e.sim}" title="${b[1]}">${b[0]}</span>` : '';
  }

  // Pronunciation respelling. Easy sounds are spelled with English letters; the marked
  // symbols (ü eu ã õ ẽ r) are French-only sounds explained in the key.
  const KEY_EASY = [
    ['a', 'cat / а'], ['ee', 'see / и'], ['ay', 'day, but short, no glide / э in «эти»'], ['eh', 'bed / э'],
    ['oh', 'go, no w-glide / о'], ['o', 'British hot'], ['oo', 'food / у'], ['uh', 'the / unstressed а in «молоко»'],
    ['ahy', 'eye'], ['y', 'yes / й'], ['w', 'we'], ['sh', 'ship / ш'], ['zh', 'measure / ж'], ['ny', 'canyon / нь'],
    ['g', 'always hard: go'], ['s', 'always as in see'],
  ];
  const KEY_SPECIAL = [
    ['ü', 'u: say "ee" with lips rounded as for "oo" (German ü, close to Russian ю in «тюль»). Before a vowel it is a quick glide: huit = üeet'],
    ['eu', 'eu / œu: "uh" with rounded lips, like British fur / bird without the r'],
    ['ã', 'an / en: "ah" through the nose; the n is not pronounced (like aunt said nasally)'],
    ['õ', 'on: "oh" through the nose (like song without finishing the ng)'],
    ['ẽ', 'in / ain / ein / un: "eh" through the nose (like the a in American bank without the n)'],
    ['r', 'French r: in the back of the throat, a voiced version of Russian х; never the English r'],
  ];
  const PR_TITLE = 'Respelling. Stress is always on the last syllable. ' +
    KEY_SPECIAL.map(([k, d]) => `${k} = ${d}`).join('; ');
  function pr(e) {
    if (!e.pr) return '';
    const marked = esc(e.pr).replace(/eu|[üãõẽ]/g, (m) => `<b>${m}</b>`);
    return `<span class="pr" title="${esc(PR_TITLE)}">[${marked}]</span>`;
  }
  function prKey() {
    return `<details class="prkey"${keyOpen()}><summary class="prkey-title">Pronunciation key <span class="ln">— respelling in [brackets]; stress always falls on the last syllable</span></summary>
      <div class="prkey-cols"><div>${KEY_EASY.map(([k, d]) => `<span class="pk"><b>${k}</b> ${esc(d)}</span>`).join('')}</div>
      <div class="prkey-special">${KEY_SPECIAL.map(([k, d]) => `<div class="pk sp"><b>${k}</b> ${esc(d)}</div>`).join('')}</div></div></details>`;
  }
  function elide(article, w) {
    return /^[aeiouyéèêàâîôûœh]/i.test(w) ? "l'" + w : article + ' ' + w;
  }
  function more(e, extra) {
    const out = [];
    if (e.faux) out.push(`<span class="faux">⚠ ${esc(e.faux)}</span>`);
    if (extra) out.push(...extra);
    if (e.note) out.push(`<span class="note">${esc(e.note)}</span>`);
    if (e.pron) out.push(`<span class="pron">${esc(e.pron)}</span>`);
    if (e.ru) out.push(`<span class="ru">RU: ${esc(e.ru)}</span>`);
    if (e.ru_like && e.sim === 'ru') out.push(`<span class="rulike">≈ ${esc(e.ru_like)}</span>`);
    else if (e.ru_like) out.push(`<span class="rulike ext">≈ RU ${esc(e.ru_like)}</span>`);
    if (e.der && e.der.from) out.push(`<span class="der">← ${esc(e.der.from)}${e.der.fromPos ? ' (' + esc(e.der.fromPos) + ')' : ''}</span>`);
    if (e.ex) out.push(`<span class="ex">${esc(e.ex)}</span>`);
    return out.length ? `<div class="more">${out.join('')}</div>` : '';
  }
  function wrap(e, cls, inner) {
    const search = [e.w, e.lem, e.en, e.ru, e.note].filter(Boolean).join(' ').toLowerCase();
    return `<div class="entry ${cls} sim-${e.sim}${known.has(e.lem + '|' + cls) ? ' known' : ''}" data-k="${esc(e.lem + '|' + cls)}" data-pats="${e.pats.join(' ')}" data-s="${esc(search)}">` +
      `<button class="known-btn" title="I know this word">✓</button>${inner}</div>`;
  }
  const rank = (e) => `<span class="rank" title="frequency rank">#${e.rank}</span>`;

  // ---------------------------------------------------------------- entry renderers
  function nounEntry(e) {
    const g = e.g || '';
    const gcls = g === 'm' ? 'g-m' : g === 'f' ? 'g-f' : 'g-mf';
    const glabel = g === 'm|f' ? 'm/f*' : (g || '?');
    const say = g === 'f' ? elide('la', e.w) : elide('le', e.w);
    const extra = [];
    let hw = `<span class="g ${gcls}" title="${g === 'm|f' ? 'gender changes the meaning' : 'gender'}">${esc(glabel)}</span> <span class="fw say" data-say="${esc(say)}">${segs(e.head)}</span>${pr(e)}`;
    if (e.pl) hw += ` <span class="tag">pl.</span> <span class="fw">${segs(e.pl)}</span>`;
    if (e.fem) hw += ` <span class="tag">f.</span> <span class="fw">${segs(e.fem)}</span>`;
    hw += ' ' + badge(e) + rank(e);
    return wrap(e, 'noun', `<div class="hw">${hw}</div><div class="tr">${esc(e.en)}</div>${more(e, extra)}`);
  }

  function verbEntry(e) {
    const persons = D.persons;
    let head = `<div class="vhead hw"><span class="fw say" data-say="${esc(e.w)}">${segs(e.head)}</span>${pr(e)} <span class="tr">${esc(e.en)}</span> ${badge(e)}`;
    if (e.pp && e.pp.length) {
      head += `<span class="aux"><b>${esc(e.aux)}</b> + <b>${segs(e.pp)}</b></span>`;
    }
    head += rank(e) + '</div>';
    let rows = '';
    const auxName = (e.aux || 'avoir').startsWith('être') ? 'être' : 'avoir';
    for (const [key, label, ext] of TENSES) {
      let cells;
      if (key === 'pc') {
        if (!e.pp || !e.pp.length) continue;
        const onlyIl = e.t && e.t.present && e.t.present.filter(Boolean).length === 1;
        cells = AUX[auxName].map((a, i) => {
          if (onlyIl && i !== 2) return '<td></td>';
          const agr = auxName === 'être' ? `<span class="agr">${i < 3 ? '(e)' : '(e)s'}</span>` : '';
          return `<td><span class="aux-f">${a}</span> ${segs(e.pp)}${agr}</td>`;
        });
      } else {
        const row = (e.t && e.t[key]) || [];
        cells = [0, 1, 2, 3, 4, 5].map((i) => `<td>${row[i] ? segs(row[i]) : ''}</td>`);
      }
      rows += `<tr class="${ext ? 'ext' : ''} r-${key}"><th class="rl">${label}</th>${cells.join('')}</tr>`;
    }
    const table = `<div class="conj-wrap"><table class="conj"><thead><tr><th class="rl"></th>${persons.map((p) => `<th>${p}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;
    return wrap(e, 'verb', head + more(e) + table);
  }

  function adjEntry(e) {
    const f = e.forms || {};
    const before = e.before ? ' <span class="tag" title="usually placed before the noun">before noun</span>' : '';
    const hw = `<span class="fw say" data-say="${esc(e.w)}">${segs(e.head)}</span>${pr(e)} ${badge(e)}${before}${rank(e)}`;
    const cell = (k, l) => `<span><span class="fl">${l}</span><span>${segs(f[k])}</span></span>`;
    const forms = `<div class="forms4">${cell('ms', 'm.')}${cell('fs', 'f.')}${cell('mp', 'm.pl')}${cell('fp', 'f.pl')}</div>`;
    return wrap(e, 'adj', `<div class="hw">${hw}</div>${forms}<div class="tr">${esc(e.en)}</div>${more(e)}`);
  }

  function advEntry(e) {
    const hw = `<span class="fw say" data-say="${esc(e.w)}">${segs(e.head)}</span>${pr(e)} ${badge(e)}${rank(e)}`;
    return wrap(e, 'adv', `<div class="hw">${hw}</div><div class="tr">${esc(e.en)}</div>${more(e)}`);
  }

  function otherEntry(e) {
    let hw;
    const f = e.forms;
    if (f) {
      const ms = f.ms2 ? `${f.ms}<span class="sep">/</span>${f.ms2}` : esc(f.ms);
      const parts = [ms];
      if (f.fs && f.fs !== f.ms) parts.push(esc(f.fs));
      if (f.mp && f.mp !== f.fs) parts.push(esc(f.mp));
      if (f.fp && f.fp !== f.mp) parts.push(esc(f.fp));
      hw = `<span class="para say" data-say="${esc([f.ms, f.fs, f.mp].join(', '))}">${parts.join('<span class="sep">·</span>')}</span>`;
    } else {
      hw = `<span class="fw say" data-say="${esc(e.w)}">${segs(e.head)}</span>`;
    }
    hw += pr(e) + ' ' + badge(e) + rank(e);
    return wrap(e, 'other', `<div class="hw">${hw}</div><div class="tr">${esc(e.en)}</div>${more(e)}`);
  }

  const RENDER = { noun: nounEntry, verb: verbEntry, adj: adjEntry, adv: advEntry, other: otherEntry };

  // ---------------------------------------------------------------- Montréal travel course
  const ROLE = { say: ['say', 'You say it'], hear: ['hear', "You'll hear it"], see: ['sign', "You'll see it written"] };
  const MTL = { id: 'mtl', title: 'Montréal', fr: 'guide de voyage' };
  function mtlWrap(it, kind, inner) {
    const k = 'mtl|' + it.f;
    const search = [it.f, it.e, it.n].filter(Boolean).join(' ').toLowerCase();
    return `<div class="entry mtl-${kind}${known.has(k) ? ' known' : ''}" data-k="${esc(k)}" data-pats="" data-s="${esc(search)}">` +
      `<button class="known-btn" title="I know this">✓</button>${inner}</div>`;
  }
  const qcBadge = (it) => (it.qc ? '<span class="badge b-qc" title="Québec usage">QC</span>' : '');
  const fauxBadge = (it) => (it.faux ? '<span class="badge b-faux" title="False friend">faux ami</span>' : '');
  const sayText = (s) => s.replace(/\[[^\]]*\]/g, '').replace(/[·/]/g, ',');
  function mtlWord(it) {
    const prs = it.pr ? `<span class="pr">[${esc(it.pr).replace(/eu|[üãõẽ]/g, (m) => `<b>${m}</b>`)}]</span>` : '';
    const hw = `<span class="fw say" data-say="${esc(sayText(it.f))}">${esc(it.f)}</span>${prs} ${qcBadge(it)}${fauxBadge(it)}`;
    const more = it.n ? `<div class="more"><span class="note">${esc(it.n)}</span></div>` : '';
    return mtlWrap(it, 'word', `<div class="hw">${hw}</div><div class="tr">${esc(it.e)}</div>${more}`);
  }
  function mtlPhrase(it) {
    const [label, title] = ROLE[it.r] || ROLE.say;
    const hw = `<span class="role r-${label}" title="${title}">${label}</span><span class="fp say" data-say="${esc(sayText(it.f))}">${esc(it.f)}</span> ${qcBadge(it)}`;
    const more = it.n ? `<div class="more"><span class="note">${esc(it.n)}</span></div>` : '';
    return mtlWrap(it, 'phrase', `<div class="hw">${hw}</div><div class="tr">${esc(it.e)}</div>${more}`);
  }
  function montrealHTML() {
    const scen = D.montreal || [];
    let html = `<section class="section mtl" id="mtl"><div class="sec-head"><h2>${MTL.title}</h2><span class="fr">${MTL.fr}</span><span class="count">${D.stats.mtl} words &amp; phrases</span></div>`;
    html += `<p class="sec-intro">A quick course for the trip: the words, the things you'll need to say, the announcements and replies you'll hear, and the signs you'll see. <span class="role r-say">say</span> <span class="role r-hear">hear</span> <span class="role r-sign">sign</span> <span class="badge b-qc">QC</span> = Québec usage.<span class="ext"> Tap any word or phrase to hear it.</span></p>`;
    html += `<div class="mtl-jump">${scen.map((s) => `<a href="#mtl-${s.id}">${esc(s.title)}</a>`).join('')}</div>`;
    for (const s of scen) {
      html += `<div class="group mtl-scen" id="mtl-${s.id}"><div class="group-head"><h3>${esc(s.title)}</h3><span class="gdesc">${esc(s.sub || '')}</span></div>`;
      html += `<p class="mtl-intro">${esc(s.intro)}</p>`;
      if (s.tips && s.tips.length) html += `<ul class="mtl-tips">${s.tips.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>`;
      for (const b of s.blocks) {
        const render = b.kind === 'words' ? mtlWord : mtlPhrase;
        html += `<div class="subgroup-head">${esc(b.title)}</div><div class="entries ${b.kind === 'words' ? '' : 'phrases'}">${b.items.map(render).join('')}</div>`;
      }
      html += '</div>';
    }
    return html + '</section>';
  }

  // ---------------------------------------------------------------- grouping
  function sorted(list) {
    const l = list.slice();
    if (state.sort === 'alpha') l.sort((a, b) => a.w.localeCompare(b.w, 'fr'));
    else l.sort((a, b) => a.rank - b.rank);
    return l;
  }
  function bySim(list) {
    return SIM.map(([k, t, d]) => ({ title: t, desc: d, items: list.filter((e) => e.sim === k) }));
  }
  function verbType(e) {
    if (e.lem === 'aller') return 'irr';
    const irregular = e.pats.length || hasStemChange(e);
    if (!irregular && e.lem.endsWith('er')) return 'er';
    if (!irregular && e.lem.endsWith('ir')) return 'ir';
    return irregular ? 'irr' : 'other';
  }
  function groups(sec, list) {
    const mode = state.mode === 'print' ? GROUP_OPTIONS[sec][0][0] : (state.groupBy[sec] || GROUP_OPTIONS[sec][0][0]);
    if (mode === 'flat') return [{ title: '', items: list }];
    if (mode === 'sim') return bySim(list);
    if (sec === 'noun' && mode === 'suffix') {
      const bucket = {};
      list.forEach((e) => {
        const s = e.der ? (e.der.suffix || (e.der.prefix ? e.der.prefix : '∅')) : '';
        (bucket[s] = bucket[s] || []).push(e);
      });
      return Object.keys(bucket).sort((a, b) => (a === '') - (b === '') || bucket[b].length - bucket[a].length)
        .map((k) => ({ title: k ? k : 'Not derived', desc: k ? `${bucket[k].length} words` : '', items: bucket[k] }));
    }
    if (sec === 'noun' && mode === 'gender') {
      return [['m', 'Masculine'], ['f', 'Feminine'], ['m/f', 'Both genders, same form'], ['m|f', 'Gender changes the meaning']]
        .map(([g, t]) => ({ title: t, items: list.filter((e) => e.g === g) }));
    }
    if (sec === 'verb' && mode === 'type') {
      return [['er', 'Regular -er verbs', 'follow parler: nothing to highlight'],
        ['ir', 'Regular -ir verbs', 'follow finir (-iss- in the plural)'],
        ['irr', 'Irregular or with spelling changes', 'coloured endings, dotted stem changes'],
        ['other', 'Other regular verbs', '']].map(([k, t, d]) => ({ title: t, desc: d, items: list.filter((e) => verbType(e) === k) }));
    }
    if (sec === 'adj') return ADJ_ORIGIN.map(([k, t, d]) => ({ title: t, desc: d, items: list.filter((e) => e.origin === k), cols: true }));
    if (sec === 'adv') {
      const out = [{ title: 'Adverbs in -ment', desc: 'built from an adjective', items: list.filter((e) => e.origin === 'ment') }];
      const rest = list.filter((e) => e.origin !== 'ment');
      ADV_GRP.forEach(([k, t, d]) => out.push({ title: t, desc: d, items: rest.filter((e) => e.grp === k) }));
      const known = new Set(ADV_GRP.map((g) => g[0]));
      out.push({ title: 'Other adverbs', items: rest.filter((e) => !known.has(e.grp)) });
      return out;
    }
    if (sec === 'other') {
      const out = [];
      OTHER_CLS.forEach(([k, t]) => {
        const items = list.filter((e) => e.cls === k);
        const subs = {};
        items.forEach((e) => { (subs[e.sub || ''] = subs[e.sub || ''] || []).push(e); });
        out.push({ title: t, items, subs });
      });
      const knownCls = new Set(OTHER_CLS.map((c) => c[0]));
      out.push({ title: 'Misc', items: list.filter((e) => !knownCls.has(e.cls)) });
      return out;
    }
    return [{ title: '', items: list }];
  }

  // ---------------------------------------------------------------- legend
  const LEGEND_KIND = {
    verb: [['present:', 'Present tense endings'], ['subjonctif:', 'Subjunctive endings'], ['pp:', 'Past participles'], ['pre:', 'Prefixes']],
    noun: [['suf:', 'Suffixes that form nouns'], ['pre:', 'Prefixes'], ['pl:', 'Irregular plurals'], ['fem:', 'Feminine forms']],
    adj: [['suf:', 'Suffixes that form adjectives'], ['pre:', 'Prefixes'], ['fem:', 'Feminine (instead of +e)'], ['pl:', 'Masculine plural (instead of +s)'], ['fpl:', 'Feminine plural']],
    adv: [['', 'Deviations from feminine + -ment']],
  };
  function legend(sec) {
    const ps = P.filter((p) => p.sec === sec).sort((a, b) => b.n - a.n);
    if (!ps.length) return '';
    const kinds = LEGEND_KIND[sec] || [['', '']];
    let html = `<details class="legend"${keyOpen()}><summary class="legend-title">Colour key <span class="ln">(${ps.length} patterns; same colour = same pattern everywhere in this section)</span></summary>`;
    const used = new Set();
    for (const [prefix, title] of kinds) {
      const items = ps.filter((p) => !used.has(p.id) && p.key.startsWith(prefix));
      if (!items.length) continue;
      items.forEach((p) => used.add(p.id));
      if (kinds.length > 1) html += `<div class="legend-sub">${title}</div>`;
      html += '<div class="legend-items">' + items.map(legendItem).join('') + '</div>';
    }
    const rest = ps.filter((p) => !used.has(p.id));
    if (rest.length) html += '<div class="legend-items">' + rest.map(legendItem).join('') + '</div>';
    return html + '</details>';
  }
  function legendItem(p) {
    const isGap = p.key.endsWith('gap') || p.key.endsWith('∅');
    const sample = isGap ? `<span class="hl gap" style="${pstyle(p.id)}"></span>` : `<span class="hl" style="${pstyle(p.id)}">${esc(p.label)}</span>`;
    return `<span class="legend-item${state.pat === p.id ? ' sel' : ''}" data-pid="${p.id}" style="--c:${p.color}"><span class="sample">${sample}</span> ${esc(p.desc)} <span class="lx">${esc(p.ex.slice(0, 3).join(', '))}</span> <span class="ln">×${p.n}</span></span>`;
  }

  // ---------------------------------------------------------------- page
  function intro() {
    const total = Object.values(D.stats).reduce((a, b) => a + b, 0);
    return `<div class="intro"><h1>Mille mots</h1>
      <p class="sub">The ${total} most frequent French words (Lexique 3.83, films + books), sorted by kind and by what makes them easy or tricky.</p>
      <div class="howto">
        <div><span class="badge b-same">EN =</span> <span class="badge b-close">EN ≈</span> identical / close to English</div>
        <div><span class="badge b-faux">faux ami</span> looks English, means something else</div>
        <div><span class="badge b-ru">RU ≈</span> resembles a Russian word</div>
        <div><span class="hl" style="--c:#e6194b">ending</span> coloured underline = unusual ending or suffix; one colour per pattern</div>
        <div>ne<span class="hl gap" style="--c:#4363d8"></span> coloured box = nothing added where an ending is expected</div>
        <div><span class="stem">vien</span>s dotted underline = the stem itself changed</div>
        <div><span class="g g-m">m</span> <span class="g g-f">f</span> <span class="g g-mf">m/f</span> noun gender (m/f* = gender changes the meaning)</div>
        <div><b>RU:</b> Russian gloss, only where it explains the meaning better than English</div>
        <div class="ext">Click a word to hear it · click a colour key to filter · ✓ marks words you know</div>
      </div>${prKey()}</div>`;
  }

  function sectionHTML(sec) {
    const meta = SECTIONS.find((s) => s.id === sec.id);
    const list = sorted(D.sections[sec.id] || []);
    let html = `<section class="section" id="${meta.id}"><div class="sec-head"><h2>${meta.title}</h2><span class="fr">${meta.fr}</span><span class="count">${list.length} words</span></div>`;
    html += `<p class="sec-intro">${SECTION_INTRO[meta.id]}</p>`;
    if (state.mode === 'learn') {
      const opts = GROUP_OPTIONS[meta.id];
      if (opts.length > 1) {
        const cur = state.groupBy[meta.id] || opts[0][0];
        html += `<label class="tgl">Group by <select data-groupby="${meta.id}">${opts.map(([v, l]) => `<option value="${v}"${v === cur ? ' selected' : ''}>${l}</option>`).join('')}</select></label>`;
      }
    }
    html += legend(meta.id);
    const render = RENDER[meta.id];
    const listCls = meta.id === 'verb' ? 'verbs' : meta.id === 'adj' ? 'adjs' : '';
    for (const g of groups(meta.id, list)) {
      if (!g.items.length) continue;
      html += '<div class="group">';
      if (g.title) html += `<div class="group-head"><h3>${esc(g.title)}</h3>${g.desc ? `<span class="gdesc">${esc(g.desc)}</span>` : ''}<span class="gcount">${g.items.length}</span></div>`;
      if (g.cols) html += '<div class="adj-cols"><span>masc. sg.</span><span>fem. sg.</span><span>masc. pl.</span><span>fem. pl.</span><span>notes</span></div>';
      if (g.subs && Object.keys(g.subs).length > 1) {
        for (const [sub, items] of Object.entries(g.subs)) {
          html += `<div class="subgroup-head">${esc(sub || 'other')}</div><div class="entries ${listCls}">${items.map(render).join('')}</div>`;
        }
      } else {
        html += `<div class="entries ${listCls}">${g.items.map(render).join('')}</div>`;
      }
      html += '</div>';
    }
    return html + '</section>';
  }

  function render() {
    document.body.className = 'mode-' + state.mode + (state.quiz && state.mode === 'learn' ? ' quiz' : '');
    const sw = $('modeSwitch');
    sw.dataset.mode = state.mode;
    sw.querySelectorAll('button').forEach((b) => b.classList.toggle('on', b.dataset.mode === state.mode));
    app.innerHTML = intro() + SECTIONS.map(sectionHTML).join('') + montrealHTML();
    applyFilters();
  }

  function applyFilters() {
    const learn = state.mode === 'learn';
    const q = state.q.trim().toLowerCase();
    let shown = 0;
    app.querySelectorAll('.entry').forEach((el) => {
      let ok = true;
      if (learn) {
        if (q && !el.dataset.s.includes(q)) ok = false;
        if (ok && state.pat !== null && !(' ' + el.dataset.pats + ' ').includes(' ' + state.pat + ' ')) ok = false;
        if (ok && state.hideKnown && el.classList.contains('known')) ok = false;
      }
      el.classList.toggle('hidden', !ok);
      if (ok) shown++;
    });
    app.querySelectorAll('.group').forEach((g) => {
      g.classList.toggle('hidden', learn && !g.querySelector('.entry:not(.hidden)'));
    });
    app.querySelectorAll('.subgroup-head').forEach((h) => {
      const list = h.nextElementSibling;
      h.classList.toggle('hidden', learn && list && !list.querySelector('.entry:not(.hidden)'));
    });
    app.querySelectorAll('.hp').forEach((el) => el.classList.remove('hp'));
    if (learn && state.pat !== null) app.querySelectorAll(`.hl[data-p="${state.pat}"]`).forEach((el) => el.classList.add('hp'));
    const pill = $('filterPill');
    if (learn && state.pat !== null) {
      const p = P[state.pat];
      pill.hidden = false;
      pill.innerHTML = `Pattern: <span class="hl" style="${pstyle(p.id)}">${esc(p.label)}</span> ✕`;
    } else pill.hidden = true;
    $('knownCount').textContent = learn ? `${known.size} known · ${shown} shown` : '';
  }

  // ---------------------------------------------------------------- nav + events
  const PAGE_ORDER = [...SECTIONS, MTL];
  $('nav').innerHTML = [MTL, ...SECTIONS].map((s) => `<a href="#${s.id}" data-sec="${s.id}"${s === MTL ? ' class="nav-mtl"' : ''}>${s.title}<small>${D.stats[s.id] || 0}</small></a>`).join('');
  const navLinks = [...document.querySelectorAll('#nav a')];
  const spy = () => {
    let cur = null;
    for (const s of PAGE_ORDER) {
      const el = document.getElementById(s.id);
      if (el && el.getBoundingClientRect().top < 140) cur = s.id;
    }
    navLinks.forEach((a) => a.classList.toggle('active', a.dataset.sec === cur));
  };
  window.addEventListener('scroll', spy, { passive: true });

  $('modeSwitch').addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (!b || b.dataset.mode === state.mode) return;
    const anchor = currentAnchor();
    state.mode = b.dataset.mode;
    store.set('mode', state.mode);
    render();
    if (anchor) document.getElementById(anchor).scrollIntoView({ behavior: 'instant' });
  });
  function currentAnchor() {
    let cur = null;
    for (const s of PAGE_ORDER) {
      const el = document.getElementById(s.id);
      if (el && el.getBoundingClientRect().top < 140) cur = s.id;
    }
    return cur;
  }
  $('printBtn').addEventListener('click', () => window.print());
  let modeBeforePrint = null;
  window.addEventListener('beforeprint', () => {
    if (state.mode !== 'print') { modeBeforePrint = state.mode; state.mode = 'print'; render(); }
  });
  window.addEventListener('afterprint', () => {
    if (modeBeforePrint) { state.mode = modeBeforePrint; modeBeforePrint = null; render(); }
  });

  let searchTimer;
  $('search').addEventListener('input', (ev) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { state.q = ev.target.value; applyFilters(); }, 120);
  });
  $('quiz').addEventListener('change', (ev) => { state.quiz = ev.target.checked; document.body.classList.toggle('quiz', state.quiz); app.querySelectorAll('.reveal').forEach((el) => el.classList.remove('reveal')); });
  $('hideKnown').checked = state.hideKnown;
  $('hideKnown').addEventListener('change', (ev) => { state.hideKnown = ev.target.checked; store.set('hideKnown', state.hideKnown); applyFilters(); });
  $('sort').value = state.sort;
  $('sort').addEventListener('change', (ev) => { state.sort = ev.target.value; store.set('sort', state.sort); render(); });
  $('filterPill').addEventListener('click', () => { state.pat = null; render(); });

  app.addEventListener('change', (ev) => {
    const sel = ev.target.closest('select[data-groupby]');
    if (!sel) return;
    state.groupBy[sel.dataset.groupby] = sel.value;
    store.set('groupBy', state.groupBy);
    render();
    document.getElementById(sel.dataset.groupby).scrollIntoView({ behavior: 'instant' });
  });

  let frVoice = null;
  const pickVoice = () => {
    const vs = window.speechSynthesis ? speechSynthesis.getVoices() : [];
    frVoice = vs.find((v) => v.lang === 'fr-FR' && /Thomas|Amélie|Google/.test(v.name)) || vs.find((v) => v.lang && v.lang.startsWith('fr')) || null;
  };
  if (window.speechSynthesis) { pickVoice(); speechSynthesis.onvoiceschanged = pickVoice; }
  function say(text) {
    if (!window.speechSynthesis) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'fr-FR';
    if (frVoice) u.voice = frVoice;
    u.rate = 0.9;
    speechSynthesis.speak(u);
  }

  app.addEventListener('click', (ev) => {
    if (state.mode !== 'learn') return;
    const kb = ev.target.closest('.known-btn');
    if (kb) {
      const entry = kb.closest('.entry');
      const k = entry.dataset.k;
      if (known.has(k)) known.delete(k); else known.add(k);
      entry.classList.toggle('known', known.has(k));
      store.set('known', [...known]);
      applyFilters();
      return;
    }
    const li = ev.target.closest('.legend-item');
    if (li) {
      const id = +li.dataset.pid;
      state.pat = state.pat === id ? null : id;
      app.querySelectorAll('.legend-item').forEach((el) => el.classList.toggle('sel', +el.dataset.pid === state.pat));
      applyFilters();
      return;
    }
    const s = ev.target.closest('.say');
    if (s) { say(s.dataset.say); }
    const td = ev.target.closest('.conj td');
    if (td && !state.quiz) {
      const th = td.closest('table').querySelectorAll('thead th')[td.cellIndex];
      const pron = th ? th.textContent.split('/')[0] : '';
      const txt = td.textContent.replace(/\(e\)s?/g, '');
      say((/^[aeiouyéèêh]/i.test(txt) && pron === 'je' ? "j'" : pron + ' ') + txt);
    }
    if (state.quiz) {
      const entry = ev.target.closest('.entry');
      if (entry) entry.classList.toggle('reveal');
    }
  });

  app.addEventListener('mouseover', (ev) => {
    const h = ev.target.closest('.hl[data-p]');
    if (!h || state.mode !== 'learn' || state.pat !== null) return;
    const id = h.dataset.p;
    app.querySelectorAll(`.hl[data-p="${id}"]`).forEach((el) => el.classList.add('hp'));
    h.addEventListener('mouseleave', () => {
      if (state.pat === null) app.querySelectorAll('.hp').forEach((el) => el.classList.remove('hp'));
    }, { once: true });
  });

  render();
  if (location.hash) { const t = document.getElementById(location.hash.slice(1)); if (t) t.scrollIntoView(); }
})();
