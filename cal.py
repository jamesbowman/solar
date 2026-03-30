import sys
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont


WIDTH = 400
HEIGHT = 300
OUTPUT_PATH = Path("cal.png")
RAW_OUTPUT_PATH = Path("panel.bin")
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/ebgaramond/EBGaramond12-Bold.ttf",
    # "/usr/share/fonts/truetype/msttcorefonts/comicbd.ttf",
    # "/usr/share/fonts/opentype/urw-base35/URWBookman-LightItalic.otf",
    # "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]
TARGET_TEXT_HEIGHT_RATIO = 0.98
TARGET_TEXT_WIDTH_RATIO = 0.98


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for font_path in FONT_CANDIDATES:
        if Path(font_path).exists():
            return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default()


def rendered_bbox(day_text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> tuple[int, int, int, int] | None:
    sample = Image.new("1", (WIDTH * 3, HEIGHT * 3), 1)
    draw = ImageDraw.Draw(sample)
    draw.text((WIDTH, HEIGHT), day_text, font=font, fill=0)
    ink = sample.point(lambda p: 255 if p == 0 else 0, mode="L")
    return ink.getbbox()


def fit_font(day_text: str) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, tuple[int, int, int, int]]:
    target_height = int(HEIGHT * TARGET_TEXT_HEIGHT_RATIO)
    target_width = int(WIDTH * TARGET_TEXT_WIDTH_RATIO)

    for size in range(700, 39, -2):
        font = load_font(size)
        bbox = rendered_bbox(day_text, font)
        if bbox is None:
            continue
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        if text_height <= target_height and text_width <= target_width:
            return font, bbox

    font = load_font(40)
    bbox = rendered_bbox(day_text, font)
    if bbox is None:
        bbox = (0, 0, 0, 0)
    return font, bbox


def main() -> None:
    if len(sys.argv) > 1:
        day_text = sys.argv[1]
    else:
        day_text = str(datetime.now().day)
    image = Image.new("1", (WIDTH, HEIGHT), 1)
    draw = ImageDraw.Draw(image)

    font, bbox = fit_font(day_text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (WIDTH - text_width) / 2 - (bbox[0] - WIDTH)
    y = (HEIGHT - text_height) / 2 - (bbox[1] - HEIGHT)

    draw.text((x, y), day_text, font=font, fill=0)

    image.save(OUTPUT_PATH)
    RAW_OUTPUT_PATH.write_bytes(image.tobytes())
    print(f"Saved {OUTPUT_PATH} and {RAW_OUTPUT_PATH} with day {day_text}")


if __name__ == "__main__":
    main()
