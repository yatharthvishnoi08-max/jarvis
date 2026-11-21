"""Keep recent complete turns and the current tool chain without changing saved history."""
import copy
import json


def model_window(messages, max_chars=24000, max_turns=6):
    system = [copy.deepcopy(m) for m in messages if m['role'] == 'system']
    turns = []
    for message in messages:
        if message['role'] == 'system':
            continue
        if message['role'] == 'user' or not turns:
            turns.append([])
        turns[-1].append(copy.deepcopy(message))
    if not turns:
        return system
    # Preserve call IDs, arguments and provider signatures exactly. Only tool
    # result prose is excerpted; complete originals remain in the saved session.
    for group in turns:
        for message in group:
            content = message.get('content')
            if message['role'] == 'tool' and isinstance(content, str) and len(content) > 6000:
                message['content'] = content[:4500] + '\n[Tool output excerpt: middle omitted; full result is saved. Inspect the source again if needed.]\n' + content[-1400:]
    selected = [turns[-1]]
    used = len(json.dumps(selected, ensure_ascii=False))
    for group in reversed(turns[:-1]):
        size = len(json.dumps(group, ensure_ascii=False))
        if len(selected) >= max_turns or used + size > max_chars:
            break
        selected.insert(0, group)
        used += size
    omitted = len(turns) - len(selected)
    if omitted:
        notice = (f'\nConversation context: {omitted} older turns are outside this request window. '
                  'The complete conversation is still saved. Do not invent omitted details or repeat '
                  'earlier actions without checking their actual state. Use relevant personal memory; '
                  'ask for a missing detail when necessary.')
        if system:
            system[0]['content'] += notice
        else:
            system = [{'role':'system', 'content':notice.strip()}]
    # The active turn is never dropped to satisfy a size target: this avoids
    # splitting tool batches or losing the current instruction during long tasks.
    return system + [message for group in selected for message in group]
