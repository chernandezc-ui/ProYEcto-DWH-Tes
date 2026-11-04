from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, TypeAlias

from sqlalchemy.engine import Connection, Engine


RecursoDB: TypeAlias = Engine | Connection


def _es_conexion_db(recurso_db: RecursoDB) -> bool:
    return isinstance(recurso_db, Connection) or (
        hasattr(recurso_db, 'execute') and not hasattr(recurso_db, 'begin')
    )


@contextmanager
def administrar_recurso_db(recurso_db: RecursoDB) -> Iterator[Connection]:
    if _es_conexion_db(recurso_db):
        yield recurso_db
        return

    with recurso_db.begin() as conexion:
        yield conexion


class ContextoTransaccionalETL:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._gestor = None
        self.conexion: Connection | None = None

    def __enter__(self) -> "ContextoTransaccionalETL":
        self._gestor = self._engine.begin()
        self.conexion = self._gestor.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._gestor is None:
            return False

        try:
            return bool(self._gestor.__exit__(exc_type, exc, tb))
        finally:
            self.conexion = None
            self._gestor = None

    def _conexion_activa(self) -> Connection:
        if self.conexion is None:
            raise RuntimeError('ContextoTransaccionalETL sin conexion activa.')
        return self.conexion

    def marcar_estado_carga(
        self,
        tabla_origen: str,
        columna_id: str,
        ids: list[int | None] | tuple[int | None, ...],
        estado: str = 'PROCESADO',
        tam_lote: int = 2000,
    ) -> int:
        from utils.sql_lotes import marcar_estado_carga_por_ids

        return marcar_estado_carga_por_ids(
            self._conexion_activa(),
            tabla_origen,
            columna_id,
            ids,
            estado=estado,
            tam_lote=tam_lote,
        )

    def enviar_cuarentena(self, tabla_origen: str, filas: list[dict]) -> int:
        from dq.cuarentena import enviar_a_cuarentena

        return enviar_a_cuarentena(self._conexion_activa(), tabla_origen, filas)

    def registrar_homologacion(
        self,
        tabla_origen: str,
        campo_origen: str,
        texto_crudo: str,
        valor_canonico: str,
        score: float,
        aprobado: bool = True,
    ) -> None:
        from mdm.homologador import registrar_homologacion

        registrar_homologacion(
            self._conexion_activa(),
            tabla_origen,
            campo_origen,
            texto_crudo,
            valor_canonico,
            score,
            aprobado=aprobado,
        )
