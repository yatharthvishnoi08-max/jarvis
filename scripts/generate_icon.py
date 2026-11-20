import math
from pathlib import Path
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
ASSETS_DIR.mkdir(exist_ok=True)

def create_arc_reactor_icon(size: int = 512) -> Image.Image:
    # 32-bit RGBA image
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center = size / 2.0
    scale = size / 100.0

    # Background subtle dark disc
    draw.ellipse([center - 47 * scale, center - 47 * scale, center + 47 * scale, center + 47 * scale],
                 fill=(5, 8, 17, 240), outline=(0, 240, 255, 180), width=max(1, int(2 * scale)))

    # Outer cyan ring
    draw.ellipse([center - 45 * scale, center - 45 * scale, center + 45 * scale, center + 45 * scale],
                 outline=(0, 240, 255, 230), width=max(1, int(3 * scale)))

    # Middle blue ring (dash illusion)
    num_dashes = 16
    for i in range(num_dashes):
        start_angle = i * (360.0 / num_dashes)
        end_angle = start_angle + 12.0
        draw.arc([center - 35 * scale, center - 35 * scale, center + 35 * scale, center + 35 * scale],
                 start=start_angle, end=end_angle, fill=(0, 112, 243, 220), width=max(1, int(2.5 * scale)))

    # Inner cyan core ring
    draw.ellipse([center - 22 * scale, center - 22 * scale, center + 22 * scale, center + 22 * scale],
                 outline=(0, 240, 255, 240), width=max(1, int(3 * scale)))

    # Cyan energy core fill
    draw.ellipse([center - 13 * scale, center - 13 * scale, center + 13 * scale, center + 13 * scale],
                 fill=(0, 240, 255, 255))

    # Center white hot spot
    draw.ellipse([center - 6.5 * scale, center - 6.5 * scale, center + 6.5 * scale, center + 6.5 * scale],
                 fill=(255, 255, 255, 255))

    # Cross tick lines
    line_w = max(1, int(2 * scale))
    draw.line([center, center - 45 * scale, center, center - 24 * scale], fill=(0, 240, 255, 230), width=line_w)
    draw.line([center, center + 24 * scale, center, center + 45 * scale], fill=(0, 240, 255, 230), width=line_w)
    draw.line([center - 45 * scale, center, center - 24 * scale, center], fill=(0, 240, 255, 230), width=line_w)
    draw.line([center + 24 * scale, center, center + 45 * scale, center], fill=(0, 240, 255, 230), width=line_w)

    return img

def main():
    icon_img = create_arc_reactor_icon(512)
    png_path = ASSETS_DIR / "jarvis.png"
    icon_img.save(png_path, "PNG")

    ico_path = ASSETS_DIR / "jarvis.ico"
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon_img.save(ico_path, format="ICO", sizes=icon_sizes)
    print(f"Generated icon assets: {png_path} and {ico_path}")

if __name__ == "__main__":
    main()
