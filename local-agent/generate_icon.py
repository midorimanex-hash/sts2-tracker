"""STS2 Tracker アイコン — シンプルな塔 + グロウ"""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw

ASSETS_DIR = Path(__file__).parent / "assets"

BG          = (26,  26,  46, 255)
TOWER       = (90,  42,  58, 255)   # #5a2a3a
SHADE       = (58,  21,  37, 255)   # #3a1525
GLOW        = (255, 140,   0)       # #ff8c00


def draw_scene(base: int) -> Image.Image:
    S = base * 4
    cx = S // 2

    img = Image.new("RGBA", (S, S), BG)

    # グロウ（上部30%、縦グラデーション）
    glow_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    px = glow_layer.load()
    end = int(S * 0.30)
    for y in range(end):
        t = 1.0 - y / end
        a = int(120 * t * t)
        for x in range(S):
            px[x, y] = (*GLOW, a)
    img = Image.alpha_composite(img, glow_layer)

    # 塔
    draw = ImageDraw.Draw(img)
    tw = int(S * 0.20)
    tl, tr = cx - tw // 2, cx + tw // 2
    tb = int(S * 0.85)
    draw.rectangle([tl, 0, tr, tb], fill=TOWER)
    draw.rectangle([tr - tw // 7, 0, tr, tb], fill=SHADE)

    return img.resize((base, base), Image.LANCZOS)


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    out = ASSETS_DIR / "icon.ico"
    sizes = [16, 32, 48, 64, 128, 256]
    imgs = [draw_scene(s) for s in sizes]
    imgs[-1].save(out, format="ICO", sizes=[(s, s) for s in sizes], append_images=imgs[:-1])
    print(f"生成完了: {out}  ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
