"""Generate visual probes from facility image for clue hunting.

This script creates multiple transformed versions of an image and writes all
outputs under the outputs directory so they can be inspected quickly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate transformed images to inspect hidden clues.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("facility_exterior.png"),
        help="Input image path (default: facility_exterior.png).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/facility_probe"),
        help="Directory where transformed outputs are written.",
    )
    return parser


def _save(image: Image.Image, output_dir: Path, name: str, saved: list[str]) -> None:
    out_path = output_dir / f"{name}.png"
    image.save(out_path)
    saved.append(str(out_path))


def _bit_plane_image(channel: Image.Image, bit: int) -> Image.Image:
    # Expand the selected bit-plane to full contrast for visibility.
    return channel.point(lambda px: 255 if ((int(px) >> bit) & 1) else 0, mode="L")


def generate_probes(input_path: Path, output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    with Image.open(input_path) as src:
        image = src.convert("RGB")
    width, height = image.size

    # Core orientation probes.
    _save(image, output_dir, "00_original", saved)
    _save(ImageOps.mirror(image), output_dir, "01_mirror_horizontal", saved)
    _save(ImageOps.flip(image), output_dir, "02_flip_vertical", saved)
    _save(image.rotate(90, expand=True), output_dir, "03_rotate_090", saved)
    _save(image.rotate(180, expand=True), output_dir, "04_rotate_180", saved)
    _save(image.rotate(270, expand=True), output_dir, "05_rotate_270", saved)

    # Tonal and contrast probes.
    gray = ImageOps.grayscale(image)
    _save(gray, output_dir, "10_grayscale", saved)
    _save(ImageOps.invert(image), output_dir, "11_negative_rgb", saved)
    _save(ImageOps.invert(gray), output_dir, "12_negative_gray", saved)
    _save(ImageOps.autocontrast(gray), output_dir, "13_autocontrast_gray", saved)
    _save(ImageOps.equalize(gray), output_dir, "14_equalize_gray", saved)
    _save(ImageOps.posterize(image, bits=3), output_dir, "15_posterize_3bit", saved)
    _save(ImageOps.solarize(image, threshold=96), output_dir, "16_solarize_096", saved)
    _save(ImageOps.solarize(image, threshold=160), output_dir, "17_solarize_160", saved)

    # Sharpening and edge probes.
    _save(gray.filter(ImageFilter.EDGE_ENHANCE_MORE), output_dir, "20_edge_enhance", saved)
    _save(gray.filter(ImageFilter.FIND_EDGES), output_dir, "21_find_edges", saved)
    _save(gray.filter(ImageFilter.CONTOUR), output_dir, "22_contour", saved)
    _save(gray.filter(ImageFilter.DETAIL), output_dir, "23_detail", saved)

    # Threshold and high-contrast probes.
    _save(gray.point(lambda p: 255 if p > 110 else 0), output_dir, "30_threshold_110", saved)
    _save(gray.point(lambda p: 255 if p > 140 else 0), output_dir, "31_threshold_140", saved)
    _save(gray.point(lambda p: 255 if p > 170 else 0), output_dir, "32_threshold_170", saved)
    _save(ImageEnhance.Contrast(gray).enhance(2.5), output_dir, "33_contrast_2_5x", saved)
    _save(ImageEnhance.Contrast(gray).enhance(4.0), output_dir, "34_contrast_4_0x", saved)

    # Channel isolation probes.
    red, green, blue = image.split()
    _save(red, output_dir, "40_channel_red", saved)
    _save(green, output_dir, "41_channel_green", saved)
    _save(blue, output_dir, "42_channel_blue", saved)

    # Low-bit probes often reveal hidden overlays or stego-like patterns.
    _save(_bit_plane_image(red, 0), output_dir, "50_red_bit0", saved)
    _save(_bit_plane_image(green, 0), output_dir, "51_green_bit0", saved)
    _save(_bit_plane_image(blue, 0), output_dir, "52_blue_bit0", saved)
    _save(_bit_plane_image(red, 1), output_dir, "53_red_bit1", saved)
    _save(_bit_plane_image(green, 1), output_dir, "54_green_bit1", saved)
    _save(_bit_plane_image(blue, 1), output_dir, "55_blue_bit1", saved)

    # Focused crop around likely signage zones: center building + lower entrance.
    center_crop = image.crop(
        (
            int(width * 0.2),
            int(height * 0.22),
            int(width * 0.8),
            int(height * 0.68),
        )
    )
    lower_crop = image.crop(
        (
            int(width * 0.25),
            int(height * 0.55),
            int(width * 0.75),
            int(height * 0.95),
        )
    )
    _save(center_crop, output_dir, "60_crop_center_building", saved)
    _save(lower_crop, output_dir, "61_crop_lower_approach", saved)
    _save(ImageEnhance.Contrast(ImageOps.grayscale(center_crop)).enhance(3.0), output_dir, "62_center_crop_contrast_3x", saved)
    _save(ImageEnhance.Contrast(ImageOps.grayscale(lower_crop)).enhance(3.0), output_dir, "63_lower_crop_contrast_3x", saved)

    manifest_path = output_dir / "manifest.json"
    saved.append(str(manifest_path))
    manifest = {
        "input": str(input_path),
        "output_dir": str(output_dir),
        "generated_files": saved,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return saved


def main() -> None:
    args = _build_parser().parse_args()
    try:
        generated = generate_probes(args.input, args.output_dir)
    except Exception as exc:
        print(f"Error generating probes: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Generated {len(generated)} files under {args.output_dir}")


if __name__ == "__main__":
    main()
