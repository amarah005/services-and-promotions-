from typing import Dict, List, Tuple


# Focused, safe synonyms (do NOT expand to entire category groups)
SYNONYMS: Dict[str, List[str]] = {
    'ac': ['air conditioner', 'a/c', 'cooling'],
    'led': ['tv', 'television', 'led tv', 'smart tv'],
    'television': ['tv', 'led', 'led tv', 'smart tv'],
    'tv': ['television', 'led tv', 'smart tv'],
    'cell': ['mobile', 'phone', 'smartphone'],
    'fridge': ['refrigerator'],
    'ref': ['refrigerator', 'fridge'],
    'wm': ['washing machine'],
    'micro': ['microwave'],
    'handfree': ['earphones', 'handsfree', 'ear buds'],
    # Audio precise mappings
    'headphones': ['headphone', 'headset', 'earphone', 'earphones', 'earbuds'],
    'earphone': ['earphones', 'headphone', 'headphones', 'earbuds'],
    'earbuds': ['earbud', 'headphones', 'headset'],
    'bluetooth': ['wireless', 'bt'],
}


def expand_query_synonyms(query: str) -> List[str]:
    """Expand a query string into tokens including simple synonyms."""
    tokens = [t.strip() for t in query.lower().replace('-', ' ').split() if t.strip()]
    expanded: List[str] = []
    for token in tokens:
        expanded.append(token)
        for key, alts in SYNONYMS.items():
            if token == key:
                expanded.extend(alts)
    # Preserve uniqueness while keeping order
    seen = set()
    ordered: List[str] = []
    for t in expanded:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered or tokens


def build_token_groups(query: str) -> List[List[str]]:
    """Return a list of token groups for AND logic with synonyms per token.

    Example: "i7 laptop" -> [["i7"], ["laptop"]]
             "tv" -> [["tv", "television", "led tv", "smart tv"]]
    """
    tokens = [t.strip() for t in query.lower().replace('-', ' ').split() if t.strip()]
    groups: List[List[str]] = []
    for t in tokens:
        group: List[str] = []
        # For very short tokens (e.g., 'ac'), avoid using the raw token to reduce noise.
        # Only use meaningful synonyms (length >= 3).
        if len(t) >= 3:
            group.append(t)
        if t in SYNONYMS:
            for alt in SYNONYMS[t]:
                if len(alt) >= 3:
                    group.append(alt)
        # If the group is still empty (all too short), keep the original token as last resort
        if not group:
            group.append(t)
        # De-duplicate within group
        seen = set()
        uniq: List[str] = []
        for g in group:
            if g not in seen:
                seen.add(g)
                uniq.append(g)
        groups.append(uniq)
    return groups


def parse_query_filters(query: str) -> Dict[str, List[str]]:
    """Very simple parser to extract potential brand/model/spec tokens.

    Returns a dict like {'brands': [...], 'models': [...], 'numbers': [...]}
    """
    import re
    tokens = [t for t in re.split(r"\s+", query.strip()) if t]
    numbers = [t for t in tokens if re.fullmatch(r"(\d+(?:\.\d+)?)(?:\"|in|gb|ton|w|hz)?", t.lower())]
    models = [t for t in tokens if re.search(r"\d", t) and len(t) <= 12]
    brands: List[str] = []  # Optionally populate from known brands table at runtime
    return {
        'brands': brands,
        'models': models,
        'numbers': numbers,
    }


