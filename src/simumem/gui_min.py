from __future__ import annotations

import random
import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .simulador import Simulador
from .proceso import Proceso


class VentanaSimulador(tk.Tk):
    """
    Interfaz mínima y sobria para observar el simulador:
      - RAM: barra de uso + gráfica de % de uso en el tiempo.
      - Colas: LISTOS (FIFO) y Espera por memoria.
      - CPU: proceso actual y lista de finalizados.
      - Controles: Agregar aleatorio, Agregar manualmente, Paso, Iniciar/Pausar, Reiniciar.

    El reloj avanza con .after() (sin hilos).
    """

    def __init__(self, capacidad_mb: int = 1024) -> None:
        super().__init__()
        self.title("Simulador de Procesos en Memoria — Minimal")
        self.geometry("900x600")
        self.minsize(860, 560)

        # ----- Modelo y reloj
        self.sim = Simulador(capacidad_mb=capacidad_mb)
        self._reloj_corriendo = False
        self._intervalo_ms = 1000  # 1 segundo por tick
        self._contador_aleatorios = 0

        # ----- Estilos sobrios (oscuro)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background="#121212")
        style.configure("TLabel", background="#121212", foreground="#e6e6e6")
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Muted.TLabel", foreground="#9aa0a6")
        style.configure("TButton", padding=6)
        style.configure("Mem.Horizontal.TProgressbar", troughcolor="#1e1e1e")

        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Simulador de Gestión de Procesos (FIFO • 1 CPU)",
                  style="Header.TLabel").pack(anchor="w")

        # ----- RAM (barra + gráfica)
        marco_ram = ttk.Frame(root, padding=(0, 8, 0, 12))
        marco_ram.pack(fill="x")

        self.pb_ram = ttk.Progressbar(
            marco_ram, style="Mem.Horizontal.TProgressbar", orient="horizontal",
            mode="determinate", maximum=self.sim.memoria.capacidad_mb
        )
        self.pb_ram.pack(fill="x")

        self.lbl_ram = ttk.Label(marco_ram, text="RAM: 0 / 0 MB", style="Muted.TLabel")
        self.lbl_ram.pack(anchor="e", pady=(6, 0))

        # Gráfica de % uso RAM
        graf = ttk.Frame(root)
        graf.pack(fill="x", pady=(0, 8))
        self._hist_max = 80             # cantidad de puntos visibles
        self._hist_uso = []             # historial de % RAM
        self.fig = Figure(figsize=(6, 1.8), dpi=100, facecolor="#121212")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#1e1e1e")
        self.ax.set_ylim(0, 100)
        self.ax.set_xlim(0, self._hist_max - 1)
        self.ax.set_title("Uso de memoria (%)", color="#e6e6e6")
        self.ax.set_ylabel("% RAM", color="#e6e6e6")
        # Estética minimal: ticks claros, rejilla suave
        self.ax.tick_params(colors="#9aa0a6")
        self.ax.grid(True, color="#2a2a2a", linewidth=0.6)
        self.line, = self.ax.plot([], [], linewidth=2.0, color="red")  # línea del %RAM

        self.canvas = FigureCanvasTkAgg(self.fig, master=graf)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="x")

        # ----- Paneles (3 columnas)
        paneles = ttk.Frame(root)
        paneles.pack(fill="both", expand=True)

        self.tree_listos = self._crear_lista(paneles, "Cola LISTOS (FIFO)")
        self.tree_espera = self._crear_lista(paneles, "Espera de Memoria")
        self.tree_cpu = self._crear_lista(paneles, "CPU y Finalizados", dos_bloques=True)

        paneles.columnconfigure((0, 1, 2), weight=1)
        self.tree_listos.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.tree_espera.grid(row=0, column=1, sticky="nsew", padx=8)
        self.tree_cpu.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        # ----- Controles
        controles = ttk.Frame(root, padding=(0, 10, 0, 0))
        controles.pack(fill="x")

        self.btn_agregar_auto = ttk.Button(controles, text="Agregar aleatorio", command=self._agregar_aleatorio)
        self.btn_agregar_manual = ttk.Button(controles, text="Agregar manualmente", command=self._abrir_dialogo_proceso)
        self.btn_paso = ttk.Button(controles, text="Paso (1s)", command=self._paso_manual)
        self.btn_toggle = ttk.Button(controles, text="Iniciar", command=self._toggle)
        self.btn_reset = ttk.Button(controles, text="Reiniciar", command=self._reiniciar)

        self.btn_agregar_auto.pack(side="left")
        self.btn_agregar_manual.pack(side="left", padx=(6, 12))
        self.btn_paso.pack(side="left")
        self.btn_toggle.pack(side="left", padx=(6, 0))
        self.btn_reset.pack(side="right")

        # Primera actualización
        self._actualizar_vista()

    # ---------- Construcción de widgets auxiliares ----------

    def _crear_lista(self, parent: ttk.Frame, titulo: str, dos_bloques: bool = False) -> ttk.Frame:
        marco = ttk.Frame(parent)
        ttk.Label(marco, text=titulo).pack(anchor="w", pady=(0, 6))
        if not dos_bloques:
            cols = ("pid", "nombre", "mem", "dur", "restante")
            tree = ttk.Treeview(marco, columns=cols, show="headings", height=10)
            tree.heading("pid", text="PID")
            tree.heading("nombre", text="Nombre")
            tree.heading("mem", text="MB")
            tree.heading("dur", text="Dur(s)")
            tree.heading("restante", text="Rest(s)")
            tree.column("pid", width=46, anchor="center")
            tree.column("mem", width=52, anchor="e")
            tree.column("dur", width=66, anchor="e")
            tree.column("restante", width=66, anchor="e")
            tree.pack(fill="both", expand=True)
            setattr(self, f"_tree_{titulo}", tree)
        else:
            marco_up = ttk.Frame(marco)
            marco_dw = ttk.Frame(marco)
            marco_up.pack(fill="x")
            marco_dw.pack(fill="both", expand=True, pady=(8, 0))

            ttk.Label(marco_up, text="CPU (proceso en ejecución)", style="Muted.TLabel").pack(anchor="w")
            cols_cpu = ("pid", "nombre", "restante")
            self.tree_cpu_now = ttk.Treeview(marco_up, columns=cols_cpu, show="headings", height=1)
            for c, txt in zip(cols_cpu, ("PID", "Nombre", "Rest(s)")):
                self.tree_cpu_now.heading(c, text=txt)
            self.tree_cpu_now.column("pid", width=60, anchor="center")
            self.tree_cpu_now.column("restante", width=80, anchor="e")
            self.tree_cpu_now.pack(fill="x")

            ttk.Label(marco_dw, text="Finalizados", style="Muted.TLabel").pack(anchor="w")
            cols_fin = ("pid", "nombre", "duracion")
            self.tree_fin = ttk.Treeview(marco_dw, columns=cols_fin, show="headings", height=8)
            for c, txt in zip(cols_fin, ("PID", "Nombre", "Duración(s)")):
                self.tree_fin.heading(c, text=txt)
            self.tree_fin.column("pid", width=60, anchor="center")
            self.tree_fin.column("duracion", width=100, anchor="e")
            self.tree_fin.pack(fill="both", expand=True)

        return marco

    # ---------- Controles ----------

    def _toggle(self):
        self._reloj_corriendo = not self._reloj_corriendo
        self.btn_toggle.configure(text="Pausar" if self._reloj_corriendo else "Iniciar")
        if self._reloj_corriendo:
            self._tick_programado()

    def _tick_programado(self):
        if not self._reloj_corriendo:
            return
        self.sim.paso()
        self._actualizar_vista()
        self.after(self._intervalo_ms, self._tick_programado)

    def _paso_manual(self):
        if self._reloj_corriendo:
            return
        self.sim.paso()
        self._actualizar_vista()

    def _reiniciar(self):
        if messagebox.askyesno("Reiniciar", "¿Seguro que deseas reiniciar el simulador?"):
            cap = self.sim.memoria.capacidad_mb
            self.sim = Simulador(capacidad_mb=cap)
            self._reloj_corriendo = False
            self._hist_uso.clear()
            self.btn_toggle.configure(text="Iniciar")
            self._actualizar_vista()

    def _agregar_aleatorio(self):
        """Crea un proceso con nombre secuencial y recursos aleatorios."""
        self._contador_aleatorios += 1
        nombre = f"Proceso {self._contador_aleatorios}"
        memoria = random.randint(20, 1000)   # límite pedido: no pase de 300 MB
        duracion = random.randint(3, 15)    # segundos
        p = Proceso(nombre, memoria_mb=memoria, duracion_s=duracion)
        self.sim.agregar(p)
        self._actualizar_vista()

    def _abrir_dialogo_proceso(self):
        dlg = tk.Toplevel(self)
        dlg.title("Nuevo proceso")
        dlg.resizable(False, False)
        frm = ttk.Frame(dlg, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Nombre").grid(row=0, column=0, sticky="w")
        ttk.Label(frm, text="Memoria (MB)").grid(row=1, column=0, sticky="w")
        ttk.Label(frm, text="Duración (s)").grid(row=2, column=0, sticky="w")

        e_nombre = ttk.Entry(frm, width=28)
        e_mem = ttk.Entry(frm, width=12)
        e_dur = ttk.Entry(frm, width=12)
        e_nombre.grid(row=0, column=1, pady=4, sticky="we")
        e_mem.grid(row=1, column=1, pady=4, sticky="we")
        e_dur.grid(row=2, column=1, pady=4, sticky="we")
        e_nombre.focus_set()

        botones = ttk.Frame(frm)
        botones.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="e")
        ttk.Button(botones, text="Cancelar", command=dlg.destroy).pack(side="right")
        ttk.Button(
            botones, text="Agregar",
            command=lambda: self._confirmar_proceso(dlg, e_nombre.get(), e_mem.get(), e_dur.get())
        ).pack(side="right", padx=(0, 6))

        frm.columnconfigure(1, weight=1)

    def _confirmar_proceso(self, dlg: tk.Toplevel, nombre: str, mem_txt: str, dur_txt: str):
        try:
            memoria = int(mem_txt)
            duracion = int(dur_txt)
            if memoria <= 0 or duracion <= 0:
                raise ValueError
            if not nombre.strip():
                # Si no escriben nombre, generamos uno que no choque con los "aleatorios".
                nombre = f"Manual {len(self.sim.finalizados)+1}"
            p = Proceso(nombre, memoria_mb=memoria, duracion_s=duracion)
            self.sim.agregar(p)
            self._actualizar_vista()
            dlg.destroy()
        except ValueError:
            messagebox.showerror("Datos inválidos", "Memoria y Duración deben ser enteros positivos.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------- Vista / Render ----------

    def _actualizar_vista(self):
        foto = self.sim.foto()
        # RAM (texto + barra)
        usado = foto["ram"]["usado_mb"]
        cap = foto["ram"]["capacidad_mb"]
        disp = foto["ram"]["disponible_mb"]
        self.pb_ram["maximum"] = cap
        self.pb_ram["value"] = usado
        self.lbl_ram.configure(text=f"RAM: {usado} / {cap} MB  —  Libre: {disp} MB")

        # Actualizar histograma de % uso RAM
        porcentaje = 0 if cap == 0 else (usado / cap) * 100.0
        self._hist_uso.append(porcentaje)
        if len(self._hist_uso) > self._hist_max:
            self._hist_uso.pop(0)
        # Redibujo de la línea
        xs = list(range(len(self._hist_uso)))
        self.line.set_data(xs, self._hist_uso)
        self.ax.set_xlim(0, max(self._hist_max - 1, len(self._hist_uso)))
        self.canvas.draw_idle()

        # Limpiar tablas
        tree_listos = self.tree_listos.winfo_children()[1] if isinstance(self.tree_listos, ttk.Frame) else None
        tree_espera = self.tree_espera.winfo_children()[1] if isinstance(self.tree_espera, ttk.Frame) else None
        for tv in (tree_listos, tree_espera, self.tree_cpu_now, self.tree_fin):
            if hasattr(tv, "get_children"):
                for it in tv.get_children():
                    tv.delete(it)

        # Rellenar listos / espera
        pids_listos = foto["listos"]
        pids_espera = foto["espera_memoria"]
        vivos = {p.pid: p for p in self._procesos_vivos()}

        if tree_listos is not None:
            for pid in pids_listos:
                p = vivos.get(pid)
                if p:
                    tree_listos.insert("", "end", values=(p.pid, p.nombre, p.memoria_mb, p.duracion_s, p.restante_s))

        if tree_espera is not None:
            for pid in pids_espera:
                p = vivos.get(pid)
                if p:
                    tree_espera.insert("", "end", values=(p.pid, p.nombre, p.memoria_mb, p.duracion_s, p.restante_s))

        # CPU
        if not self.sim.cpu.ociosa():
            p = self.sim.cpu.actual
            self.tree_cpu_now.insert("", "end", values=(p.pid, p.nombre, p.restante_s))  # type: ignore

        # Finalizados (últimos 10)
        for p in self.sim.finalizados[-10:]:
            self.tree_fin.insert("", "end", values=(p.pid, p.nombre, p.duracion_s))

    def _procesos_vivos(self):
        vivos = []
        vivos.extend(list(self.sim.plan.listos))
        vivos.extend(list(self.sim.plan.espera_memoria))
        if not self.sim.cpu.ociosa():
            vivos.append(self.sim.cpu.actual)  # type: ignore
        return vivos
