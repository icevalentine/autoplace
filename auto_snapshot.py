import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import os
import re
import random
from typing import List, Tuple, Optional, Dict, Any

# ---------------------------
# Helpers: đọc file .txt
# ---------------------------

PointDef = Tuple[int, int, str]  # (row, col, "#RRGGBB")
COLOR_LINE_RE = re.compile(r'^\s*(#[0-9A-Fa-f]{6})\s+(\d+)\s+(.*)$')
COORD_RE = re.compile(r'\(\s*(\d+)\s*,\s*(\d+)\s*\)')

def parse_points_txt(path: str) -> List[PointDef]:
    """Trả về list điểm theo đúng thứ tự xuất hiện trong file."""
    points: List[PointDef] = []
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    if not lines:
        return points
    for line in lines[1:]:
        m = COLOR_LINE_RE.match(line)
        if not m:
            continue
        color_hex = m.group(1).upper()
        coords = COORD_RE.findall(m.group(3))
        for (r, c) in coords:
            points.append((int(r), int(c), color_hex))
    return points

def parse_color_groups_txt(path: str) -> List[Tuple[str, List[Tuple[int,int]]]]:
    """Trả về [(color_hex, [(row, col), ...]), ...] theo thứ tự dòng màu trong file."""
    groups: List[Tuple[str, List[Tuple[int,int]]]] = []
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    if not lines:
        return groups
    for line in lines[1:]:
        m = COLOR_LINE_RE.match(line)
        if not m:
            continue
        color_hex = m.group(1).upper()
        coords = [(int(r), int(c)) for (r, c) in COORD_RE.findall(m.group(3))]
        groups.append((color_hex, coords))
    return groups

def hex_to_rgba(color_hex: str) -> Tuple[int,int,int,int]:
    color_hex = color_hex.lstrip('#')
    return (int(color_hex[0:2], 16),
            int(color_hex[2:4], 16),
            int(color_hex[4:6], 16),
            255)

# ---------------------------
# UI: Layer
# ---------------------------

class LayerRow:
    """
    - Entry x,y (top-left)
    - Checkbox 'Theo thứ tự file' (✓: tuần tự; ✗: ngẫu nhiên trong mỗi màu, vẫn theo thứ tự màu)
    - Nút Load File + nhãn tên file
    - Dữ liệu: raw_points + color_groups
    """
    def __init__(self, parent: tk.Widget, idx: int):
        self.idx = idx
        self.frame = tk.Frame(parent)
        self.frame.pack(fill=tk.X, padx=8, pady=4)

        tk.Label(self.frame, text=f"Layer {idx+1}").grid(row=0, column=0, padx=4, sticky="w")

        tk.Label(self.frame, text="x:").grid(row=0, column=1, sticky="e")
        self.x_var = tk.StringVar(value="0")
        tk.Entry(self.frame, textvariable=self.x_var, width=7).grid(row=0, column=2, padx=4)

        tk.Label(self.frame, text="y:").grid(row=0, column=3, sticky="e")
        self.y_var = tk.StringVar(value="0")
        tk.Entry(self.frame, textvariable=self.y_var, width=7).grid(row=0, column=4, padx=4)

        self.ordered_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.frame, text="Theo thứ tự file", variable=self.ordered_var)\
            .grid(row=0, column=5, padx=6)

        self.btn_load = tk.Button(self.frame, text="Load File", command=self.load_file)
        self.btn_load.grid(row=0, column=6, padx=6)

        self.file_label = tk.Label(self.frame, text="(chưa chọn file)", anchor="w")
        self.file_label.grid(row=0, column=7, padx=6, sticky="w")

        self.file_path: Optional[str] = None
        self.raw_points: Optional[List[PointDef]] = None
        self.color_groups: Optional[List[Tuple[str, List[Tuple[int,int]]]]] = None

    def load_file(self):
        path = filedialog.askopenfilename(
            title="Chọn file TXT của layer",
            filetypes=[("Text", "*.txt"), ("Tất cả", "*.*")]
        )
        if not path:
            return
        try:
            self.raw_points = parse_points_txt(path)
            self.color_groups = parse_color_groups_txt(path)
            if not self.raw_points:
                messagebox.showwarning("Cảnh báo", "File không có dữ liệu điểm hợp lệ.")
            self.file_path = path
            self.file_label.config(text=os.path.basename(path))
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không đọc được file:\n{e}")

    def get_start_xy(self) -> Optional[Tuple[int,int]]:
        try:
            return int(self.x_var.get().strip()), int(self.y_var.get().strip())
        except ValueError:
            return None

