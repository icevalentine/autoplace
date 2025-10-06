import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import os

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Phân tích màu ảnh (Tkinter + Pillow + NumPy)")
        self.geometry("900x600")

        # Trạng thái
        self.image_path = None
        self.image_rgba = None       # PIL Image (RGBA)
        self.tkimg = None            # ImageTk.PhotoImage để hiển thị
        self.color_map = {}          # dict[str -> list[(row, col)]], 1-based

        # Thanh công cụ
        toolbar = tk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=6, pady=6)

        btn_open = tk.Button(toolbar, text="Mở ảnh…", command=self.open_image)
        btn_open.pack(side=tk.LEFT, padx=4)

        btn_export = tk.Button(toolbar, text="Xuất file…", command=self.export_text)
        btn_export.pack(side=tk.LEFT, padx=4)

        self.info_var = tk.StringVar(value="Chưa tải ảnh.")
        lbl_info = tk.Label(toolbar, textvariable=self.info_var, anchor="w")
        lbl_info.pack(side=tk.LEFT, padx=12)

        # Khu vực hiển thị ảnh có thanh cuộn
        viewer = tk.Frame(self)
        viewer.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(viewer, bg="#f0f0f0")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        yscroll = tk.Scrollbar(viewer, orient=tk.VERTICAL, command=self.canvas.yview)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        xscroll = tk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        # ID item ảnh trên canvas
        self.canvas_image_id = None

    def open_image(self):
        path = filedialog.askopenfilename(
            title="Chọn ảnh",
            filetypes=[
                ("Ảnh", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tiff;*.webp"),
                ("Tất cả", "*.*"),
            ],
        )
        if not path:
            return

        try:
            img = Image.open(path).convert("RGBA")  # đảm bảo có alpha
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không mở được ảnh:\n{e}")
            return

        self.image_path = path
        self.image_rgba = img
        self.display_image_on_canvas(img)
        self.compute_colors()

    def display_image_on_canvas(self, img_rgba: Image.Image):
        # Hiển thị ảnh thật kích thước gốc, có thanh cuộn
        w, h = img_rgba.size
        self.canvas.delete("all")
        self.tkimg = ImageTk.PhotoImage(img_rgba)
        self.canvas_image_id = self.canvas.create_image(0, 0, image=self.tkimg, anchor="nw")
        self.canvas.config(scrollregion=(0, 0, w, h))

    def compute_colors(self):
        """Đọc ảnh RGBA, bỏ pixel alpha=0, gom nhóm theo màu RGB.
        Lưu vào self.color_map: { '#RRGGBB': [(row, col), ...] } với row/col 1-based."""
        if self.image_rgba is None:
            self.color_map = {}
            self.info_var.set("Chưa tải ảnh.")
            return

        arr = np.array(self.image_rgba, dtype=np.uint8)  # (H, W, 4)
        H, W, C = arr.shape
        assert C == 4

        alpha = arr[:, :, 3]
        ys, xs = np.where(alpha != 0)  # chỉ lấy pixel alpha != 0

        # Lấy RGB tương ứng
        rgbs = arr[ys, xs, :3]  # (N, 3)

        color_map = {}
        # Duyệt từng điểm (tối ưu vừa đủ, dễ đọc; có thể mất vài giây với ảnh rất lớn)
        for i in range(len(ys)):
            r, g, b = rgbs[i]
            color_hex = f"#{r:02X}{g:02X}{b:02X}"
            # Lưu tọa độ 1-based theo (row, col) = (y+1, x+1)
            rc = (int(ys[i]) + 1, int(xs[i]) + 1)
            if color_hex not in color_map:
                color_map[color_hex] = []
            color_map[color_hex].append(rc)

        self.color_map = color_map

        # Cập nhật thông tin
        unique_colors = len(color_map)
        kept_pixels = len(ys)
        total_pixels = H * W
        base = os.path.basename(self.image_path) if self.image_path else "—"
        self.info_var.set(
            f"Ảnh: {base} | Kích thước: {W}×{H} | Pixel giữ lại: {kept_pixels}/{total_pixels} | Số màu: {unique_colors}"
        )

    def export_text(self):
        if not self.color_map:
            messagebox.showwarning("Chú ý", "Chưa có dữ liệu màu để xuất. Hãy mở ảnh trước.")
            return

        path = filedialog.asksaveasfilename(
            title="Lưu file kết quả",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("Tất cả", "*.*")],
        )
        if not path:
            return

        try:
            # Sắp xếp màu theo mã hex tăng dần cho ổn định (có thể đổi sang sắp xếp theo số lượng nếu bạn thích)
            colors_sorted = sorted(self.color_map.items(), key=lambda kv: kv[0])

            with open(path, "w", encoding="utf-8") as f:
                f.write(str(len(colors_sorted)) + "\n")
                for color_hex, coords in colors_sorted:
                    # Có thể sắp xếp lại tọa độ theo (row, col) để dễ đọc:
                    coords_sorted = sorted(coords)
                    coords_str = " ".join(f"({r},{c})" for r, c in coords_sorted)
                    line = f"{color_hex} {len(coords_sorted)} {coords_str}\n"
                    f.write(line)

            messagebox.showinfo("Thành công", f"Đã xuất file:\n{path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể ghi file:\n{e}")

if __name__ == "__main__":
    App().mainloop()
