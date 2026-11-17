"""Pure photo preparation tests: no DB or access to existing user images."""
from io import BytesIO
from pathlib import Path
import importlib.util
import random

source = Path(__file__).resolve().parents[1] / 'factoryos/modules/article_defects/photos.py'
spec = importlib.util.spec_from_file_location('catalogue_photos', source)
photos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(photos)
from PIL import Image


def upload(image, format='PNG', **kwargs):
    stream = BytesIO()
    image.save(stream, format, **kwargs)
    stream.seek(0)
    return stream


def check(encoded, size=None):
    assert len(encoded) <= photos.MAX_STORED_BYTES
    with Image.open(BytesIO(encoded)) as result:
        assert result.format == 'JPEG' and result.mode == 'RGB'
        assert max(result.size) <= photos.MAX_EDGE
        assert not result.getexif() and not result.info.get('icc_profile')
        if size is not None:
            assert result.size == size, result.size
        return result.size


check(photos.prepare_photo(upload(Image.new('RGB', (4000, 3000), 'gray'))), (1600, 1200))
check(photos.prepare_photo(upload(Image.new('RGB', (90, 120), 'red'))), (90, 120))
exif = Image.Exif()
exif[274] = 6
exif[270] = 'private metadata'
check(photos.prepare_photo(upload(Image.new('RGB', (2000, 1000), 'blue'), 'JPEG', exif=exif)), (800, 1600))
transparent = photos.prepare_photo(upload(Image.new('RGBA', (100, 100), (255, 0, 0, 0))))
check(transparent, (100, 100))
with Image.open(BytesIO(transparent)) as result:
    assert min(result.getpixel((50, 50))) > 245
noise = Image.frombytes('RGB', (2000, 1500), random.Random(5).randbytes(9_000_000))
noisy_upload = upload(noise)
encoded = photos.prepare_photo(noisy_upload)
check(encoded)
assert len(encoded) < noisy_upload.getbuffer().nbytes
print(f'PASS: detailed/noisy photo {noisy_upload.getbuffer().nbytes:,} -> {len(encoded):,} bytes; dimensions {check(encoded)}')
for invalid in (BytesIO(b'not an image'), BytesIO(b'x' * (photos.MAX_UPLOAD_BYTES + 1)), upload(Image.new('RGB', (2, 2)), 'GIF'), upload(Image.new('1', (6000, 5000)))):
    try:
        photos.prepare_photo(invalid)
        raise AssertionError('Invalid upload accepted')
    except ValueError:
        pass
print('PASS: size/byte caps, no upscale, EXIF orientation and metadata removal, white transparency, invalid/type/pixel/upload limits')
