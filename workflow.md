# AI Image Retrieval System — Complete Workflow & Architecture

## 1. Overview

This project is a Flask-powered web application that performs **Semantic Visual Search** using OpenAI's **CLIP (Contrastive Language-Image Pretraining)** model. 

It provides two distinct search modes:
1. **My Computer (Local Folder)**: Analyze photos stored locally on your machine without uploading them anywhere. Embeddings are precomputed once, cached, and subsequent searches run in under a second completely offline.
2. **Online Sources**: Search stock photo platforms (Unsplash, Pixabay) via APIs, download candidates on-the-fly, and rank them using CLIP relevance.

The user interface uses a clean, professional, non-gradient editorial design with tabbed navigation.

---

## 2. High-Level Architecture

```
                          ┌────────────────────────────────┐
                          │         Web Browser            │
                          │   (templates/index.html)       │
                          └───────────────┬────────────────┘
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   │                                             │
      Mode 1: Local Computer                        Mode 2: Online Sources
                   │                                             │
                   ▼                                             ▼
┌──────────────────────────────────────┐     ┌──────────────────────────────────────┐
│  POST /scan-folder                   │     │  POST /search                        │
│  - Input: folder path (e.g. D:\Pics) │     │  - Input: text query                 │
│  - Finds all image files             │     │  - Calls Unsplash / Pixabay APIs     │
│  - Background worker computes CLIP   │     │  - Downloads candidate thumbnails    │
│    embeddings                        │     │  - Computes CLIP image embeddings    │
│  - Saves to embeddings_cache.json    │     │  - Computes CLIP text embedding      │
├──────────────────────────────────────┤     │  - Ranks candidates by similarity    │
│  GET /scan-status (polls progress)   │     └──────────────────────────────────────┘
├──────────────────────────────────────┤
│  POST /search-local                  │
│  - Input: text query                 │
│  - Computes query text vector        │
│  - Dot-product with cached vectors   │
│  - Instant top-N results             │
├──────────────────────────────────────┤
│  GET /local-image?path=...           │
│  - Streams local photo to browser    │
└──────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│             CLIP Model               │
│    (openai/clip-vit-base-patch32)    │
│  - ViT Vision Transformer            │
│  - Text Transformer                  │
│  - Shared 512-dimensional vector     │
│    space                             │
└──────────────────────────────────────┘
```

---

## 3. How the AI Search Works (CLIP Explained)

Traditional search engines match exact keywords or tags (metadata). If an image of a red convertible on the highway is simply named `IMG_1042.jpg` without tags, a keyword search for "car" or "vehicle" will fail.

**CLIP changes this:**
- CLIP was trained on hundreds of millions of image-and-text pairs.
- It maps both **text descriptions** and **raw images** into the exact same **512-dimensional vector space**.
- In this space, the text vector for *"a dog running on the beach"* points in nearly the exact same direction as the visual feature vector extracted from a photo of a dog running on sand.

### Cosine Similarity Formula

When comparing normalized vectors:
$$\text{Similarity} = \vec{v}_{\text{text}} \cdot \vec{v}_{\text{image}} = \sum_{i=1}^{512} v_{\text{text}, i} \times v_{\text{image}, i}$$

- **1.0**: Perfect alignment
- **> 0.25 - 0.35**: Strong match
- **~ 0.15 - 0.20**: Moderate contextual relevance
- **< 0.10**: Weak or unrelated

Because both vectors are $L_2$-normalized (`norm = 1`), computing similarity is simply a fast matrix dot-product (`@` in PyTorch).

---

## 4. Deep-Dive: Mode 1 — Local Computer Analysis

### 4.1 Folder Scanning & Background Processing
1. **User input**: You supply a local path such as `C:\Users\Name\Pictures` or `D:\Photos`.
2. **Path discovery**: `Path.rglob()` searches recursively for all files ending in `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.gif`, `.tiff`.
3. **Background Thread**: A background daemon thread (`scan_folder_background`) handles processing so the web interface does not freeze or time out.
4. **Progress polling**: The frontend polls `GET /scan-status` every 400ms to update the live progress bar and count (`X / Y images analyzed`).

### 4.2 Where is the analysis data stored?
All computed features are written directly to:
📁 **`embeddings_cache.json`** in your project root directory.

#### Structure of `embeddings_cache.json`:
```json
{
  "folder": "D:\\Photos",
  "images": {
    "D:\\Photos\\IMG_001.jpg": {
      "filename": "IMG_001.jpg",
      "embedding": [0.015243, -0.045129, 0.124589, 0.003112, "... (512 floats)"]
    },
    "D:\\Photos\\vacations\\beach.png": {
      "filename": "beach.png",
      "embedding": [-0.021045, 0.089412, -0.034511, 0.018742, "... (512 floats)"]
    }
  }
}
```

### 4.3 Why is this design efficient?
- **Zero upload / Complete privacy**: Photos never leave your machine; no third-party APIs see your files.
- **Smart incremental caching**: On subsequent scans or re-runs, existing images in `embeddings_cache.json` are skipped and loaded instantly.
- **Instant search latency**: For 500–10,000 photos, matching text against precomputed vectors takes **under 50 milliseconds** because no images need to be opened or processed during search.
- **Local serving endpoint**: The endpoint `GET /local-image?path=...` uses Flask's `send_file()` to render and preview images directly in your browser without copying them into the project folder.

---

## 5. Deep-Dive: Mode 2 — Online Sources

1. **User query**: User types a search prompt like *"snowy mountain peak"*.
2. **API Querying**: The app sends concurrent requests to:
   - **Unsplash API**: Up to 15 images
   - **Pixabay API**: Up to 15 images
   - *(Pexels is automatically skipped if no key is configured)*
3. **Download candidates**: Flask downloads the candidate image thumbnails into memory using Python `BytesIO` streams (temporary, not saved to disk).
4. **On-the-fly CLIP embedding**: CLIP extracts vectors for each candidate.
5. **Re-ranking**: Results are sorted descending by their dot product with the user query and returned as JSON.

---

## 6. Endpoints Reference

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Serves main UI (`templates/index.html`) |
| `POST` | `/scan-folder` | Initiates background analysis of a local directory (`{ "folder": "..." }`) |
| `GET` | `/scan-status` | Returns current scan progress (`scanning`, `processed`, `total`, `complete`, `error`) |
| `POST` | `/search-local` | Searches precomputed local embeddings with a natural language query |
| `GET` | `/local-image` | Serves a local image file by path (`?path=...`) |
| `POST` | `/search` | Searches online APIs and ranks results with CLIP |

---

## 7. Project Structure

```
AI-Based-Image-Retrieval-System/
├── app.py                   # Main Flask backend (CLIP inference, routes, background worker)
├── embeddings_cache.json    # Local embeddings cache (generated after folder scan)
├── .env                     # API keys (optional: Unsplash, Pixabay)
├── templates/
│   └── index.html           # Single-page web UI (HTML, CSS, JavaScript)
├── workflow.md              # Complete architecture & workflow documentation (this file)
└── .venv/                   # Python virtual environment
```

---

## 8. Requirements & Setup

- **Python**: 3.10 – 3.13
- **Core libraries**:
  - `torch`: PyTorch runtime for tensor math and model execution.
  - `transformers`: Hugging Face library running `CLIPModel` and `CLIPProcessor`.
  - `Pillow`: Image decoding and pre-processing.
  - `flask`: HTTP server.
  - `requests`: External API calls.
  - `python-dotenv`: Environment configuration loading.
