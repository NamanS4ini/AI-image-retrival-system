import re

from clip_model import get_text_embedding, get_text_embeddings


QUERY_TOKEN = re.compile(r'(?<!\S)(?:"[^"]*"|-"[^"]*"(?=\s|$)|\S+)')
EXCLUSION_THRESHOLD = 0.20
EXCLUSION_WEIGHT = 0.85


def parse_text_query(query):
    """Split a text query into its positive text and excluded words or phrases."""
    exclusions = []

    def collect_exclusion(match):
        token = match.group()
        if token == "-" or not token.startswith("-"):
            return token
        if token.startswith('-"'):
            if len(token) < 3 or not token.endswith('"') or '"' in token[2:-1]:
                raise ValueError('Close the excluded phrase with double quotes, like -"white hat".')
            term = token[2:-1].strip()
            if not term:
                raise ValueError("Enter a word or phrase to exclude.")
        else:
            term = token[1:]
        exclusions.append(term)
        return ""

    positive = QUERY_TOKEN.sub(collect_exclusion, query).strip()
    if not positive:
        raise ValueError("Enter what to look for before adding an exclusion.")
    if exclusions:
        positive = " ".join(positive.split())
    return positive, tuple(dict.fromkeys(exclusions))


def query_embeddings(positive, exclusions):
    if not exclusions:
        return get_text_embedding(positive), None
    embeddings = get_text_embeddings([positive, *exclusions])
    return embeddings[:1], embeddings[1:]


def score_media(query_features, media_features, excluded_features=None):
    """Apply a soft penalty for the strongest excluded concept on each image."""
    scores = (query_features @ media_features.T).squeeze(0)
    if excluded_features is not None:
        strongest_match = (excluded_features @ media_features.T).amax(dim=0)
        penalty = (strongest_match - EXCLUSION_THRESHOLD).clamp_min(0) * EXCLUSION_WEIGHT
        scores = scores - penalty
    return scores
