from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from .estados import EstadoProceso


class ProcesoError(Exception):
    """Errores propios relacionados con operaciones del proceso."""


# Generador sencillo de PID incremental.
def _pid_secuencial():
    actual = 0
    while True:
        actual += 1
        yield actual


_pid_gen = _pid_secuencial()


@dataclass
class Proceso:
    """
    Representa un proceso listo para entrar al simulador.

    Campos principales:
      - pid: identificador único (lo asignamos automáticamente).
      - nombre: algo humano para reconocerlo en pantalla.
      - memoria_mb: cuánto RAM necesita reservar (MB).
      - duracion_s: segundos que necesita de CPU para terminar.

    El proceso nace en estado NUEVO y, en cuanto tenga memoria, pasará a LISTO.
    """

    nombre: str
    memoria_mb: int
    duracion_s: int
    pid: int = field(default_factory=lambda: next(_pid_gen), init=False)
    estado: EstadoProceso = field(default=EstadoProceso.NUEVO, init=False)

    # Seguimiento de tiempo (para estadísticas simples)
    _restante_s: int = field(init=False)
    _consumido_s: int = field(default=0, init=False)

    # Marcas de tiempo “informales” para reportes (no obligatorias)
    t_creacion: Optional[float] = field(default=None, init=False)
    t_inicio: Optional[float] = field(default=None, init=False)
    t_fin: Optional[float] = field(default=None, init=False)

    def __post_init__(self):
        if self.memoria_mb <= 0:
            raise ProcesoError("La memoria solicitada debe ser > 0 MB.")
        if self.duracion_s <= 0:
            raise ProcesoError("La duración del proceso debe ser > 0 s.")
        self._restante_s = int(self.duracion_s)

    # -----------------------------
    # Ciclo de vida y utilidades
    # -----------------------------

    def admitir(self):
        """
        Marca el proceso como LISTO (ya tiene memoria reservada).
        No lo despacho a CPU todavía; solo indica que puede entrar a la cola.
        """
        if self.estado is not EstadoProceso.NUEVO:
            raise ProcesoError("Solo se puede admitir un proceso en estado NUEVO.")
        self.estado = EstadoProceso.LISTO

    def despachar(self):
        """Pasa a EJECUTANDO (toma la CPU)."""
        if self.estado is not EstadoProceso.LISTO:
            raise ProcesoError("Para despachar, el proceso debe estar LISTO.")
        self.estado = EstadoProceso.EJECUTANDO

    def tictac(self, delta_s: int = 1) -> bool:
        """
        Avanza el 'reloj' del proceso cuando está en CPU.
        Resta tiempo y acumula consumo. Devuelve True si terminó con este tick.
        """
        if self.estado is not EstadoProceso.EJECUTANDO:
            raise ProcesoError("tictac() solo aplica cuando el proceso está EJECUTANDO.")

        if delta_s <= 0:
            return False

        consumir = min(delta_s, self._restante_s)
        self._restante_s -= consumir
        self._consumido_s += consumir
        if self._restante_s == 0:
            self.estado = EstadoProceso.TERMINADO
            return True
        return False

    def cancelar(self, motivo: str = ""):
        """Sale del sistema sin completar. Usado para abortos manuales o errores."""
        if self.estado.finalizo():
            return  # ya no hay nada que hacer
        self.estado = EstadoProceso.CANCELADO

    # -----------------------------
    # Lecturas útiles
    # -----------------------------

    @property
    def restante_s(self) -> int:
        return self._restante_s

    @property
    def consumido_s(self) -> int:
        return self._consumido_s

    @property
    def progreso(self) -> float:
        """Porcentaje de avance 0..1 (solo informativo)."""
        return self._consumido_s / self.duracion_s

    def resumen(self) -> dict:
        """Pequeño dict para tablas/logs."""
        return {
            "pid": self.pid,
            "nombre": self.nombre,
            "memoria_mb": self.memoria_mb,
            "duracion_s": self.duracion_s,
            "consumido_s": self._consumido_s,
            "restante_s": self._restante_s,
            "estado": self.estado.name,
        }

    def __repr__(self) -> str:
        return (
            f"Proceso(pid={self.pid}, nombre='{self.nombre}', "
            f"memoria_mb={self.memoria_mb}, duracion_s={self.duracion_s}, "
            f"estado={self.estado.name}, restante_s={self._restante_s})"
        )
