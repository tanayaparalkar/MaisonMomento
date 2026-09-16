"""
Fix image filename mismatches between ProductImage DB records and actual files on disk.
Strategy: Rename the DB records to match the actual files on disk.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maison_momento.settings')
django.setup()

from apps.catalog.models import ProductImage
from pathlib import Path
from django.conf import settings

media_products_dir = Path(settings.MEDIA_ROOT) / "products"

# Map of actual files on disk (lowercase for matching)
actual_files = {f.lower(): f for f in os.listdir(media_products_dir) if f.endswith('.png')}

print("=== Actual files on disk ===")
for f in sorted(actual_files.values()):
    print(f"  {f}")

print("\n=== Fixing ProductImage records ===")
for pi in ProductImage.objects.all():
    current_path = pi.image.name  # e.g. "products/néroli_riviera.png"
    current_filename = os.path.basename(current_path)
    
    # Check if the file actually exists
    full_path = Path(settings.MEDIA_ROOT) / current_path
    if full_path.exists():
        print(f"  OK: {pi.product.name} -> {current_path}")
        continue
    
    # Try to find a matching file
    # Build expected filename from product name
    product_slug = pi.product.name.lower().replace(' ', '_').replace("'", "").replace('é', 'e').replace('è', 'e').replace('ô', 'o').replace('î', 'i').replace('ï', 'i')
    
    # Manual mapping for known mismatches
    name_to_file = {
        "bergamot_solstice": "bergamont_solistice.png",
        "neroli_riviera": "neroli_riviera.png",  # may not exist
        "musc_imperial_precieux": "music_imperial_precieux.png",
        "cuir_dorient": "cuir_d_orient.png",
        "cedre_blanc_&_vetiver": "cedre_blanc_&_vetiver.png",
        "oud_sublime_royale": "oud_sublime_royal.png",
        "pure_cashmere_musc": "pure_cashmere_music.png",
    }
    
    matched_file = None
    
    # Check manual mapping first
    for key, val in name_to_file.items():
        if key in product_slug:
            if val in actual_files.values():
                matched_file = val
                break
    
    # If no manual match, try fuzzy matching by checking if any actual file starts with similar chars
    if not matched_file:
        for actual_name in actual_files.values():
            actual_base = actual_name.replace('.png', '')
            if product_slug.startswith(actual_base[:5]) or actual_base.startswith(product_slug[:5]):
                matched_file = actual_name
                break
    
    if matched_file:
        new_path = f"products/{matched_file}"
        pi.image.name = new_path
        pi.save(update_fields=['image'])
        print(f"  FIXED: {pi.product.name}: {current_path} -> {new_path}")
    else:
        print(f"  MISSING: {pi.product.name} -> {current_path} (no matching file found)")

print("\n=== Verification ===")
for pi in ProductImage.objects.all():
    full_path = Path(settings.MEDIA_ROOT) / pi.image.name
    status = "✓" if full_path.exists() else "✗ MISSING"
    print(f"  {status}: {pi.product.name} -> {pi.image.name}")
