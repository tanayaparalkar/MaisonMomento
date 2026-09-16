import glob
import os
from PIL import Image

# Find the most recently uploaded image in the .user_uploaded directory
search_dir = "/Users/tanaya/.gemini/antigravity-ide/brain/5bc2dd54-9877-44da-a628-d8a05c4a1a72/.user_uploaded/"
files = glob.glob(os.path.join(search_dir, '*'))
files.sort(key=os.path.getmtime, reverse=True)

if files:
    img_path = files[0]
    img = Image.open(img_path)
    img = img.convert('RGB')
    
    # Get the color of the center pixel
    width, height = img.size
    r, g, b = img.getpixel((width // 2, height // 2))
    
    hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
    print(f"Color: {hex_color} from {os.path.basename(img_path)}")
else:
    print("No images found.")
