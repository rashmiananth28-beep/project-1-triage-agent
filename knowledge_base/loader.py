import json
import os

# Words that add no search value - we ignore these
STOP_WORDS = {
    "i", "a", "an", "the", "is", "am", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "to", "of", "in", "on", "at",
    "for", "with", "about", "by", "from", "up", "into", "not", "no", "so",
    "my", "we", "our", "it", "its", "this", "that", "and", "or", "but",
    "user", "please", "help", "issue", "problem", "getting", "using", "since",
    "still", "also", "just", "when", "how", "what", "why", "where", "which"
}

def load_kb():
    """Load knowledge base from JSON file"""
    kb_path = os.path.join(os.path.dirname(__file__), "kb.json")
    with open(kb_path, 'r') as f:
        return json.load(f)

def search_kb(query: str, top_k: int = 3, min_score: int = 1) -> list:
    """
    Search knowledge base using scored word-by-word matching.
    
    Each KB entry is scored based on how many query words match
    its issue text, tags, and category. Returns top matches.

    Args:
        query: The search query (ticket title + description)
        top_k: Maximum number of results to return
        min_score: Minimum score to include a result (filters weak matches)

    Returns:
        List of matching resolutions sorted by relevance score
    """
    kb = load_kb()

    # Clean and split query into meaningful words
    query_words = [
        word.strip(".,!?;:'\"").lower()
        for word in query.split()
        if word.lower() not in STOP_WORDS and len(word) > 2
    ]

    if not query_words:
        return []

    scored_results = []

    for resolution in kb["resolutions"]:
        score = 0
        matched_words = []

        # Build searchable text for this KB entry
        issue_text = resolution["issue"].lower()
        category_text = resolution["category"].lower()
        tags = [tag.lower() for tag in resolution["tags"]]
        solution_text = resolution["solution"].lower()

        for word in query_words:
            # Issue title match = highest value (3 points)
            if word in issue_text:
                score += 3
                matched_words.append(f"{word}(issue)")

            # Tag match = high value (2 points)
            elif any(word in tag or tag in word for tag in tags):
                score += 2
                matched_words.append(f"{word}(tag)")

            # Category match = medium value (1 point)
            elif word in category_text:
                score += 1
                matched_words.append(f"{word}(category)")

            # Solution text match = low value (1 point)
            elif word in solution_text:
                score += 1
                matched_words.append(f"{word}(solution)")

        # Only include results that meet minimum score
        if score >= min_score:
            scored_results.append({
                "score": score,
                "matched_words": matched_words,
                **resolution
            })

    # Sort by score descending, return top_k
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    top_results = scored_results[:top_k]

    # Print what was found (helpful for debugging)
    if top_results:
        print(f"   KB Search: '{' '.join(query_words[:5])}...'")
        for r in top_results:
            print(f"   ✅ Matched: [{r['id']}] {r['issue']} (score: {r['score']}, words: {r['matched_words']})")
    else:
        print(f"   KB Search: No matches found for words: {query_words}")

    return top_results