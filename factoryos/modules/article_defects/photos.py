"""Bounded, metadata-free storage for new catalogue photos; never keep originals."""
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 24_000_000
MAX_EDGE = 1600
MAX_STORED_BYTES = 500_000


def prepare_photo(stream):
    """Validate before writing, orient, flatten transparency, then bound JPEG bytes."""
    raw = stream.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError('Foto: maximal 10 MB pro Bild hochladen.')
    try:
        with Image.open(BytesIO(raw)) as original:
            if original.format not in ('JPEG', 'PNG', 'WEBP'):
                raise ValueError('Foto: JPEG/PNG/WebP verwenden.')
            if original.width * original.height > MAX_PIXELS:
                raise ValueError('Foto: maximal 24 Megapixel verwenden.')
            original.load()
            oriented = ImageOps.exif_transpose(original)
            if oriented.mode in ('RGBA', 'LA') or 'transparency' in oriented.info:
                rgba = oriented.convert('RGBA')
                image = Image.new('RGB', rgba.size, 'white')
                image.paste(rgba, mask=rgba.getchannel('A'))
            else:
                image = oriented.convert('RGB')
            image.info.clear()
            image.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Foto konnte nicht gelesen werden. Bitte ein gültiges Foto auswählen.') from exc

    while True:
        # Prefer retaining image dimensions before reducing them further.
        for quality in (84, 78, 72):
            output = BytesIO()
            image.save(output, 'JPEG', quality=quality, optimize=True, progressive=True)
            encoded = output.getvalue()
            if len(encoded) <= MAX_STORED_BYTES:
                return encoded
        if max(image.size) <= 1:
            raise ValueError('Foto konnte nicht ausreichend verkleinert werden.')
        size = tuple(max(1, int(value * 0.85)) for value in image.size)
        image = image.resize(size, Image.Resampling.LANCZOS)
