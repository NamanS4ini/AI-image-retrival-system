from io import BytesIO
import mimetypes
import os
from flask import Blueprint, render_template, request, send_file

from services.scanner import get_video_frame

main_bp = Blueprint("main", __name__)

ONLINE_EXAMPLE_QUERIES = {
    "mountain-sunset": "A calm sunset over the mountains",
    "foggy-ride": "A cyclist on a quiet road in the fog",
    "dog-in-water": "A dog running through shallow water",
    "no-white-hat": 'man -"white hat"',
}

MIME_OVERRIDES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@main_bp.route("/")
def home():
    """Render main application UI."""
    return render_template("index.html", online_examples=ONLINE_EXAMPLE_QUERIES)


@main_bp.route("/local")
def local_search():
    return render_template("local.html")


@main_bp.route("/online")
def online_search():
    return render_template(
        "online.html",
        example=ONLINE_EXAMPLE_QUERIES.get(request.args.get("example")),
        show_image_search=request.args.get("mode") == "image",
    )


@main_bp.route("/history")
def history():
    return render_template("history.html")


@main_bp.route("/local-image")
def serve_local_image():
    """Stream locally stored media file inline with Range seeking support."""
    media_path = request.args.get("path", "")
    if not media_path or not os.path.isfile(media_path):
        return "Not found", 404

    mime, _ = mimetypes.guess_type(media_path)
    if not mime:
        ext = os.path.splitext(media_path)[1].lower()
        mime = MIME_OVERRIDES.get(ext, "application/octet-stream")

    return send_file(
        media_path,
        mimetype=mime,
        conditional=True,
        as_attachment=False,
    )


@main_bp.route("/local-video-frame")
def serve_video_frame():
    """Extract and stream a specific video keyframe as JPEG thumbnail."""
    video_path = request.args.get("path", "")
    try:
        timestamp = float(request.args.get("timestamp", 0.0))
    except (ValueError, TypeError):
        timestamp = 0.0

    if not video_path or not os.path.isfile(video_path):
        return "Not found", 404

    frame_bytes = get_video_frame(video_path, timestamp)
    if not frame_bytes:
        return "Frame extraction failed", 500

    return send_file(BytesIO(frame_bytes), mimetype="image/jpeg", as_attachment=False)
