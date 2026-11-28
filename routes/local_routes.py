import os
from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from clip_model import get_image_embedding
from routes.reference_image import read_reference_image
from services import scanner
from services.text_query import parse_text_query

local_bp = Blueprint("local", __name__)


@local_bp.route("/scan-folder", methods=["POST"])
def scan_folder():
    """Trigger background scanning of a local directory."""
    data = request.get_json() or {}
    folder_path = data.get("folder", "").strip()

    if not folder_path:
        return jsonify({"error": "Please provide a folder path."}), 400
    if not os.path.isdir(folder_path):
        return jsonify({"error": f"Folder not found: {folder_path}"}), 404
    if scanner.scan_state["scanning"]:
        return jsonify({"error": "A scan is already in progress."}), 409

    scanner.start_folder_scan(folder_path)
    return jsonify({"status": "started"})


@local_bp.route("/scan-status")
def get_scan_status():
    """Get current scanning progress and statistics."""
    return jsonify(scanner.scan_state)


@local_bp.route("/search-local", methods=["POST"])
def search_local():
    """Perform semantic search across cached local images."""
    data = request.get_json() or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Please enter a search query."}), 400
    try:
        positive, exclusions = parse_text_query(query)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if not scanner.local_embeddings:
        return jsonify(
            {"error": "No folder scanned yet. Please scan a folder first."}
        ), 400

    results = scanner.search_local_images(positive, top_n=30, exclusions=exclusions)
    return jsonify({"query": query, "images": results})


@local_bp.post("/search-local-by-image")
def search_local_by_image():
    if not scanner.local_embeddings:
        return jsonify({"error": "No folder scanned yet. Please scan a folder first."}), 400

    try:
        image, name = read_reference_image()
    except (BadRequest, RequestEntityTooLarge) as error:
        return jsonify({"error": error.description}), error.code

    results = scanner.rank_local_media(get_image_embedding(image))
    return jsonify({"query": name, "mode": "image", "images": results})
