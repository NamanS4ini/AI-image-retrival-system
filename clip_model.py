import torch
from transformers import CLIPModel, CLIPProcessor

if torch.cuda.is_available():
    device = "cuda"
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"

print(f"Using device: {device}")

clip_model = CLIPModel.from_pretrained(
    "openai/clip-vit-base-patch32"
).to(device)

clip_processor = CLIPProcessor.from_pretrained(
    "openai/clip-vit-base-patch32"
)


def get_text_embedding(text):
    """Convert text to a normalized CLIP embedding vector."""
    return get_text_embeddings([text])


def get_text_embeddings(texts):
    """Convert a batch of text prompts to normalized CLIP vectors."""
    inputs = clip_processor(
        text=texts, return_tensors="pt", padding=True, truncation=True
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
