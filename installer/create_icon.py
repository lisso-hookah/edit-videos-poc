"""
installer\icon.ico を生成するスクリプト。
ビルド前に一度だけ実行する。

  pip install pillow
  python installer\create_icon.py
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw


def make_frame(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 背景円
    margin = max(1, size // 32)
    d.ellipse([margin, margin, size - margin, size - margin], fill="#0d1117")

    # フィルムフレーム
    left  = int(size * 0.14)
    right = int(size * 0.86)
    top   = int(size * 0.30)
    bot   = int(size * 0.70)
    edge  = int(size * 0.14)

    d.rectangle([left, top, right, bot], fill="#58a6ff")
    d.rectangle([left, top, left + edge, bot], fill="#1c2128")
    d.rectangle([right - edge, top, right, bot], fill="#1c2128")

    # パーフォレーション穴
    hole_w = int(edge * 0.75)
    hole_h = int(size * 0.08)
    hole_x = left + (edge - hole_w) // 2
    for yi in range(3):
        y = top + int(size * 0.06) + yi * (hole_h + int(size * 0.04))
        d.rectangle([hole_x, y, hole_x + hole_w, y + hole_h], fill="#58a6ff")
        rx = right - edge + (edge - hole_w) // 2
        d.rectangle([rx, y, rx + hole_w, y + hole_h], fill="#58a6ff")

    # 再生三角
    px = int(size * 0.40)
    py_top = int(size * 0.38)
    py_bot = int(size * 0.62)
    tip_x  = int(size * 0.67)
    d.polygon([(px, py_top), (px, py_bot), (tip_x, (py_top + py_bot) // 2)], fill="#0d1117")

    return img


def main() -> None:
    out = Path(__file__).parent / "icon.ico"
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [make_frame(s) for s in sizes]
    # ICO には最大解像度のフレームで保存（Pillow が自動的に多サイズ埋め込み）
    frames[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"アイコン生成完了: {out}")


if __name__ == "__main__":
    main()
