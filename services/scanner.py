import json
import os
import threading
from pathlib import Path
import cv2
from PIL import Image
import torch

from clip_model import device, get_image_embedding
from config import (
    CACHE_FILE,
    FRAME_SAMPLE_INTERVAL_SEC,
    IMAGE_EXTENSIONS,
    MEDIA_EXTENSIONS,
    VIDEO_EXTENSIONS,
)
from services.text_query import query_embeddings, score_media

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
        media_type = data.get("type", "image")
        if media_type == "video":
            compact_keyframes = []
            for kf in data.get("keyframes", []):
                compact_keyframes.append({
                    "timestamp": kf["timestamp"],
                    "embedding": [round(x, 6) for x in kf["embedding"]],
                })
            compact[path] = {
                "type": "video",
                "filename": data["filename"],
                "duration": data.get("duration", 0),
                "keyframes": compact_keyframes,
            }
        else:
            compact[path] = {
                "type": "image",
                "filename": data["filename"],
                "embedding": [round(x, 6) for x in data["embedding"]],
            }

    with open(CACHE_FILE, "w") as f:
        json.dump({"folder": scan_state["folder"], "images": compact}, f)


def extract_video_keyframes(video_path, sample_interval=FRAME_SAMPLE_INTERVAL_SEC):
    """Extract keyframes from a video at regular time intervals.

    Returns a list of dicts: [{'timestamp': float, 'image': PIL.Image}], duration (float)
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return [], 0.0

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / fps if fps > 0 else 0.0

    # Ensure we don't extract too many frames for very long videos (cap at ~120 frames)
    frame_step = max(int(fps * sample_interval), 1)
    if total_frames > 0 and total_frames // frame_step > 120:
        frame_step = total_frames // 120

    keyframes = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_step == 0:
            timestamp = round(frame_idx / fps, 2)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            keyframes.append({"timestamp": timestamp, "image": pil_image})

        frame_idx += 1

    cap.release()
    return keyframes, round(duration, 2)


def get_video_frame(video_path, timestamp_sec=0.0):
    """Extract a single video frame at timestamp as JPEG bytes."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None

    cap.set(cv2.CAP_PROP_POS_MSEC, max(float(timestamp_sec), 0.0) * 1000.0)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        return None

    success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not success:
        return None

    return buffer.tobytes()


def scan_folder_background(folder_path):
    """Scan a folder for images and videos and compute CLIP embeddings.

    Runs in a background daemon thread. Already-cached files are reused.
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
        media_files = set()
        for ext in MEDIA_EXTENSIONS:
            media_files.update(str(p) for p in folder.rglob(f"*{ext}"))
            media_files.update(str(p) for p in folder.rglob(f"*{ext.upper()}"))

        media_files = sorted(media_files)
        scan_state["total"] = len(media_files)

        if not media_files:
            scan_state["error"] = "No supported image or video files found in this folder."
            scan_state["scanning"] = False
            return

        new_embeddings = {}

        for i, media_path in enumerate(media_files):
            # Reuse cached embedding if already present
            if media_path in local_embeddings:
                new_embeddings[media_path] = local_embeddings[media_path]
            else:
                ext = Path(media_path).suffix.lower()
                try:
                    if ext in VIDEO_EXTENSIONS:
                        keyframes, duration = extract_video_keyframes(media_path)
                        computed_keyframes = []
                        for kf in keyframes:
                            feat = get_image_embedding(kf["image"])
                            computed_keyframes.append({
                                "timestamp": kf["timestamp"],
                                "embedding": feat.cpu().squeeze().tolist(),
                            })
                        if computed_keyframes:
                            new_embeddings[media_path] = {
                                "type": "video",
                                "filename": os.path.basename(media_path),
                                "duration": duration,
                                "keyframes": computed_keyframes,
                            }
                    elif ext in IMAGE_EXTENSIONS:
                        image = Image.open(media_path).convert("RGB")
                        features = get_image_embedding(image)
                        new_embeddings[media_path] = {
                            "type": "image",
                            "embedding": features.cpu().squeeze().tolist(),
                            "filename": os.path.basename(media_path),
                        }
                except Exception as e:
                    print(f"Skipping {media_path}: {e}")

            scan_state["processed"] = i + 1

        local_embeddings = new_embeddings
        save_cache()
        scan_state["complete"] = True

    except Exception as e:
        scan_state["error"] = str(e)
    finally:
        scan_state["scanning"] = False


def start_folder_scan(folder_path):
    """Start asynchronous folder scan in a daemon thread."""
    thread = threading.Thread(
        target=scan_folder_background,
        args=(folder_path,),
        daemon=True,
    )
    thread.start()


def search_local_images(query, top_n=30, *, exclusions=()):
    """Search locally cached images and videos using text query similarity."""
    if not local_embeddings:
        return []

    features, excluded_features = query_embeddings(query, exclusions)
    return rank_local_media(features, top_n, excluded_features=excluded_features)


def rank_local_media(query_features, top_n=30, *, excluded_features=None):
    """Rank indexed media against an embedding from either CLIP encoder."""
    results = []

    for path, media_data in local_embeddings.items():
        media_type = media_data.get("type", "image")

        if media_type == "video" and "keyframes" in media_data:
            keyframes = media_data["keyframes"]
            if not keyframes:
                continue

            matrix = torch.tensor(
                [kf["embedding"] for kf in keyframes]
            ).to(device)

            scores = score_media(query_features, matrix, excluded_features)
            best_idx = scores.argmax().item()
            best_score = scores[best_idx].item()

            best_timestamp = keyframes[best_idx]["timestamp"]

            results.append({
                "path": path,
                "filename": media_data["filename"],
                "type": "video",
                "score": best_score,
                "timestamp": best_timestamp,
                "duration": media_data.get("duration", 0),
            })
        else:
            # Single image embedding
            if "embedding" not in media_data:
                continue

            embedding = torch.tensor(
                media_data["embedding"]
            ).unsqueeze(0).to(device)
            similarity = score_media(query_features, embedding, excluded_features).item()
            results.append({
                "path": path,
                "filename": media_data["filename"],
                "type": "image",
                "score": similarity,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


# Initialize cache on module import
load_cache()
