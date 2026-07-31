import io
import sys
import time
import threading
import tkinter as tk
from datetime import datetime

import requests
from PIL import Image, ImageTk

API = "http://localhost:8000/api/access/state"
NAME_URL = "http://localhost:8000/api/access/name"

BG = "#050505"
CARD = "#0d0d0d"
CARD2 = "#0a1a0a"
BORDER = "#1a3a1a"
GREEN = "#00cc66"
GREEN_DIM = "#004400"
RED = "#ff4444"
RED_DIM = "#2a0000"
AMBER = "#ffaa00"
AMBER_DIM = "#332200"
TEXT = "#e0e0e0"
TEXT_DIM = "#55aa55"

FONT = "Segoe UI"


class AccessApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Acceso Personal - IoT Security")
        self.configure(bg=BG)
        self.geometry("520x980")
        self.minsize(440, 700)

        self.photo_cache = {}
        self.phase = ""
        self.banner_anim = False
        self.dots = 0

        self._build_ui()
        self.after(300, self._poll)
        self._clock()

    # ---------------- UI ----------------
    def _build_ui(self):
        # Topbar
        top = tk.Frame(self, bg=CARD, height=64, highlightbackground=GREEN, highlightthickness=2)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="ACCESO PERSONAL", bg=CARD, fg=TEXT,
                 font=(FONT, 15, "bold")).pack(side="left", padx=16)
        tk.Label(top, text="IoT Security Monitor", bg=CARD, fg=TEXT_DIM,
                 font=(FONT, 9)).place(x=16, y=38)

        self.pill = tk.Label(top, text="SISTEMA LISTO", bg=GREEN_DIM, fg=GREEN,
                             font=(FONT, 9, "bold"), padx=12, pady=5)
        self.pill.pack(side="right", padx=12)

        # Main content
        content = tk.Frame(self, bg=BG)
        content.pack(fill="both", expand=True, padx=14, pady=12)

        # Phase card
        self.phase_card = tk.Frame(content, bg=CARD, highlightbackground=BORDER,
                                   highlightthickness=1, height=360)
        self.phase_card.pack(fill="x", pady=(0, 12))
        self.phase_card.pack_propagate(False)

        self.phase_widgets = {}  # {name: widget}
        self._build_idle()
        self._build_scanning()
        self._build_register_face()
        self._build_register_rfid()
        self._build_verify_rfid()
        self._build_result()

        # Legend
        legend = tk.Frame(content, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        legend.pack(fill="x", pady=(0, 12))
        tk.Label(legend, text="FUNCIONES DE LOS BOTONES DEL ESP32", bg=CARD, fg=GREEN,
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        self.card_login = self._btn_card(legend, "LOGIN", "Identificarse con tarjeta RFID o reconocimiento facial", GREEN, GREEN_DIM)
        self.card_register = self._btn_card(legend, "REGISTRAR", "Registrar nuevo personal: rostro + tarjeta", AMBER, AMBER_DIM)
        self.card_cancel = self._btn_card(legend, "CANCELAR", "Cancelar la operación actual", RED, RED_DIM)

        self._show("idle")

        # Recent
        recent = tk.Frame(content, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        recent.pack(fill="both", expand=True)
        tk.Label(recent, text="ULTIMOS ACCESOS", bg=CARD, fg=GREEN,
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.recent_box = tk.Frame(recent, bg=CARD)
        self.recent_box.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # Footer
        foot = tk.Frame(self, bg=CARD, height=44, highlightbackground=BORDER, highlightthickness=1)
        foot.pack(fill="x")
        foot.pack_propagate(False)
        self.clock = tk.Label(foot, bg=CARD, fg=TEXT_DIM, font=(FONT, 12, "bold"))
        self.clock.pack(side="left", padx=14)
        self.date = tk.Label(foot, bg=CARD, fg=TEXT_DIM, font=(FONT, 9))
        self.date.pack(side="right", padx=14)

        self.bind("<F11>", self._toggle_fullscreen)

    def _btn_card(self, parent, title, desc, color, dim):
        card = tk.Frame(parent, bg=CARD2, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=12, pady=5)
        tk.Label(card, text=title, bg=CARD2, fg=color, font=(FONT, 12, "bold"),
                 width=12, anchor="w").pack(side="left", padx=(12, 6), pady=8)
        tk.Label(card, text=desc, bg=CARD2, fg=TEXT_DIM, font=(FONT, 9),
                 anchor="w", justify="left").pack(side="left", pady=8)
        return card

    def _center_text(self, parent, text, fg, size, pady=6):
        return tk.Label(parent, text=text, bg=CARD, fg=fg, font=(FONT, size, "bold"))

    # --- Views ---
    def _build_idle(self):
        w = tk.Frame(self.phase_card, bg=CARD)
        tk.Label(w, text="\U0001F464", bg=CARD, font=(FONT, 58)).pack(pady=(40, 6))
        tk.Label(w, text="Esperando identificación", bg=CARD, fg=TEXT,
                 font=(FONT, 19, "bold")).pack()
        tk.Label(w, text="Coloque su tarjeta RFID en el lector\n"
                         "o presione LOGIN para reconocimiento facial",
                 bg=CARD, fg=TEXT_DIM, font=(FONT, 11), justify="center").pack(pady=8)
        self.phase_widgets["idle"] = w

    def _build_scanning(self):
        w = tk.Frame(self.phase_card, bg=CARD)
        self.spinner = tk.Canvas(w, width=64, height=64, bg=CARD, highlightthickness=0)
        self.spinner.pack(pady=(50, 14))
        self.spin_angle = 0
        tk.Label(w, text="Verificando identidad", bg=CARD, fg=TEXT,
                 font=(FONT, 19, "bold")).pack()
        self.spin_sub = tk.Label(w, text="Mirando a la cámara, no se mueva", bg=CARD,
                                 fg=TEXT_DIM, font=(FONT, 11))
        self.spin_sub.pack(pady=8)
        self.phase_widgets["scanning_face"] = w

    def _build_register_face(self):
        w = tk.Frame(self.phase_card, bg=CARD)
        tk.Label(w, text="\U0001F916", bg=CARD, font=(FONT, 58)).pack(pady=(40, 6))
        tk.Label(w, text="Registrando rostro", bg=CARD, fg=TEXT,
                 font=(FONT, 19, "bold")).pack()
        tk.Label(w, text="Mire a la cámara por unos segundos", bg=CARD,
                 fg=TEXT_DIM, font=(FONT, 11)).pack(pady=8)
        self.phase_widgets["register_face"] = w

    def _build_register_rfid(self):
        w = tk.Frame(self.phase_card, bg=CARD)
        tk.Label(w, text="\U0001F3B4", bg=CARD, font=(FONT, 54)).pack(pady=(36, 6))
        tk.Label(w, text="Acerca la tarjeta RFID", bg=CARD, fg=TEXT,
                 font=(FONT, 19, "bold")).pack()
        tk.Label(w, text="Coloque la tarjeta en el lector para\nvincularla a su rostro",
                 bg=CARD, fg=TEXT_DIM, font=(FONT, 11), justify="center").pack(pady=8)

        row = tk.Frame(w, bg=CARD)
        row.pack(pady=10)
        self.name_entry = tk.Entry(row, bg=BG, fg=TEXT, insertbackground=GREEN,
                                   relief="flat", font=(FONT, 11), width=26)
        self.name_entry.insert(0, "Nombre del empleado (opcional)")
        self.name_entry.pack(side="left", padx=(0, 6), ipady=5)
        self.name_entry.bind("<FocusIn>", lambda e: self.name_entry.delete(0, "end")
                             if self.name_entry.get() == "Nombre del empleado (opcional)" else None)
        self.name_btn = tk.Button(row, text="Guardar", bg=GREEN_DIM, fg=GREEN,
                                  font=(FONT, 10, "bold"), relief="flat",
                                  activebackground=GREEN, activeforeground=BG, padx=10,
                                  command=self._save_name)
        self.name_btn.pack(side="left", ipady=3)
        self.phase_widgets["register_rfid"] = w

        self._build_result()

    def _build_verify_rfid(self):
        w = tk.Frame(self.phase_card, bg=CARD)
        tk.Label(w, text="\U0001F3B4", bg=CARD, font=(FONT, 54)).pack(pady=(36, 6))
        tk.Label(w, text="Acerca su tarjeta", bg=CARD, fg=TEXT,
                 font=(FONT, 19, "bold")).pack()
        self.verify_name = tk.Label(w, text="Confirmando identidad...", bg=CARD,
                                    fg=GREEN, font=(FONT, 12, "bold"))
        self.verify_name.pack(pady=6)
        tk.Label(w, text="Para acceder se necesita la tarjeta y el rostro",
                 bg=CARD, fg=TEXT_DIM, font=(FONT, 10)).pack(pady=4)
        self.phase_widgets["verify_rfid"] = w

    def _build_result(self):
        w = tk.Frame(self.phase_card, bg=CARD)
        self.result_photo = tk.Label(w, bg=CARD)
        self.result_photo.pack(pady=(18, 2))
        self.result_name = tk.Label(w, text="---", bg=CARD, fg=TEXT,
                                    font=(FONT, 20, "bold"))
        self.result_name.pack()
        self.result_role = tk.Label(w, text="---", bg=CARD, fg=TEXT_DIM, font=(FONT, 11))
        self.result_role.pack()
        self.result_banner = tk.Label(w, text="", font=(FONT, 20, "bold"),
                                      bg=GREEN_DIM, fg=GREEN, padx=20, pady=10)
        self.result_banner.pack(pady=10)
        self.result_msg = tk.Label(w, text="", bg=CARD, fg=TEXT, font=(FONT, 11))
        self.result_msg.pack()
        self.result_uid = tk.Label(w, text="", bg=CARD, fg=TEXT_DIM, font=(FONT, 9))
        self.result_uid.pack()
        self.phase_widgets["result"] = w

    # ---------------- Helpers ----------------
    def _show(self, name):
        for key, wid in self.phase_widgets.items():
            wid.pack_forget()
        self.phase_widgets[name].pack(fill="both", expand=True)
        self.phase = name
        if name == "result":
            self._banner_animate()
        self._highlight_legend()

    def _highlight_legend(self):
        active = self.phase in ("scanning_face", "verify_rfid")
        self.card_login.configure(highlightbackground=GREEN if active else BORDER,
                                  highlightthickness=2 if active else 1)
        active = self.phase in ("register_face", "register_rfid")
        self.card_register.configure(highlightbackground=AMBER if active else BORDER,
                                     highlightthickness=2 if active else 1)
        active = self.phase in ("scanning_face", "register_face", "register_rfid", "verify_rfid")
        self.card_cancel.configure(highlightbackground=RED if active else BORDER,
                                   highlightthickness=2 if active else 1)

    def _banner_animate(self):
        self.banner_anim = not self.banner_anim
        if self.phase != "result":
            return
        banner = self.result_banner
        if banner.cget("text") in ("ACCESO CONCEDIDO", "REGISTRADO"):
            banner.configure(bg=GREEN_DIM if self.banner_anim else GREEN,
                             fg=GREEN if self.banner_anim else "#052b16")
        elif banner.cget("text") == "ACCESO DENEGADO":
            banner.configure(bg=RED_DIM if self.banner_anim else RED,
                             fg=RED if self.banner_anim else "#2b0505")
        self.after(400, self._banner_animate)

    def _save_name(self):
        name = self.name_entry.get().strip()
        if name in ("", "Nombre del empleado (opcional)"):
            return
        def worker():
            try:
                requests.post(NAME_URL, json={"name": name}, timeout=3)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()
        self.name_btn.configure(text="Guardado ✓")

    def _set_pill(self, text, kind):
        colors = {
            "ok": (GREEN_DIM, GREEN),
            "error": (RED_DIM, RED),
            "working": (AMBER_DIM, AMBER),
        }
        bg, fg = colors.get(kind, (GREEN_DIM, GREEN))
        self.pill.configure(text=text, bg=bg, fg=fg)

    # ---------------- Polling ----------------
    def _poll(self):
        def worker():
            try:
                r = requests.get(API, timeout=3)
                return r.json()
            except Exception:
                return None
        threading.Thread(target=lambda: self.after(0, self._apply, worker()), daemon=True).start()
        self.after(500, self._poll)

    def _apply(self, state):
        if state is None:
            self._set_pill("SERVIDOR NO DISPONIBLE", "error")
            return
        self._set_pill(state.get("pill", "SISTEMA LISTO"), state.get("pillKind", ""))
        self._render_recent(state.get("recent", []))
        new_phase = state.get("phase", "idle")
        if new_phase != self.phase:
            self._show(new_phase)
        if new_phase == "result":
            self._render_result(state.get("result", {}))
        if new_phase == "verify_rfid":
            verify = state.get("verify") or {}
            name = verify.get("name", "")
            self.verify_name.configure(
                text=("Persona detectada: " + name) if name else "Confirmando identidad...")

    def _render_recent(self, recent):
        for child in self.recent_box.winfo_children():
            child.destroy()
        if not recent:
            tk.Label(self.recent_box, text="Sin actividad reciente", bg=CARD,
                     fg=TEXT_DIM, font=(FONT, 10)).pack(anchor="w", pady=3)
            return
        methods = {"rfid": "RFID", "facial": "FACIAL", "manual": "MANUAL", "dual": "DOBLE"}
        for r in recent[:6]:
            row = tk.Frame(self.recent_box, bg=CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=r.get("person", "?"), bg=CARD, fg=TEXT,
                     font=(FONT, 10, "bold"), width=18, anchor="w").pack(side="left")
            tk.Label(row, text=methods.get(r.get("method"), r.get("method", "")),
                     bg=CARD, fg=TEXT_DIM, font=(FONT, 8), width=7, anchor="w").pack(side="left")
            ok = r.get("status") == "authorized"
            tk.Label(row, text="OK" if ok else "DENEGADO", bg=CARD,
                     fg=GREEN if ok else RED, font=(FONT, 9, "bold"),
                     width=9, anchor="e").pack(side="left", expand=True)
            tk.Label(row, text=r.get("time", ""), bg=CARD, fg=TEXT_DIM,
                     font=(FONT, 9)).pack(side="right")

    def _render_result(self, res):
        user = res.get("user") or {}
        self.result_name.configure(text=user.get("name", "Desconocido"))
        self.result_role.configure(text=user.get("role", "---"))

        if res.get("registered"):
            banner = "REGISTRADO"
        elif res.get("authorized"):
            banner = "ACCESO CONCEDIDO"
        else:
            banner = "ACCESO DENEGADO"
        self.result_banner.configure(text=banner)
        self.result_msg.configure(text=res.get("message", ""))
        self.result_uid.configure(text=("UID: " + res["uid"]) if res.get("uid") else "")

        photo_url = res.get("photo")
        img = self._load_photo(photo_url) if photo_url else None
        if img is not None:
            self.result_photo.configure(image=img)
            self.result_photo.image = img
            self.result_photo.pack(pady=(18, 2))
        else:
            icon = "\U0001F60E" if res.get("authorized") else "\U0001F625"
            self.result_photo.configure(image="", text=icon, font=(FONT, 54),
                                        fg=GREEN if res.get("authorized") else RED)
            self.result_photo.pack(pady=(18, 2))

    def _load_photo(self, url):
        if url in self.photo_cache:
            return self.photo_cache[url]
        try:
            r = requests.get("http://localhost:8000" + url, timeout=3)
            img = Image.open(io.BytesIO(r.content)).resize((150, 150), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.photo_cache[url] = photo
            return photo
        except Exception:
            return None

    # ---------------- Misc ----------------
    def _clock(self):
        now = datetime.now()
        self.clock.configure(text=now.strftime("%H:%M:%S"))
        self.date.configure(text=now.strftime("%A, %d de %B de %Y"))
        self.after(1000, self._clock)

    def _toggle_fullscreen(self, _=None):
        self.attributes("-fullscreen", not self.attributes("-fullscreen"))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        API = f"http://{sys.argv[1]}/api/access/state"
    app = AccessApp()
    app.mainloop()
