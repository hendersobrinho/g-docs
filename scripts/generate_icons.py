from __future__ import annotations

import base64
import io
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from PIL import Image


ROOT_DIR = Path(__file__).resolve().parents[1]
ICONS_DIR = ROOT_DIR / "assets" / "icons"
MASTER_ICON_PATH = ICONS_DIR / "icon.svg"
PNG_ICON_PATH = ICONS_DIR / "icon.png"
ICO_ICON_PATH = ICONS_DIR / "icon.ico"
ICNS_ICON_PATH = ICONS_DIR / "icon.icns"
OUTPUT_SIZE = 1024
DEFAULT_INNER_SIZE_RATIO = 0.82
WINDOWS_ICON_INNER_SIZE_RATIO = 0.90
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
EMBEDDED_PNG_PATTERN = re.compile(r"data:image/png;base64,([A-Za-z0-9+/=\s]+)")


def get_pillow_image_module():
    from PIL import Image

    return Image


def load_svg_as_image(svg_path: Path) -> Image.Image:
    image_module = get_pillow_image_module()
    try:
        import cairosvg  # type: ignore[import-not-found]
    except ImportError:
        return extract_embedded_png(svg_path)

    png_bytes = cairosvg.svg2png(
        url=str(svg_path),
        output_width=OUTPUT_SIZE,
        output_height=OUTPUT_SIZE,
    )
    return image_module.open(io.BytesIO(png_bytes)).convert("RGBA")


def extract_embedded_png(svg_path: Path) -> Image.Image:
    image_module = get_pillow_image_module()
    svg_text = svg_path.read_text(encoding="utf-8")
    match = EMBEDDED_PNG_PATTERN.search(svg_text)
    if not match:
        raise RuntimeError(
            "Nao foi possivel renderizar o SVG. Instale 'cairosvg' ou use um icon.svg com PNG embutido."
        )

    png_data = base64.b64decode(re.sub(r"\s+", "", match.group(1)))
    return image_module.open(io.BytesIO(png_data)).convert("RGBA")


def normalize_icon_canvas(
    image: Image.Image,
    inner_size_ratio: float = DEFAULT_INNER_SIZE_RATIO,
) -> Image.Image:
    image_module = get_pillow_image_module()
    alpha_channel = image.getchannel("A")
    bounding_box = alpha_channel.getbbox() or image.getbbox()
    if not bounding_box:
        raise RuntimeError("O arquivo fonte nao possui area visivel para gerar os icones.")

    cropped_image = image.crop(bounding_box)
    target_size = int(OUTPUT_SIZE * inner_size_ratio)
    scale_factor = min(target_size / cropped_image.width, target_size / cropped_image.height)
    resized_size = (
        max(1, round(cropped_image.width * scale_factor)),
        max(1, round(cropped_image.height * scale_factor)),
    )
    resized_image = cropped_image.resize(resized_size, image_module.Resampling.LANCZOS)

    canvas = image_module.new("RGBA", (OUTPUT_SIZE, OUTPUT_SIZE), (0, 0, 0, 0))
    offset_x = (OUTPUT_SIZE - resized_image.width) // 2
    offset_y = (OUTPUT_SIZE - resized_image.height) // 2
    canvas.paste(resized_image, (offset_x, offset_y), resized_image)
    return canvas


def save_png(image: Image.Image, destination: Path) -> None:
    image.save(destination, format="PNG")


def save_ico(image: Image.Image, destination: Path) -> None:
    image.save(destination, format="ICO", sizes=ICO_SIZES)


def save_icns(image: Image.Image, destination: Path) -> None:
    image.save(destination, format="ICNS")


def save_optional_icns(image: Image.Image, destination: Path, platform: str | None = None) -> bool:
    current_platform = platform or sys.platform
    try:
        save_icns(image, destination)
    except Exception as exc:
        if current_platform == "darwin":
            raise RuntimeError(
                "Nao foi possivel gerar o icon.icns necessario para o build do macOS."
            ) from exc

        print(
            "Aviso: nao foi possivel gerar icon.icns neste ambiente; "
            "o build segue normalmente fora do macOS."
        )
        return False

    return True


def generate_icons(platform: str | None = None) -> list[str]:
    if not MASTER_ICON_PATH.exists():
        raise FileNotFoundError(f"Arquivo mestre nao encontrado: {MASTER_ICON_PATH}")

    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    source_image = load_svg_as_image(MASTER_ICON_PATH)
    default_normalized_image = normalize_icon_canvas(source_image)
    windows_normalized_image = normalize_icon_canvas(
        source_image,
        inner_size_ratio=WINDOWS_ICON_INNER_SIZE_RATIO,
    )
    generated_files: list[str] = []

    save_png(default_normalized_image, PNG_ICON_PATH)
    generated_files.append(PNG_ICON_PATH.name)
    save_ico(windows_normalized_image, ICO_ICON_PATH)
    generated_files.append(ICO_ICON_PATH.name)

    if save_optional_icns(default_normalized_image, ICNS_ICON_PATH, platform=platform):
        generated_files.append(ICNS_ICON_PATH.name)

    return generated_files


def main() -> None:
    generated_files = generate_icons()
    print(f"Icones atualizados em: {ICONS_DIR}")
    print(f"- Mestre: {MASTER_ICON_PATH.name}")
    print(f"- Linux/interface: {PNG_ICON_PATH.name}")
    print(f"- Windows: {ICO_ICON_PATH.name}")
    if ICNS_ICON_PATH.name in generated_files:
        print(f"- macOS: {ICNS_ICON_PATH.name}")
    else:
        print(f"- macOS: {ICNS_ICON_PATH.name} (mantido sem regenerar neste ambiente)")


if __name__ == "__main__":
    main()
