#!/usr/bin/env python3
# img2json.py
# pip install pillow

import argparse, json, sys
from PIL import Image

def rgba_to_hex(r, g, b, a=None, keep_alpha=False):
    if keep_alpha:
        return f"#{r:02X}{g:02X}{b:02X}{a:02X}"
    return f"#{r:02X}{g:02X}{b:02X}"

def image_to_hex_grid(path, keep_alpha=False, transparent_as_null=False):
    im = Image.open(path).convert("RGBA")  # đảm bảo có alpha để xử lý minh bạch
    w, h = im.size
    px = im.load()

    grid = []
    for y in range(h):
        row = []
        for x in range(w):
            r, g, b, a = px[x, y]
            if transparent_as_null and a == 0:
                row.append(None)  # sẽ serialize thành null trong JSON
            else:
                row.append(rgba_to_hex(r, g, b, a, keep_alpha=keep_alpha))
        grid.append(row)
    return grid

def main():
    ap = argparse.ArgumentParser(description="Convert image to JSON 2D array of hex colors.")
    ap.add_argument("input", help="Đường dẫn ảnh (png/jpg/bmp/gif, ...)")
    ap.add_argument("-o", "--output", help="File JSON xuất ra (mặc định: stdout)")
    ap.add_argument("--keep-alpha", action="store_true",
                    help="Giữ alpha và xuất dạng #RRGGBBAA (mặc định chỉ #RRGGBB).")
    ap.add_argument("--transparent-as-null", action="store_true",
                    help="Nếu pixel alpha=0 thì ghi null thay vì mã hex.")
    ap.add_argument("--indent", type=int, default=0,
                    help="Số space để pretty-print JSON (0 = compact).")
    args = ap.parse_args()

    grid = image_to_hex_grid(args.input,
                             keep_alpha=args.keep_alpha,
                             transparent_as_null=args.transparent_as_null)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(grid, f, ensure_ascii=False, indent=args.indent)
    else:
        json.dump(grid, sys.stdout, ensure_ascii=False, indent=args.indent)

if __name__ == "__main__":
    main()
