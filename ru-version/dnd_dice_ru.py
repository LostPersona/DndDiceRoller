from __future__ import annotations
import math, platform, sys, threading, time, tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from typing import List, Tuple
from random import SystemRandom
from itertools import cycle

sysrand = SystemRandom()

if platform.system() == "Windows":
    import winsound
    playsound = None
else:
    try:
        from playsound import playsound
    except ImportError:
        playsound = None

def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return str(Path(base, rel))

SOUND_FILE = Path(resource_path("sounds/dice_sound.wav"))

def regular_polygon(n: int, size: int = 50, angle: float = 0) -> List[Tuple[float, float]]:
    cx = cy = size / 2
    r = size / 2 * 0.85
    rot = -math.pi / 2 + (math.pi / 4 if n == 4 else 0) + angle
    return [
        (cx + r * math.cos(2 * math.pi * i / n + rot),
         cy + r * math.sin(2 * math.pi * i / n + rot))
        for i in range(n)
    ]

class DiceRoller:
    DICE_SIDES = {"d4": 4, "d6": 6, "d8": 8, "d10": 10, "d12": 12, "d20": 20, "d100": 100}
    SPRITE_SIDES = {4: 3, 6: 4, 8: 6, 10: 6, 12: 6, 20: 8, 100: 8} # to fix
    DIE_COLOURS = {4: "#e0f7fa", 6: "#fff9c4", 8: "#ffe0b2", 10: "#dcedc8", # to fix
                   12: "#d1c4e9", 20: "#ffcdd2", 100: "#c8e6c9"}

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Контроль мастера — Кубы — Создано LostPersona")
        self._icon_img: tk.PhotoImage | None = None
        try:
            ico_path = resource_path("files/d20.ico")
            self._icon_img = tk.PhotoImage(file=ico_path)
            self.root.iconphoto(True, self._icon_img)
        except Exception:
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass
        self._build_display_window()
        self._build_control_ui()

    def _build_display_window(self):
        self.display = tk.Toplevel(self.root)
        self.display.title("Игроки — Результаты броска — Создано LostPersona")
        self.display.geometry("1020x520")

        if self._icon_img:
            try:
                self.display.iconphoto(True, self._icon_img)
            except Exception:
                pass

        self.die_type_label = tk.Label(self.display, text="Тип: —",
                                       font=("Helvetica", 14, "bold"),
                                       fg="gray25", bg=self.display.cget("bg"))
        self.die_type_label.pack(anchor="nw", padx=12, pady=10)

        self.dice_frame = ttk.Frame(self.display, padding=10)
        self.dice_frame.pack(expand=True, fill="both")

        self.total_text = tk.Text(self.display, height=1, bd=0,
                                  bg=self.display.cget("bg"),
                                  font=("Helvetica", 28, "bold"),
                                  highlightthickness=0)
        self.total_text.tag_configure("mod", foreground="red")
        self.total_text.config(state="disabled")
        self.total_text.pack(side="bottom", pady=6, fill="x")

    def _build_control_ui(self):
        fr = ttk.Frame(self.root, padding=10)
        fr.pack(fill="x")
        ttk.Label(fr, text="Тип куба:").grid(row=0, column=0, sticky="w")
        self.die_var = tk.StringVar(value="d20")
        ttk.OptionMenu(fr, self.die_var, "d20", *self.DICE_SIDES.keys()).grid(
            row=0, column=1, sticky="w", padx=5)
        ttk.Label(fr, text="Количество:").grid(row=1, column=0, sticky="w")
        self.qty_var = tk.StringVar(value="1")
        ttk.Spinbox(fr, from_=1, to=50, textvariable=self.qty_var, width=6)\
            .grid(row=1, column=1, sticky="w", padx=5)
        ttk.Label(fr, text="Модификатор:").grid(row=2, column=0, sticky="w")
        self.mod_var = tk.StringVar()
        ttk.Entry(fr, textvariable=self.mod_var, width=8)\
            .grid(row=2, column=1, sticky="w", padx=5)
        ttk.Label(fr, text="(± число, опц.)").grid(row=2, column=2, sticky="w")
        self.mode_var = tk.StringVar(value="random")
        ttk.Radiobutton(fr, text="Случайно", variable=self.mode_var, value="random")\
            .grid(row=3, column=0, sticky="w")
        ttk.Radiobutton(fr, text="Фиксация", variable=self.mode_var, value="force")\
            .grid(row=3, column=1, sticky="w")
        ttk.Label(fr, text="Фикс. значения:").grid(row=4, column=0, sticky="w")
        self.force_entry = ttk.Entry(fr, width=28)
        self.force_entry.grid(row=4, column=1, sticky="w", padx=5)
        ttk.Label(fr, text="(через запятую)").grid(row=4, column=2, sticky="w")
        ttk.Button(fr, text="Бросить!", command=self.roll).grid(
            row=5, column=0, columnspan=3, pady=12)
        self.history = tk.Text(self.root, height=12, width=70, state="disabled")
        self.history.pack(padx=10, pady=5, fill="both", expand=True)

    def roll(self):
        try:
            qty = max(1, int(self.qty_var.get()))
        except ValueError:
            messagebox.showerror("Ошибка", "Количество должно быть целым ≥ 1.")
            return
        try:
            mod = int(self.mod_var.get().strip() or 0)
        except ValueError:
            messagebox.showerror("Ошибка", "Модификатор должен быть целым числом.")
            return

        sides = self.DICE_SIDES[self.die_var.get()]
        if self.mode_var.get() == "random":
            results = [sysrand.randint(1, sides) for _ in range(qty)]
        else:
            results = self._parse_forced_results(qty, sides)
            if results is None:
                return

        total = sum(results) + mod
        self._play_sound()
        self._update_display(results, sides, mod, total)
        self._append_history(f"{qty}×{self.die_var.get()} → "
                             f"{' + '.join(map(str, results))}"
                             f"{f' + {mod}' if mod else ''} = {total}\n")

    def _update_display(self, results, sides, mod, total):
        self.die_type_label.config(text=f"Тип: {self.die_var.get()}")
        for w in self.dice_frame.winfo_children():
            w.destroy()
        self.display.update_idletasks()
        area_w = self.dice_frame.winfo_width() or 1
        area_h = self.dice_frame.winfo_height() or 1
        base = 200 if sides < 100 else 220
        pad = 16

        while True:
            cols = max(1, area_w // (base + pad))
            rows = -(-len(results) // cols)
            if rows * (base + pad) <= area_h:
                break
            base = int(base * 0.9)

        for r in range(rows):
            row_frame = ttk.Frame(self.dice_frame)
            row_frame.pack(anchor="center")
            for c in range(cols):
                idx = r * cols + c
                if idx >= len(results): break
                die_canvas = self._animated_die(row_frame, sides, results[idx], base)
                die_canvas.pack(side="left", padx=pad // 2, pady=pad // 2)

        self.total_text.config(state="normal")
        self.total_text.delete("1.0", "end")
        for i, v in enumerate(results):
            self.total_text.insert("end", str(v))
            if i != len(results) - 1:
                self.total_text.insert("end", " + ")
        if mod:
            sign = "+" if mod >= 0 else "-"
            self.total_text.insert("end", f" {sign} ")
            self.total_text.insert("end", str(abs(mod)), ("mod",))
        if len(results) + (1 if mod else 0) > 1:
            self.total_text.insert("end", f" = {total}")
        self.total_text.config(state="disabled")

    def _animated_die(self, parent, sides, value, size):
        canvas = tk.Canvas(parent, width=size, height=size, highlightthickness=0)
        n = self.SPRITE_SIDES.get(sides, 12)
        angle_values = [i * math.pi / 10 for i in range(20)]
        frames = cycle(angle_values)
        start_time = time.time()

        def animate():
            if time.time() - start_time > 0.1:
                canvas.delete("all")
                canvas.create_polygon(
                    regular_polygon(n, size),
                    fill=self.DIE_COLOURS.get(sides, "white"),
                    outline="black", width=2
                )
                canvas.create_text(size / 2, size / 2, text=str(value),
                                   font=("Helvetica", int(size * 0.12), "bold"))
                return
            angle = next(frames)
            canvas.delete("all")
            canvas.create_polygon(
                regular_polygon(n, size, angle),
                fill=self.DIE_COLOURS.get(sides, "white"),
                outline="black", width=2
            )
            canvas.create_text(size / 2, size / 2, text=str(value),
                               font=("Helvetica", int(size * 0.12), "bold"))
            canvas.after(20, animate)

        animate()
        return canvas

    def _play_sound(self):
        if not SOUND_FILE.exists():
            self._warn_once("no_file", f"Не найден файл звука:\n{SOUND_FILE}")
            return
        if platform.system() == "Windows":
            winsound.PlaySound(str(SOUND_FILE),
                               winsound.SND_FILENAME | winsound.SND_ASYNC)
        elif playsound:
            threading.Thread(target=lambda: playsound(str(SOUND_FILE)),
                             daemon=True).start()
        else:
            self._warn_once("no_sound", "Нет поддержки звука.")

    _warned: set[str] = set()
    def _warn_once(self, key: str, msg: str):
        if key in self._warned:
            return
        self._warned.add(key)
        messagebox.showwarning("Внимание", msg)

    def _parse_forced_results(self, qty, sides):
        txt = self.force_entry.get().strip()
        if not txt:
            messagebox.showerror("Нет значений", "Не введены фиксированные значения.")
            return None
        try:
            vals = [int(x) for x in txt.split(",") if x.strip()]
        except ValueError:
            messagebox.showerror("Ошибка", "Допустимы только целые числа.")
            return None
        if len(vals) == 1:
            vals *= qty
        if len(vals) != qty:
            messagebox.showerror("Ошибка", f"Введите одно или ровно {qty} чисел.")
            return None
        bad = [v for v in vals if not (1 <= v <= sides)]
        if bad:
            messagebox.showerror("Ошибка", f"Значения {bad} вне диапазона 1–{sides}.")
            return None
        return vals

    def _append_history(self, line):
        self.history.config(state="normal")
        self.history.insert("end", line)
        self.history.see("end")
        self.history.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    DiceRoller(root)
    root.mainloop()
