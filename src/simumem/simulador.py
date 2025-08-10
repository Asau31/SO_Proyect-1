from __future__ import annotations

from typing import List, Optional, Iterable

from .memoria import MemoriaRAM
from .planificador import PlanificadorFIFO
from .cpu import CPUUnica
from .proceso import Proceso


class Simulador:
    """
    Orquesta general:
      - Alta de procesos (van directo al planificador).
      - Bucle de pasos (tick): despacha a CPU si está libre,
        avanza CPU, libera memoria cuando un proceso termina,
        e intenta admitir procesos de la cola de espera.
    """

    def __init__(self, capacidad_mb: int = 1024) -> None:
        self.memoria = MemoriaRAM(capacidad_mb)
        self.plan = PlanificadorFIFO(self.memoria)
        self.cpu = CPUUnica()
        self.finalizados: List[Proceso] = []

    # --------- Altas ---------

    def cargar(self, procesos: Iterable[Proceso]) -> None:
        for p in procesos:
            self.plan.crear(p)

    def agregar(self, p: Proceso) -> None:
        self.plan.crear(p)

    # --------- Motor ---------

    def paso(self) -> None:
        """
        Ejecuta un 'paso' de simulación (1 segundo):
          1) Si la CPU está libre, toma el siguiente LISTO.
          2) Avanza CPU 1s.
          3) Si alguien terminó, libera memoria y registra finalizado.
          4) Intenta admitir procesos en espera de memoria.
        """
        # 1) Despacho si corresponde
        if self.cpu.ociosa():
            siguiente = self.plan.tomar_siguiente()
            if siguiente is not None:
                self.cpu.cargar(siguiente)

        # 2) Avance de CPU
        terminado = self.cpu.tick()

        # 3) Postproceso del que terminó
        if terminado is not None:
            self.memoria.liberar(terminado.pid)
            self.finalizados.append(terminado)

        # 4) Intentar admitir procesos que esperaban RAM
        self.plan.intentar_admitir_espera()

    def corriendo(self) -> bool:
        """¿Sigue habiendo trabajo por hacer?"""
        algo_en_colas = self.plan.hay_pendientes()
        cpu_activa = not self.cpu.ociosa()
        return algo_en_colas or cpu_activa

    # --------- Reportes pequeños ---------

    def foto(self) -> dict:
        foto = self.plan.foto()
        foto["cpu"] = {
            "ocupada": not self.cpu.ociosa(),
            "pid": None if self.cpu.ociosa() else self.cpu.actual.pid,  # type: ignore
        }
        foto["finalizados"] = [p.pid for p in self.finalizados]
        return foto
