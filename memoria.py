from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

class MemoriaError(Exception):
    """Errores relacionados con la administración de memoria."""

@dataclass
class MemoriaRAM:
    """
    Administrador muy directo de memoria.
    - Trabajamos en MB y sin fragmentación (modelo simple y suficiente para el curso).
    - Lleva un registro por PID de lo reservado.
    """

    capacidad_mb: int = 1024  # 1 GB por defecto
    _asignaciones: Dict[int, int] = field(default_factory=dict, init=False)

    # --------------- Lecturas útiles ---------------

    @property
    def usado_mb(self) -> int:
        return sum(self._asignaciones.values())

    @property
    def disponible_mb(self) -> int:
        return self.capacidad_mb - self.usado_mb

    # --------------- Operaciones principales ---------------

    def puede_reservar(self, pedido_mb: int) -> bool:
        """Consulta rápida para validaciones antes de admitir a la cola."""
        return 0 < pedido_mb <= self.disponible_mb

    def reservar(self, pid: int, pedido_mb: int) -> bool:
        """
        Intenta reservar 'pedido_mb' para el PID dado.
        Devuelve True si se reservó; False si no hay espacio suficiente.
        """
        if pid in self._asignaciones:
            raise MemoriaError(f"El PID {pid} ya tiene memoria asignada.")
        if pedido_mb <= 0:
            raise MemoriaError("El pedido de memoria debe ser > 0 MB.")

        if pedido_mb <= self.disponible_mb:
            self._asignaciones[pid] = pedido_mb
            return True
        return False

    def liberar(self, pid: int) -> int:
        """
        Libera la memoria asociada a 'pid'. Devuelve la cantidad liberada (MB).
        Si el PID no existe, devuelve 0 (idempotente para simplificar flujo).
        """
        return self._asignaciones.pop(pid, 0)

    # --------------- Utilidades ---------------

    def foto(self) -> dict:
        """Pequeño snapshot para UI/tablas."""
        return {
            "capacidad_mb": self.capacidad_mb,
            "usado_mb": self.usado_mb,
            "disponible_mb": self.disponible_mb,
            "pids": dict(self._asignaciones),  # copia para no exponer el interno
        }
