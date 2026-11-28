from functools import lru_cache

from clip_model import get_text_embeddings


PHOTO_TOPICS = (
    "mountain landscape", "sunset sky", "forest", "waterfall", "beach",
    "ocean", "desert", "lake", "snowy landscape", "thunderstorm",
    "night sky", "city skyline", "city street", "building exterior",
    "home interior", "garden", "flower", "tree", "insect",
    "dog", "cat", "bird", "horse", "wildlife", "farm animal",
    "food", "fruit", "coffee", "portrait", "group of people",
    "child playing", "people exercising", "sports game", "running",
    "bicycle", "car", "train", "airplane", "sailboat",
    "computer", "office workspace", "books", "clothing", "shoes",
    "music instrument", "hand tools", "abstract pattern",
)


@lru_cache(maxsize=1)
def topic_embeddings():
    return get_text_embeddings([f"a photo of {topic}" for topic in PHOTO_TOPICS])


def suggest_photo_keywords(image_features):
    """Select a stock-photo search topic using CLIP zero-shot classification."""
    topic_scores = image_features @ topic_embeddings().T
    return PHOTO_TOPICS[topic_scores.argmax().item()]
