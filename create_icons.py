from PIL import Image, ImageDraw
import os

os.makedirs('static/icons', exist_ok=True)

for size in [192, 512]:
    # Green background
    img = Image.new('RGB', (size, size), '#2ecc71')
    draw = ImageDraw.Draw(img)
    m = int(size * 0.1)
    # White circle
    draw.ellipse([m, m, size-m, size-m], fill='white')
    # Dark green leaf shape
    cx, cy = size//2, size//2
    r = int(size * 0.28)
    draw.ellipse([cx-r, cy-r-int(size*0.04), cx+r, cy+r+int(size*0.04)], fill='#2ecc71')
    draw.ellipse([cx-int(r*0.55), cy-int(r*0.55), cx+int(r*0.55), cy+int(r*0.55)], fill='#27ae60')
    img.save(f'static/icons/icon-{size}.png')
    print(f'Created icon-{size}.png')

print('Icons created successfully!')
