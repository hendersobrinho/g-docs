from __future__ import annotations

import base64
from functools import lru_cache
import io
import re
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from xml.etree import ElementTree

from PIL import Image, ImageDraw

from documentos_empresa_app.utils.resources import get_icons_directory


SVG_PATH_TOKEN_PATTERN = re.compile(r"[MLHVCZmlhvcz]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?")
SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"

STATUS_ICON_FILENAMES = {
    "attention": "status_attention.svg",
    "completed": "status_completed.svg",
    "closed": "status_closed.svg",
    "in_progress": "status_in_progress.svg",
    "neutral": "status_neutral.svg",
    "not_started": "status_not_started.svg",
    "overdue": "status_overdue.svg",
    "save": "status_save.svg",
}


def get_status_icon(widget: tk.Misc, icon_name: str, size: int = 16) -> tk.PhotoImage:
    root = widget._root()
    cache = getattr(root, "_docflow_status_icon_cache", None)
    if cache is None:
        cache = {}
        setattr(root, "_docflow_status_icon_cache", cache)

    cache_key = (icon_name, size)
    if cache_key not in cache:
        cache[cache_key] = tk.PhotoImage(
            master=root,
            data=_render_status_icon_png_base64(icon_name, size),
            format="png",
        )
    return cache[cache_key]


def set_button_icon(button: ttk.Button, icon_name: str = "save", size: int = 16) -> None:
    icon = get_status_icon(button, icon_name, size=size)
    button.configure(image=icon, compound="left")


@lru_cache(maxsize=64)
def _render_status_icon(icon_name: str, size: int) -> Image.Image:
    icon_filename = STATUS_ICON_FILENAMES.get(icon_name)
    if not icon_filename:
        raise KeyError(f"Icone de status desconhecido: {icon_name}")

    svg_path = get_icons_directory() / icon_filename
    if not svg_path.exists():
        raise FileNotFoundError(f"Arquivo de icone nao encontrado: {svg_path}")
    return _render_simple_svg(svg_path, size)


@lru_cache(maxsize=64)
def _render_status_icon_png_base64(icon_name: str, size: int) -> bytes:
    image = _render_status_icon(icon_name, size)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue())


def _strip_svg_namespace(tag_name: str) -> str:
    return tag_name.removeprefix(SVG_NAMESPACE)


def _parse_color(raw_color: str | None) -> str | None:
    if raw_color is None:
        return None
    normalized = raw_color.strip()
    if not normalized or normalized.lower() == "none":
        return None
    return normalized


def _parse_float(raw_value: str | None, default: float = 0.0) -> float:
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def _parse_viewbox(root: ElementTree.Element, output_size: int) -> tuple[float, float, float, float]:
    viewbox = root.attrib.get("viewBox")
    if viewbox:
        values = [float(value) for value in re.split(r"[\s,]+", viewbox.strip()) if value]
        if len(values) == 4:
            return values[0], values[1], values[2], values[3]

    width = _parse_float(root.attrib.get("width"), output_size)
    height = _parse_float(root.attrib.get("height"), output_size)
    return 0.0, 0.0, width, height


