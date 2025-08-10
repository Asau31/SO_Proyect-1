from __future__ import annotations

from collections import deque
from typing import Deque, Optional, List

from .proceso import Proceso
from .memoria import MemoriaRAM


class PlanificadorFIFO:
    """
    Mantiene dos colas:
      - espera_memoria: procesos que aún no caben en RAM.
      - listos: procesos con memoria reservada, esperando CPU (FIFO real).

    Reglas:
      - Al crear un proceso, primero intento reservar memoria. Si cabe,
        el proceso pasa a LISTO y entra a 'listos'. Si no, va a 'espera_memoria'.
      - Cada vez que se libera memoria, intento admitir de 'espera_memoria'
        hacia 'listos' respetando el orden de llegada.
    """

    def __init__(self, memoria: MemoriaRAM) -> None:
        self.memoria = memoria
        self.espera_memoria: Deque[Proceso] = deque()
        self.listos: Deque[Proceso] = deque()

    # --------- Altas y movimientos ---------

    def crear(self, p: Proceso) -> None:
        """Intenta dejar al proceso listo; si no cabe, lo manda a espera de memoria."""
        if self.memoria.puede_reservar(p.memoria_mb):
            self.memoria.reservar(p.pid, p.memoria_mb)
            p.admitir()
            self.listos.append(p)
        else:
            self.espera_memoria.append(p)

    def intentar_admitir_espera(self) -> None:
        """
        Mueve procesos desde 'espera_memoria' a 'listos' siempre que la RAM alcance.
        Respeta el orden FIFO, sin reordenamientos.
        """
        # Consumo por el frente, y paro en el primero que no cabe.
        mover: List[Proceso] = []
        while self.espera_memoria:
            candidato = self.espera_memoria[0]
            if self.memoria.puede_reservar(candidato.memoria_mb):
                self.espera_memoria.popleft()
                self.memoria.reservar(candidato.pid, candidato.memoria_mb)
                candidato.admitir()
                mover.append(candidato)
            else:
                break
        # Encolamos los que sí cupieron
        self.listos.extend(mover)

    def tomar_siguiente(self) -> Optional[Proceso]:
        """Entrega el siguiente proceso LISTO (FIFO)."""
        return self.listos.popleft() if self.listos else None

    # --------- Consultas útiles ---------

    def hay_pendientes(self) -> bool:
        """¿Quedan procesos en alguna cola?"""
        return bool(self.espera_memoria or self.listos)

    def foto(self) -> dict:
        """Snapshot ligero para UI o logs."""
        return {
            "listos": [p.pid for p in self.listos],
            "espera_memoria": [p.pid for p in self.espera_memoria],
            "ram": self.memoria.foto(),
        }
