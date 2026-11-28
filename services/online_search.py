import requests
from config import UNSPLASH_KEY, PEXELS_KEY, PIXABAY_KEY, is_valid_key


def search_unsplash(query):
    """Search Unsplash for image candidates."""
    try:
        response = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": 15},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
            timeout=10,
        )
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
    """Search Pexels for image candidates."""
    try:
        headers = {"Authorization": PEXELS_KEY}
        response = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": 15},
            headers=headers,
            timeout=10,
        )
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
    """Search Pixabay for image candidates."""
    try:
        response = requests.get(
            "https://pixabay.com/api/",
            params={"key": PIXABAY_KEY, "q": query, "image_type": "photo", "per_page": 15},
            timeout=10,
        )
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
    except requests.RequestException:
        print("Pixabay search request failed.")
        return []


def fetch_online_images(query):
    """Fetch candidate images across all enabled stock photo providers."""
    images = []
    if is_valid_key(UNSPLASH_KEY):
        images += search_unsplash(query)
    if is_valid_key(PEXELS_KEY):
        images += search_pexels(query)
    if is_valid_key(PIXABAY_KEY):
        images += search_pixabay(query)
    return images
