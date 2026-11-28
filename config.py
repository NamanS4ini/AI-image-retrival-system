import os
from pathlib import Path
from dotenv import load_dotenv

# Disable TensorFlow (Avoid ImportError on Python 3.13)
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CACHE_FILE = os.path.join(BASE_DIR, "embeddings_cache.json")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
FRAME_SAMPLE_INTERVAL_SEC = 2.0

UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
PEXELS_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")


def is_valid_key(key):
    """Check if an API key is set and not a placeholder."""
    return bool(key and not key.startswith("your_"))


# Log warnings for missing API keys
if not is_valid_key(UNSPLASH_KEY):
    print("Warning: UNSPLASH_ACCESS_KEY is missing or placeholder.")
if not is_valid_key(PEXELS_KEY):
    print("Warning: PEXELS_API_KEY is missing — Pexels will be skipped.")
if not is_valid_key(PIXABAY_KEY):
    print("Warning: PIXABAY_API_KEY is missing — Pixabay will be skipped.")