def _cubic_point(
    start: tuple[float, float],
    control_a: tuple[float, float],
    control_b: tuple[float, float],
    end: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    inv_t = 1.0 - t
    x = (
        inv_t**3 * start[0]
        + 3 * inv_t**2 * t * control_a[0]
        + 3 * inv_t * t**2 * control_b[0]
        + t**3 * end[0]
    )
    y = (
        inv_t**3 * start[1]
        + 3 * inv_t**2 * t * control_a[1]
        + 3 * inv_t * t**2 * control_b[1]
        + t**3 * end[1]
    )
    return x, y


def _parse_simple_svg_path(path_data: str) -> list[list[tuple[float, float]]]:
    tokens = SVG_PATH_TOKEN_PATTERN.findall(path_data)
    paths: list[list[tuple[float, float]]] = []
    current_path: list[tuple[float, float]] = []
    current = (0.0, 0.0)
    path_start = (0.0, 0.0)
    command = ""
    index = 0

    def read_number() -> float:
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value

    def has_number() -> bool:
        return index < len(tokens) and not re.fullmatch(r"[MLHVCZmlhvcz]", tokens[index])

    while index < len(tokens):
        token = tokens[index]
        if re.fullmatch(r"[MLHVCZmlhvcz]", token):
            command = token
            index += 1

        is_relative = command.islower()
        normalized_command = command.upper()

        if normalized_command == "M":
            x = read_number()
            y = read_number()
            if is_relative:
                x += current[0]
                y += current[1]
            current = (x, y)
            path_start = current
            current_path = [current]
            paths.append(current_path)
            command = "l" if is_relative else "L"
            continue

        if normalized_command == "L":
            while has_number():
                x = read_number()
                y = read_number()
                if is_relative:
                    x += current[0]
                    y += current[1]
                current = (x, y)
                current_path.append(current)
            continue

        if normalized_command == "H":
            while has_number():
                x = read_number()
                if is_relative:
                    x += current[0]
                current = (x, current[1])
                current_path.append(current)
            continue

        if normalized_command == "V":
            while has_number():
                y = read_number()
                if is_relative:
                    y += current[1]
                current = (current[0], y)
                current_path.append(current)
            continue

        if normalized_command == "C":
            while has_number():
                control_a = (read_number(), read_number())
                control_b = (read_number(), read_number())
                end = (read_number(), read_number())
                if is_relative:
                    control_a = (control_a[0] + current[0], control_a[1] + current[1])
                    control_b = (control_b[0] + current[0], control_b[1] + current[1])
                    end = (end[0] + current[0], end[1] + current[1])
                for step in range(1, 25):
                    current_path.append(_cubic_point(current, control_a, control_b, end, step / 24))
                current = end
            continue

        if normalized_command == "Z":
            current_path.append(path_start)
            current = path_start
            command = ""
            continue

        raise RuntimeError(f"Comando SVG nao suportado no icone: {command}")

    return paths


def _render_simple_svg(svg_path: Path, output_size: int) -> Image.Image:
    root = ElementTree.fromstring(svg_path.read_text(encoding="utf-8"))
    min_x, min_y, viewbox_width, viewbox_height = _parse_viewbox(root, output_size)
    scale = min(output_size / viewbox_width, output_size / viewbox_height)
    image = Image.new("RGBA", (output_size, output_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def transform(point: tuple[float, float]) -> tuple[float, float]:
        return (point[0] - min_x) * scale, (point[1] - min_y) * scale

    for element in root:
        tag_name = _strip_svg_namespace(element.tag)
        if tag_name == "rect":
            fill = _parse_color(element.attrib.get("fill"))
            if not fill:
                continue
            x = _parse_float(element.attrib.get("x"))
            y = _parse_float(element.attrib.get("y"))
            width = _parse_float(element.attrib.get("width"))
            height = _parse_float(element.attrib.get("height"))
            radius = _parse_float(element.attrib.get("rx"))
            draw.rounded_rectangle(
                [
                    transform((x, y)),
                    transform((x + width, y + height)),
                ],
                radius=radius * scale,
                fill=fill,
            )
            continue

        if tag_name != "path":
            continue

        paths = _parse_simple_svg_path(element.attrib.get("d", ""))
        fill = _parse_color(element.attrib.get("fill"))
        stroke = _parse_color(element.attrib.get("stroke"))
        stroke_width = max(1, round(_parse_float(element.attrib.get("stroke-width"), 1.0) * scale))
        linecap = element.attrib.get("stroke-linecap", "").strip().lower()

        for path in paths:
            transformed_path = [transform(point) for point in path]
            if fill and len(transformed_path) >= 3:
                draw.polygon(transformed_path, fill=fill)
            if stroke and len(transformed_path) >= 2:
                draw.line(transformed_path, fill=stroke, width=stroke_width, joint="curve")
                if linecap == "round":
                    radius = stroke_width / 2
                    for x, y in (transformed_path[0], transformed_path[-1]):
                        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=stroke)

    return image
