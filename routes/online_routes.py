from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from clip_model import get_image_embedding
from routes.reference_image import read_reference_image
from services.image_keywords import suggest_photo_keywords
from services.online_search import fetch_online_images
from services.ranker import rank_image_candidates, rank_images
from services.text_query import parse_text_query

online_bp = Blueprint("online", __name__)


@online_bp.route("/search", methods=["POST"])
def search_images():
    """Search online providers and re-rank with CLIP."""
    data = request.get_json() or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Please enter a search query."}), 400
    try:
        positive, exclusions = parse_text_query(query)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    images = fetch_online_images(positive)
    if not images:
        return jsonify(
            {"error": "No images found. Check your API keys."}
        ), 500

    ranked = rank_images(positive, images, exclusions=exclusions)
    return jsonify({"query": query, "images": ranked})


@online_bp.post("/search-by-image")
def search_online_by_image():
    try:
        image, name = read_reference_image()
    except (BadRequest, RequestEntityTooLarge) as error:
        return jsonify({"error": error.description}), error.code

    keywords = request.form.get("keywords", "").strip()
    if len(keywords) > 100:
        return jsonify({"error": "Search keywords must be 100 characters or fewer."}), 400

    features = get_image_embedding(image)
    keywords = keywords or suggest_photo_keywords(features)
    candidates = fetch_online_images(keywords)
    ranked = rank_image_candidates(features, candidates)
    return jsonify({"query": name, "mode": "image", "keywords": keywords, "images": ranked})
