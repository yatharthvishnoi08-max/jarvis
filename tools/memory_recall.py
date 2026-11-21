"""Bounded, local keyword retrieval. No hosted index or embedding calls required.

BM25 is a first retrieval layer, not semantic understanding. Owner-pinned facts
form a small profile; other facts must match the current request or recent context.
"""
import math
import re
from collections import Counter
from tools.memory_store import list_memories

STOP_WORDS = set('a an and are as at be been but by can could did do does for from had has have how i if in is it its me my of on or our please should that the their them there these they this to us was we were what when where which who will with would you your jarvis remember memory memories know tell about'.split())
MAX_CONTEXT_CHARS = 5000


def terms(text):
    return [word for word in re.findall(r'[^\W_]+', text.casefold()) if len(word) > 1 and word not in STOP_WORDS]


def recall(query: str, recent_context: str = ''):
    records = list_memories()
    documents = [Counter(terms(r['rule'])) for r in records]
    current = set(terms(query[:2000]))
    recent = set(terms(recent_context[-1000:])) - current
    wanted = current | recent
    frequency = Counter(word for document in documents for word in document)
    average = sum(sum(doc.values()) for doc in documents) / max(1, len(documents)) or 1
    ranked = []
    for record, document in zip(records, documents):
        score = 0.0
        length = sum(document.values())
        for word in wanted & document.keys():
            count = document[word]
            inverse = math.log(1 + (len(records) - frequency[word] + .5) / (frequency[word] + .5))
            score += inverse * count * 2.2 / (count + 1.2 * (.25 + .75 * length / average)) * (1 if word in current else .25)
        if score > 0 and not record['pinned']:
            ranked.append((score, record))
    ranked.sort(key=lambda pair: (pair[0], pair[1]['updated_at'], pair[1]['id']), reverse=True)
    pinned = [r for r in records if r['pinned']]
    selected, lines = [], []
    used = 0

    def include(record, kind, budget):
        nonlocal used
        label = f"[{kind} memory #{record['id']}; updated {record['updated_at'][:10]}] "
        available = min(1000, budget - len(label) - 1)
        if available < 80:
            return 0
        text = record['rule']
        start = 0
        if kind == 'Relevant' and len(text) > available:
            matches = [m for m in re.finditer(r'[^\W_]+', text) if m.group().casefold() in wanted]
            if matches:
                start = max(0, matches[0].start() - 100)
        excerpt = text[start:start + available - 6]
        if start:
            excerpt = '… ' + excerpt
        if start + available - 6 < len(text):
            excerpt += ' …'
        line = label + excerpt
        lines.append(line)
        selected.append({'id': record['id'], 'kind': kind, 'excerpt': excerpt})
        amount = len(line) + 1
        used += amount
        return amount

    profile_used = 0
    for record in pinned:
        profile_used += include(record, 'Core', 1500 - profile_used)
    for _, record in ranked[:6]:
        include(record, 'Relevant', MAX_CONTEXT_CHARS - used)
    context = '\n'.join(lines) or '(No relevant saved memories.)'
    return {'context': context, 'selected': selected, 'characters': len(context),
            'limit': MAX_CONTEXT_CHARS, 'method': 'local_keyword', 'active_count': len(records)}
