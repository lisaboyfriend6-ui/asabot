import difflib

def smart_search(query, data):
    query = query.lower().strip()

    results = []

    for s in data:
        name = s["command"].lower()

        score = difflib.SequenceMatcher(None, query, name).ratio() * 3

        if query in name or name in query:
            score += 2

        results.append((score, s))

    results.sort(reverse=True, key=lambda x: x[0])
    return results