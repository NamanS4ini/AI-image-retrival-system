from os import SEEK_END

from flask import request
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
IMAGE_FORMATS = ("JPEG", "PNG", "WEBP", "BMP", "GIF", "TIFF")


def read_reference_image():
    """Read a bounded multipart image and return its RGB pixels and display name."""
    request.max_content_length = MAX_IMAGE_BYTES + 64 * 1024
    try:
        upload = request.files.get("image")
    except RequestEntityTooLarge as error:
        raise RequestEntityTooLarge("Choose an image up to 10 MB.") from error
    if not upload or not upload.filename:
        raise BadRequest("Choose a reference image first.")

    upload.stream.seek(0, SEEK_END)
    if upload.stream.tell() > MAX_IMAGE_BYTES:
        raise RequestEntityTooLarge("Choose an image up to 10 MB.")
    upload.stream.seek(0)

    try:
        with Image.open(upload.stream, formats=IMAGE_FORMATS) as source:
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise RequestEntityTooLarge("Choose an image under 25 megapixels.")
            image = ImageOps.exif_transpose(source).convert("RGB")
    except Image.DecompressionBombError as error:
        raise RequestEntityTooLarge("Choose an image under 25 megapixels.") from error
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise BadRequest("Choose a valid JPEG, PNG, WebP, BMP, GIF, or TIFF image.") from error

    name = upload.filename.replace("\\", "/").rsplit("/", 1)[-1]
    return image, name or "Reference image"
