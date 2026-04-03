"""
Generate Glossa icon files (ICO + PNG).
Draws a dark circle with a globe symbol.
Requires: pip install Pillow
"""
from PIL import Image, ImageDraw
import os


def create_icon():
    sizes = [16, 32, 48, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Dark circle background
        draw.ellipse([0, 0, size - 1, size - 1], fill=(23, 23, 23, 255))

        # Globe - outer circle
        cx, cy = size // 2, size // 2
        r = int(size * 0.35)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(74, 144, 217, 255),
            width=max(1, size // 16),
        )

        # Globe - vertical ellipse (meridian)
        mr = int(r * 0.5)
        draw.ellipse(
            [cx - mr, cy - r, cx + mr, cy + r],
            outline=(74, 144, 217, 255),
            width=max(1, size // 16),
        )

        # Globe - horizontal line (equator)
        lw = max(1, size // 16)
        draw.line([cx - r, cy, cx + r, cy], fill=(74, 144, 217, 255), width=lw)

        images.append(img)

    os.makedirs("assets", exist_ok=True)

    # Save multi-size ICO (largest image first, rest as append_images)
    images[-1].save(
        "assets/icon.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1],
    )

    # Save 256x256 PNG
    images[-1].save("assets/icon.png", format="PNG")

    print("Icon created: assets/icon.ico + assets/icon.png")


if __name__ == "__main__":
    create_icon()
