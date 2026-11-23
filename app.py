import os
import json
import threading
from io import BytesIO
from pathlib import Path

# Disable TensorFlow (Avoid ImportError on Python 3.13)
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file
import requests
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()
app = Flask(__name__)

UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")

CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "embeddings_cache.json"
)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}


def _is_valid_key(key):
    """Check if an API key is set and not a placeholder."""
    return key and not key.startswith("your_")


if not _is_valid_key(UNSPLASH_KEY):
    print("Warning: UNSPLASH_ACCESS_KEY is missing or placeholder.")
if not _is_valid_key(PEXELS_KEY):
    print("Warning: PEXELS_API_KEY is missing — Pexels will be skipped.")
if not _is_valid_key(PIXABAY_KEY):
    print("Warning: PIXABAY_API_KEY is missing — Pixabay will be skipped.")


# ============================================================
# CLIP MODEL
# ============================================================

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

clip_model = CLIPModel.from_pretrained(
    "openai/clip-vit-base-patch32"
).to(device)

clip_processor = CLIPProcessor.from_pretrained(
    "openai/clip-vit-base-patch32"
)


def get_text_embedding(text):
    """Convert text to a normalized CLIP embedding vector."""
    inputs = clip_processor(
        text=[text], return_tensors="pt", padding=True
    ).to(device)
    with torch.no_grad():
        features = clip_model.get_text_features(**inputs)
        if not isinstance(features, torch.Tensor):
            features = features.pooler_output
        features /= features.norm(dim=-1, keepdim=True)
    return features


def get_image_embedding(image):
    """Convert a PIL Image to a normalized CLIP embedding vector."""
    inputs = clip_processor(
        images=image, return_tensors="pt"
    ).to(device)
    with torch.no_grad():
        features = clip_model.get_image_features(**inputs)
        if not isinstance(features, torch.Tensor):
            features = features.pooler_output
        features /= features.norm(dim=-1, keepdim=True)
    return features


# ============================================================
# LOCAL FOLDER SCANNING
# ============================================================

scan_state = {
    "scanning": False,
    "folder": None,
    "total": 0,
    "processed": 0,
    "complete": False,
    "error": None,
}

local_embeddings = {}


def load_cache():
    """Load previously computed embeddings from disk."""
    global local_embeddings
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
            local_embeddings = data.get("images", {})
            scan_state["folder"] = data.get("folder")
            scan_state["complete"] = bool(local_embeddings)
            scan_state["total"] = len(local_embeddings)
            scan_state["processed"] = len(local_embeddings)
            print(
                f"Loaded {len(local_embeddings)} cached embeddings "
                f"from {scan_state['folder']}"
            )
        except Exception as e:
            print(f"Error loading cache: {e}")


def save_cache():
    """Save embeddings to disk (rounded to save space)."""
    compact = {}
    for path, data in local_embeddings.items():
        compact[path] = {
            "embedding": [round(x, 6) for x in data["embedding"]],
            "filename": data["filename"],
        }
    with open(CACHE_FILE, "w") as f:
        json.dump({"folder": scan_state["folder"], "images": compact}, f)


def scan_folder_background(folder_path):
    """Scan a folder for images and compute CLIP embeddings.

    Runs in a background thread. Progress is tracked via scan_state.
    Already-cached images are reused without recomputation.
    """
    global local_embeddings

    scan_state.update({
        "scanning": True,
        "folder": folder_path,
        "error": None,
        "complete": False,
        "total": 0,
        "processed": 0,
    })

    try:
        folder = Path(folder_path)
        image_files = set()
        for ext in IMAGE_EXTENSIONS:
            image_files.update(str(p) for p in folder.rglob(f"*{ext}"))
            image_files.update(str(p) for p in folder.rglob(f"*{ext.upper()}"))

        image_files = sorted(image_files)
        scan_state["total"] = len(image_files)

        if not image_files:
            scan_state["error"] = "No images found in this folder."
            scan_state["scanning"] = False
            return

        new_embeddings = {}

        for i, img_path in enumerate(image_files):
            # Reuse cached embedding if available
            if img_path in local_embeddings:
                new_embeddings[img_path] = local_embeddings[img_path]
            else:
                try:
                    image = Image.open(img_path).convert("RGB")
                    features = get_image_embedding(image)
                    new_embeddings[img_path] = {
                        "embedding": features.cpu().squeeze().tolist(),
                        "filename": os.path.basename(img_path),
                    }
                except Exception as e:
                    print(f"Skipping {img_path}: {e}")

            scan_state["processed"] = i + 1

        local_embeddings = new_embeddings
        save_cache()
        scan_state["complete"] = True

    except Exception as e:
        scan_state["error"] = str(e)
    finally:
        scan_state["scanning"] = False


