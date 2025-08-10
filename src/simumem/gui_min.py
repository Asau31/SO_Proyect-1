from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from .simulador import Simulador
from .proceso import Proceso


class VentanaSimulador(tk.Tk):
    """
    Interfaz mínima para observar el simulador:
      - RAM: barra de uso con texto.
      - Colas FIFO: listos y espera de memoria.
      - CPU: proceso actual.
      - Finalizados: historial corto.
      - Controles: Agregar proceso, Paso, Iniciar/Pausar, Reiniciar.

    La ventana avanza la simulación con .after() para mantener todo en un solo hilo.
    """

    def __init__(self, capacidad_mb: int = 1024) -> None:
        super().__init__()
        self.title("Simulador de Procesos en Memoria — Minimal")
        self.geometry("760x520")
        self.minsize(720, 500)

        # Modelo
        self.sim = Simulador(capacidad_mb=capacidad_mb)
        self._reloj_corriendo = False
        self._intervalo_ms = 1000  # 1 segundo por tick

        # Estilos sobrios
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#121212")
        style.configure("TLabel", background="#121212", foreground="#e6e6e6")
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Muted.TLabel", foreground="#9aa0a6")
        style.configure("TButton", padding=6)
        style.configure("Mem.Horizontal.TProgressbar", troughcolor="#1e1e1e")

        # ---- Layout raíz
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        # Encabezado
        ttk.Label(root, text="Simulador de Gestión de Procesos (FIFO / 1 CPU)",
                  style="Header.TLabel").pack(anchor="w")

        # RAM
        marco_ram = ttk.Frame(root, padding=(0, 8, 0, 12))
        marco_ram.pack(fill="x")
        self.pb_ram = ttk.Progressbar(
            marco_ram, style="Mem.Horizontal.TProgressbar", orient="horizontal",
            mode="determinate", maximum=self.sim.memoria.capacidad_mb
        )
        self.pb_ram.pack(fill="x")
        self.lbl_ram = ttk.Label(marco_ram, text="RAM: 0 / 0 MB", style="Muted.TLabel")
        self.lbl_ram.pack(anchor="e", pady=(6, 0))

        # Paneles principales (3 columnas)
        paneles = ttk.Frame(root)
        paneles.pack(fill="both", expand=True)

        self.tree_listos = self._crear_lista(paneles, "Cola LISTOS (FIFO)")
        self.tree_espera = self._crear_lista(paneles, "Espera de Memoria")
        self.tree_cpu = self._crear_lista(paneles, "CPU y Finalizados", dos_bloques=True)

        paneles.columnconfigure((0, 1, 2), weight=1)
        self.tree_listos.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.tree_espera.grid(row=0, column=1, sticky="nsew", padx=8)
        self.tree_cpu.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        # Controles
        controles = ttk.Frame(root, padding=(0, 10, 0, 0))
        controles.pack(fill="x")

        self.btn_agregar = ttk.Button(controles, text="Agregar proceso", command=self._abrir_dialogo_proceso)
        self.btn_paso = ttk.Button(controles, text="Paso (1s)", command=self._paso_manual)
        self.btn_toggle = ttk.Button(controles, text="Iniciar", command=self._toggle)
        self.btn_reset = ttk.Button(controles, text="Reiniciar", command=self._reiniciar)

        self.btn_agregar.pack(side="left")
        self.btn_paso.pack(side="left", padx=6)
        self.btn_toggle.pack(side="left")
        self.btn_reset.pack(side="right")

        # Primera pintura
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
            # Arriba: CPU actual (una fila). Abajo: finalizados.
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

    # ---------- Lógica de control ----------

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
        # Si el reloj está corriendo, ignoro el paso manual para no pisarnos.
        if self._reloj_corriendo:
            return
        self.sim.paso()
        self._actualizar_vista()

    def _reiniciar(self):
        if messagebox.askyesno("Reiniciar", "¿Seguro que deseas reiniciar el simulador?"):
            cap = self.sim.memoria.capacidad_mb
            self.sim = Simulador(capacidad_mb=cap)
            self._reloj_corriendo = False
            self.btn_toggle.configure(text="Iniciar")
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
        ttk.Button(botones, text="Agregar", command=lambda: self._confirmar_proceso(dlg, e_nombre.get(), e_mem.get(), e_dur.get())).pack(side="right", padx=(0, 6))

        frm.columnconfigure(1, weight=1)

    def _confirmar_proceso(self, dlg: tk.Toplevel, nombre: str, mem_txt: str, dur_txt: str):
        try:
            memoria = int(mem_txt)
            duracion = int(dur_txt)
            if not nombre.strip():
                nombre = f"Proceso {len(self.sim.finalizados)+1}"
            p = Proceso(nombre, memoria_mb=memoria, duracion_s=duracion)
            self.sim.agregar(p)
            self._actualizar_vista()
            dlg.destroy()
        except ValueError:
            messagebox.showerror("Datos inválidos", "Memoria y Duración deben ser números enteros.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------- Vista ----------

    def _actualizar_vista(self):
        foto = self.sim.foto()
        # RAM
        usado = foto["ram"]["usado_mb"]
        cap = foto["ram"]["capacidad_mb"]
        disp = foto["ram"]["disponible_mb"]
        self.pb_ram["maximum"] = cap
        self.pb_ram["value"] = usado
        self.lbl_ram.configure(text=f"RAM: {usado} / {cap} MB  —  Libre: {disp} MB")

        # Listos
        t = self._tree_Cola_LISTOS_( ) if hasattr(self, "_tree_Cola_LISTOS_") else None  # noqa: E702
        # Nota: nombres dinámicos con espacios son incómodos; accedemos directo:
        tree_listos = self.tree_listos.winfo_children()[1] if isinstance(self.tree_listos, ttk.Frame) else None  # TreeView es el 2° hijo
        tree_espera = self.tree_espera.winfo_children()[1] if isinstance(self.tree_espera, ttk.Frame) else None

        # Limpieza y llenado seguro
        for tv in (tree_listos, tree_espera, self.tree_cpu_now, self.tree_fin):
            if hasattr(tv, "get_children"):
                for it in tv.get_children():
                    tv.delete(it)

        # Rellenar listos
        # Para mostrar info completa buscamos los objetos desde los IDs que da foto()
        pids_listos = foto["listos"]
        pids_espera = foto["espera_memoria"]

        # Recolecta vivos (en colas + cpu)
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

        # Finalizados
        for p in self.sim.finalizados[-10:]:  # últimos 10
            self.tree_fin.insert("", "end", values=(p.pid, p.nombre, p.duracion_s))

    def _procesos_vivos(self):
        """
        Construye una lista de procesos que no han terminado:
        los que están en listas + el que está en CPU, consultando al planificador.
        """
        vivos = []
        vivos.extend(list(self.sim.plan.listos))
        vivos.extend(list(self.sim.plan.espera_memoria))
        if not self.sim.cpu.ociosa():
            vivos.append(self.sim.cpu.actual)  # type: ignore
        return vivos
