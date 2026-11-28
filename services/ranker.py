from io import BytesIO
from PIL import Image
import requests

from clip_model import get_image_embedding
from services.text_query import query_embeddings, score_media


def rank_images(query, images, top_n=15, *, exclusions=()):
    """Rank online candidates against a text query."""
    if not images:
        return []
    features, excluded_features = query_embeddings(query, exclusions)
    return rank_image_candidates(features, images, top_n, excluded_features=excluded_features)


def rank_image_candidates(query_features, images, top_n=15, *, excluded_features=None):
    """Rank downloaded candidates against an embedding from either encoder."""
    ranked = []

    for image_data in images:
        try:
            response = requests.get(image_data["url"], timeout=5)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGB")

            image_features = get_image_embedding(image)
            similarity = score_media(query_features, image_features, excluded_features).item()

            image_data["score"] = similarity
            ranked.append(image_data)

        except Exception as error:
            print(f"Skipping image: {error}")

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_n]
