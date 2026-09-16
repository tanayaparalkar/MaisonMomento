import os
from PIL import Image

def crop_bottom(img_path, pixels):
    if not os.path.exists(img_path):
        return
    try:
        img = Image.open(img_path)
        width, height = img.size
        # Crop the bottom 'pixels' off
        cropped = img.crop((0, 0, width, height - pixels))
        cropped.save(img_path)
        print(f"Successfully cropped {img_path}")
    except Exception as e:
        print(f"Failed to crop {img_path}: {e}")

images = [
    'static/images/about/echoes.jpg',
    'static/images/about/forest.jpg',
    'static/images/about/golden.jpg'
]

for img in images:
    crop_bottom(img, 70)
