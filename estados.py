from enum import Enum, auto

class EstadoProceso(Enum):
    """
    Ciclo de vida mínimo que usaremos en el simulador.

    NUEVO      : Archivo que es totalmente nuevo, no tiene memoria asignada. 
    LISTO      : Tiene memoria asignada y espera turno en la cola FIFO.
    EJECUTANDO : Está consumiendo la única CPU.
    TERMINADO  : Concluyó y liberó memoria.
    CANCELADO  : Se abortó por error o a petición del usuario.

    """

    NUEVO = auto()
    LISTO = auto()
    EJECUTANDO = auto()
    TERMINADO = auto()
    CANCELADO = auto()

    def finalizo(self) -> bool:
        """
        ¿Este estado ya cierra la historia del proceso?
        Lo dejo como método porque hace el flujo más expresivo.
        """
        return self in (EstadoProceso.TERMINADO, EstadoProceso.CANCELADO)