# Load cache on startup
load_cache()


# ============================================================
# ONLINE IMAGE SOURCES
# ============================================================


def search_unsplash(query):
    try:
        url = (
            "https://api.unsplash.com/search/photos"
            f"?query={query}"
            f"&client_id={UNSPLASH_KEY}"
            "&per_page=15"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        return [
            {
                "url": item["urls"]["regular"],
                "download": item["urls"]["full"],
                "source": item["links"]["html"],
                "photographer": item["user"]["name"],
                "site": "Unsplash",
            }
            for item in data.get("results", [])
        ]
    except requests.RequestException as error:
        print(f"Unsplash Error: {error}")
        return []


def search_pexels(query):
    try:
        url = f"https://api.pexels.com/v1/search?query={query}&per_page=15"
        headers = {"Authorization": PEXELS_KEY}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        return [
            {
                "url": item["src"]["medium"],
                "download": item["src"]["original"],
                "source": item["url"],
                "photographer": item["photographer"],
                "site": "Pexels",
            }
            for item in data.get("photos", [])
        ]
    except requests.RequestException as error:
        print(f"Pexels Error: {error}")
        return []


def search_pixabay(query):
    try:
        url = (
            f"https://pixabay.com/api/?key={PIXABAY_KEY}"
            f"&q={query}"
            "&image_type=photo"
            "&per_page=15"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        return [
            {
                "url": item["webformatURL"],
                "download": item["largeImageURL"],
                "source": item["pageURL"],
                "photographer": item.get("user", "Unknown"),
                "site": "Pixabay",
            }
            for item in data.get("hits", [])
        ]
    except requests.RequestException as error:
        print(f"Pixabay Error: {error}")
        return []


# ============================================================
# CLIP RANKING (ONLINE IMAGES)
# ============================================================


def rank_images(query, images, top_n=15):
    """Download each online image, compute its CLIP embedding,
    and rank by similarity to the query text."""

    if not images:
        return []

    text_features = get_text_embedding(query)
    ranked = []

    for image_data in images:
        try:
            response = requests.get(image_data["url"], timeout=5)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGB")

            image_features = get_image_embedding(image)
            similarity = (text_features @ image_features.T).item()

            image_data["score"] = similarity
            ranked.append(image_data)

        except Exception as error:
            print(f"Skipping image: {error}")

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_n]


# ============================================================
# ROUTES
# ============================================================


@app.route("/")
def home():
    return render_template("index.html")


# --- Online Search ---

@app.route("/search", methods=["POST"])
def search_images():
    data = request.get_json()
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Please enter a search query."}), 400

    images = []
    if _is_valid_key(UNSPLASH_KEY):
        images += search_unsplash(query)
    if _is_valid_key(PEXELS_KEY):
        images += search_pexels(query)
    if _is_valid_key(PIXABAY_KEY):
        images += search_pixabay(query)

    if not images:
        return jsonify(
            {"error": "No images found. Check your API keys."}
        ), 500

    ranked = rank_images(query, images)
    return jsonify({"query": query, "images": ranked})


# --- Local Folder ---

@app.route("/scan-folder", methods=["POST"])
def scan_folder():
    data = request.get_json()
    folder_path = data.get("folder", "").strip()

    if not folder_path:
        return jsonify({"error": "Please provide a folder path."}), 400
    if not os.path.isdir(folder_path):
        return jsonify({"error": f"Folder not found: {folder_path}"}), 404
    if scan_state["scanning"]:
        return jsonify({"error": "A scan is already in progress."}), 409

    thread = threading.Thread(
        target=scan_folder_background,
        args=(folder_path,),
        daemon=True,
    )
    thread.start()

    return jsonify({"status": "started"})


@app.route("/scan-status")
def get_scan_status():
    return jsonify(scan_state)


@app.route("/search-local", methods=["POST"])
def search_local():
    data = request.get_json()
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Please enter a search query."}), 400
    if not local_embeddings:
        return jsonify(
            {"error": "No folder scanned yet. Please scan a folder first."}
        ), 400

    text_features = get_text_embedding(query)

    results = []
    for path, img_data in local_embeddings.items():
        embedding = torch.tensor(
            img_data["embedding"]
        ).unsqueeze(0).to(device)
        similarity = (text_features @ embedding.T).item()
        results.append({
            "path": path,
            "filename": img_data["filename"],
            "score": similarity,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return jsonify({"query": query, "images": results[:30]})


@app.route("/local-image")
def serve_local_image():
    img_path = request.args.get("path", "")
    if not img_path or not os.path.isfile(img_path):
        return "Not found", 404
    return send_file(img_path)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)
