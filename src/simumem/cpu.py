from __future__ import annotations

from typing import Optional
from .proceso import Proceso
from .estados import EstadoProceso


class CPUUnica:
    """
    CPU muy directa: puede cargar un solo proceso.
    El reloj avanza en ticks de 1 segundo por simplicidad.
    """

    def __init__(self) -> None:
        self.actual: Optional[Proceso] = None
        self.tiempo_total = 0  # métrica simple

    def ociosa(self) -> bool:
        return self.actual is None

    def cargar(self, p: Proceso) -> None:
        if not self.ociosa():
            raise RuntimeError("La CPU ya está ocupada.")
        p.despachar()
        self.actual = p

    def descargar(self) -> Optional[Proceso]:
        """Suelta el proceso actual (sin tocar su estado)."""
        p = self.actual
        self.actual = None
        return p

    def tick(self) -> Optional[Proceso]:
        """
        Avanza un segundo. Si el proceso termina en este tick,
        lo devuelve para que el simulador lo postprocese.
        """
        self.tiempo_total += 1
        if self.actual is None:
            return None
        termino = self.actual.tictac(1)
        if termino and self.actual.estado is EstadoProceso.TERMINADO:
            fin = self.actual
            self.actual = None
            return fin
        return None