# ---------------------------
# App chính
# ---------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Layer Painter – Ordered vs Random-in-Color")
        self.geometry("1100x700")

        self.bg_img: Optional[Image.Image] = None
        self.tkimg: Optional[ImageTk.PhotoImage] = None
        self.layers: List[LayerRow] = []

        # Toolbar
        toolbar = tk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)
        tk.Button(toolbar, text="Load Background", command=self.load_background).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Add Layer", command=self.add_layer).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Preview", command=self.preview_layers).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="Export Snapshot", command=self.export_snapshots).pack(side=tk.LEFT, padx=4)

        self.info_var = tk.StringVar(value="Chưa có background.")
        tk.Label(toolbar, textvariable=self.info_var, anchor="w").pack(side=tk.LEFT, padx=12)

        # Layers panel
        layers_box = tk.LabelFrame(self, text="Layers")
        layers_box.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)
        self.layers_container = tk.Frame(layers_box)
        self.layers_container.pack(fill=tk.X)

        # Viewer
        viewer = tk.Frame(self)
        viewer.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.canvas = tk.Canvas(viewer, bg="#eaeaea")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll = tk.Scrollbar(viewer, orient=tk.VERTICAL, command=self.canvas.yview)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        xscroll = tk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.canvas_img_id = None

    # ---------- Actions ----------

    def load_background(self):
        path = filedialog.askopenfilename(
            title="Chọn ảnh background",
            filetypes=[("Ảnh", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tiff;*.webp"),
                       ("Tất cả", "*.*")]
        )
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không mở được ảnh:\n{e}")
            return
        self.bg_img = img
        self._show_image(img)
        w, h = img.size
        self.info_var.set(f"Background: {os.path.basename(path)} | {w}×{h} px")

    def add_layer(self):
        self.layers.append(LayerRow(self.layers_container, len(self.layers)))

    def _show_image(self, img_rgba: Image.Image):
        w, h = img_rgba.size
        self.canvas.delete("all")
        self.tkimg = ImageTk.PhotoImage(img_rgba)
        self.canvas_img_id = self.canvas.create_image(0, 0, image=self.tkimg, anchor="nw")
        self.canvas.config(scrollregion=(0, 0, w, h))

    # ---------- Build sequences ----------

    def build_abs_points_for_preview(self, lr: LayerRow, W: int, H: int) -> List[Tuple[int,int,Tuple[int,int,int,int]]]:
        """Trả về list điểm tuyệt đối cho Preview theo chế độ checkbox."""
        if not lr.file_path or not lr.raw_points:
            return []
        start = lr.get_start_xy()
        if start is None:
            return []
        start_x, start_y = start

        if lr.ordered_var.get():
            # Theo đúng thứ tự điểm trong file
            pts = lr.raw_points
        else:
            # Ngẫu nhiên trong từng màu, nhưng theo thứ tự các màu
            if not lr.color_groups:
                return []
            pts = []
            for color_hex, coords in lr.color_groups:
                group = [(r, c, color_hex) for (r, c) in coords]
                random.shuffle(group)
                pts.extend(group)

        abs_pts: List[Tuple[int,int,Tuple[int,int,int,int]]] = []
        for (row, col, color_hex) in pts:
            x = start_x + (col - 1)
            y = start_y + (row - 1)
            if 0 <= x < W and 0 <= y < H:
                abs_pts.append((x, y, hex_to_rgba(color_hex)))
        return abs_pts

    def build_layer_state_for_export(self, lr: LayerRow, W: int, H: int) -> Dict[str, Any]:
        """
        Trả về state cho một layer khi Export:
          - mode="ordered": dùng 'pts_abs' (list) + 'idx'
          - mode="bycolor": dùng 'groups_abs' (list các nhóm theo thứ tự màu, mỗi nhóm đã shuffle) + 'ptr_color' + 'idxs'
        """
        state: Dict[str, Any] = {"mode": "empty"}
        if not lr.file_path or not lr.raw_points or lr.get_start_xy() is None:
            return state
        start_x, start_y = lr.get_start_xy()

        if lr.ordered_var.get():
            # Mode ordered: giữ nguyên thứ tự điểm
            pts_abs: List[Tuple[int,int,Tuple[int,int,int,int]]] = []
            for (row, col, color_hex) in lr.raw_points:
                x = start_x + (col - 1)
                y = start_y + (row - 1)
                if 0 <= x < W and 0 <= y < H:
                    pts_abs.append((x, y, hex_to_rgba(color_hex)))
            if pts_abs:
                state = {"mode": "ordered", "pts_abs": pts_abs, "idx": 0}
        else:
            # Mode bycolor: theo thứ tự màu, random trong từng màu
            if not lr.color_groups:
                return state
            groups_abs: List[Tuple[str, List[Tuple[int,int]]]] = []
            for color_hex, coords in lr.color_groups:
                abs_coords = []
                for (row, col) in coords:
                    x = start_x + (col - 1)
                    y = start_y + (row - 1)
                    if 0 <= x < W and 0 <= y < H:
                        abs_coords.append((x, y))
                if abs_coords:
                    random.shuffle(abs_coords)  # random trong màu
                    groups_abs.append((color_hex, abs_coords))
            if groups_abs:
                state = {"mode": "bycolor", "groups_abs": groups_abs, "ptr_color": 0, "idxs": [0]*len(groups_abs)}
        return state

    # ---------- Preview ----------

    def preview_layers(self):
        if self.bg_img is None:
            messagebox.showwarning("Chú ý", "Hãy Load Background trước.")
            return

        base = self.bg_img.copy()
        arr = np.array(base, dtype=np.uint8)
        H, W, _ = arr.shape

        total_drawn = 0
        for lr in self.layers:
            pts_abs = self.build_abs_points_for_preview(lr, W, H)
            for (x, y, rgba) in pts_abs:
                r,g,b,a = rgba
                arr[y, x, 0] = r
                arr[y, x, 1] = g
                arr[y, x, 2] = b
                arr[y, x, 3] = a
                total_drawn += 1

        out_img = Image.fromarray(arr, mode="RGBA")
        self._show_image(out_img)
        self.info_var.set(f"Preview: đã vẽ {total_drawn} pixel từ {len(self.layers)} layer.")

    # ---------- Export Snapshot ----------

    def export_snapshots(self):
        if self.bg_img is None:
            messagebox.showwarning("Chú ý", "Hãy Load Background trước.")
            return

        out_dir = filedialog.askdirectory(title="Chọn thư mục lưu snapshot")
        if not out_dir:
            return

        acc_arr = np.array(self.bg_img.copy(), dtype=np.uint8)
        H, W, _ = acc_arr.shape

        # Chuẩn bị state theo layer
        layer_states = [self.build_layer_state_for_export(lr, W, H) for lr in self.layers]
        if not any((st.get("mode") in ("ordered", "bycolor")) for st in layer_states):
            messagebox.showwarning("Chú ý", "Không có layer hợp lệ để xuất snapshot.")
            return

        def any_remaining() -> bool:
            for st in layer_states:
                mode = st.get("mode")
                if mode == "ordered":
                    if st["idx"] < len(st["pts_abs"]):
                        return True
                elif mode == "bycolor":
                    groups_abs = st["groups_abs"]
                    idxs = st["idxs"]
                    for gi, (_, pts) in enumerate(groups_abs):
                        if idxs[gi] < len(pts):
                            return True
            return False

        def next_point_from_layer(st):
            mode = st.get("mode")
            if mode == "ordered":
                idx = st["idx"]
                pts_abs = st["pts_abs"]
                if idx < len(pts_abs):
                    st["idx"] += 1
                    return pts_abs[idx]  # (x, y, rgba)
                return None
            elif mode == "bycolor":
                groups_abs = st["groups_abs"]  # [(color_hex, [(x,y),...]), ...]
                idxs = st["idxs"]
                ptr = st["ptr_color"]
                total_groups = len(groups_abs)
                for _ in range(total_groups):
                    color_hex, coords = groups_abs[ptr]
                    i = idxs[ptr]
                    if i < len(coords):
                        x, y = coords[i]
                        idxs[ptr] += 1
                        # không đổi ptr nếu còn điểm trong nhóm
                        from_hex = hex_to_rgba(color_hex)
                        return (x, y, from_hex)
                    else:
                        ptr = (ptr + 1) % total_groups
                        st["ptr_color"] = ptr
                return None
            return None

        snap_id = 1
        total_applied = 0

        while any_remaining():
            applied_this_image = 0

            # Lấy điểm theo round-robin giữa các layer cho đến khi áp dụng được 5 pixel
            # (bỏ qua các điểm không làm thay đổi ảnh)
            while applied_this_image < 5 and any_remaining():
                progressed = False   # có tiêu thụ ít nhất 1 điểm nào đó không?
                for st in layer_states:
                    if applied_this_image >= 5:
                        break
                    pt = next_point_from_layer(st)
                    if pt is None:
                        continue
                    progressed = True  # đã tiêu thụ 1 điểm (dù có vẽ hay bỏ qua)
                    x, y, rgba = pt
                    # Nếu màu trùng với pixel hiện tại, bỏ qua (không tăng applied_this_image)
                    if tuple(acc_arr[y, x]) == rgba:
                        continue
                    # Áp dụng điểm (ghi thật)
                    r, g, b, a = rgba
                    acc_arr[y, x, 0] = r
                    acc_arr[y, x, 1] = g
                    acc_arr[y, x, 2] = b
                    acc_arr[y, x, 3] = a
                    applied_this_image += 1
                    total_applied += 1

                if not progressed:
                    # Không còn điểm nào để tiêu thụ
                    break

            if applied_this_image == 0:
                # Không thể áp dụng thêm thay đổi nào nữa
                break

            # Lưu ảnh snapshot
            img_to_save = Image.fromarray(acc_arr, mode="RGBA")
            fname = f"snapshot_{snap_id:06d}.png"
            out_path = os.path.join(out_dir, fname)
            try:
                img_to_save.save(out_path)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu {fname}:\n{e}")
                return
            snap_id += 1

        messagebox.showinfo(
            "Hoàn tất",
            f"Đã xuất {snap_id-1} ảnh snapshot vào:\n{out_dir}\n"
            f"Tổng số pixel đã cập nhật: {total_applied}"
        )

# ---------------------------
# Run
# ---------------------------

if __name__ == "__main__":
    App().mainloop()
