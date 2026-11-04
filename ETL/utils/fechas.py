"""
fechas.py
=========
Utilidades para parseo y normalización de fechas.
Los Excel de campo llegan con formatos inconsistentes.
"""

from datetime import datetime, date, timedelta
import re
from typing import Optional

import pandas as pd

from config.parametros import obtener


_EXCEL_BASE_DATE = datetime(1899, 12, 30)


FORMATOS_ACEPTADOS = [
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d',
    '%Y/%m/%d %H:%M:%S',
    '%Y/%m/%d %H:%M',
    '%Y/%m/%d',
    '%Y%m%d %H:%M:%S',
    '%Y%m%d %H:%M',
    '%Y%m%d',
    '%d/%m/%Y %H:%M:%S',
    '%d/%m/%Y %H:%M',
    '%d/%m/%Y',
    '%d-%m-%Y %H:%M:%S',
    '%d-%m-%Y %H:%M',
    '%d-%m-%Y',
    '%d.%m.%Y',
]

FECHA_CAMPANA_INICIO = '2025-03-01'
FECHA_CAMPANA_FIN = '2026-06-30'

DOMINIOS_SIN_RESTRICCION_CAMPANA = {
    'clima',
    'historico',
    'induccion_floral',
    'tasa_crecimiento_brotes',
    'conteo_fenologico',
    'evaluacion_vegetativa',
    'floracion',
    'censo_plantas',
    'evaluacion_pesos',
    'ciclos_fenologicos',
}


def _obtener_rango_campana_configurado() -> tuple[str, str]:
    try:
        inicio = obtener('CAMPANA_FECHA_INICIO', FECHA_CAMPANA_INICIO)
        fin = obtener('CAMPANA_FECHA_FIN', FECHA_CAMPANA_FIN)
    except Exception:
        inicio = FECHA_CAMPANA_INICIO
        fin = FECHA_CAMPANA_FIN

    return (
        str(inicio).strip() or FECHA_CAMPANA_INICIO,
        str(fin).strip() or FECHA_CAMPANA_FIN,
    )


def obtener_politica_fecha(dominio: str | None = None) -> dict:
    """
    Retorna la politica de validacion temporal para un dominio/fact.
    Si el dominio no existe, usa la politica default.
    """
    clave = str(dominio).strip().lower() if dominio else 'default'
    inicio, fin = _obtener_rango_campana_configurado()
    politica_default = {
        'validar_campana': True,
        'inicio': inicio,
        'fin': fin,
    }
    if clave in DOMINIOS_SIN_RESTRICCION_CAMPANA:
        return {
            'validar_campana': False,
            'inicio': None,
            'fin': None,
        }
    return politica_default.copy()


def resolver_dominio_fecha(tipo_tabla: str | None) -> str | None:
    if tipo_tabla is None:
        return None

    mapa = {
        'clima': 'clima',
        'conteo_fruta': 'conteo_fenologico',
        'conteo_fenologico': 'conteo_fenologico',
        'cosecha_sap': 'cosecha_sap',
        'evaluacion_pesos': 'evaluacion_pesos',
        'evaluacion_vegetativa': 'evaluacion_vegetativa',
        'fisiologia': 'fisiologia',
        'induccion_floral': 'induccion_floral',
        'peladas': 'peladas',
        'sanidad': 'sanidad',
        'sanidad_activo': 'sanidad_activo',
        'tareo': 'tareo',
        'tasa_crecimiento_brotes': 'tasa_crecimiento_brotes',
        'ciclo_poda': 'ciclo_poda',
    }
    return mapa.get(str(tipo_tabla).strip().lower())


def describir_rango_campana(
    *,
    dominio: str | None = None,
    inicio: str | None = None,
    fin: str | None = None,
) -> str:
    politica = obtener_politica_fecha(dominio)
    inicio_resuelto = inicio if inicio is not None else politica.get('inicio')
    fin_resuelto = fin if fin is not None else politica.get('fin')

    if inicio_resuelto is None or fin_resuelto is None:
        return 'sin restriccion de campana'

    return f'{inicio_resuelto} -> {fin_resuelto}'


def parsear_serie_fechas(serie: 'pd.Series') -> 'pd.Series':
    """
    Parsea una Serie COMPLETA de fechas en un solo paso vectorizado.
    Mucho más rápido que aplicar parsear_fecha fila a fila.
    Usa inferencia automática de formato; los valores no parseables quedan NaT.
    """
    # Primer intento rápido con inferencia de formato
    serie_texto = serie.astype('string')
    mascara_iso = serie_texto.str.fullmatch(r'\d{4}-\d{2}-\d{2}', na=False)
    mascara_iso_dt = serie_texto.str.fullmatch(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}', na=False)

    resultado = pd.Series(pd.NaT, index=serie.index, dtype='datetime64[ns]')
    if mascara_iso.any():
        resultado.loc[mascara_iso] = pd.to_datetime(
            serie_texto[mascara_iso],
            errors='coerce',
            format='%Y-%m-%d'
        )
    if mascara_iso_dt.any():
        serie_iso_dt = serie_texto[mascara_iso_dt].str.replace('T', ' ', regex=False)
        resultado.loc[mascara_iso_dt] = pd.to_datetime(
            serie_iso_dt,
            errors='coerce',
            format='%Y-%m-%d %H:%M:%S'
        )

    mascara_restante = resultado.isna() & serie.notna()
    if mascara_restante.any():
        resultado.loc[mascara_restante] = pd.to_datetime(
            serie[mascara_restante],
            errors='coerce',
            dayfirst=True
        )
    # Rellenar los NaT con intento de número de serie Excel
    mascara_nat = resultado.isna() & serie.notna()
    if mascara_nat.any():
        def _desde_serial(v):
            try:
                serial = int(float(str(v).strip()))
                if 30000 < serial < 60000:
                    return _EXCEL_BASE_DATE + timedelta(days=serial)
            except (ValueError, TypeError):
                pass
            return None
        resultado_serial = pd.to_datetime(
            serie[mascara_nat].map(_desde_serial),
            errors='coerce'
        )
        resultado = resultado.where(~mascara_nat, other=resultado_serial)
    return resultado


def parsear_fecha(valor: str | None) -> Optional[datetime]:
    """
    Intenta parsear un string de fecha. Intento rápido primero,
    luego recorre todos los formatos aceptados si falla.
    Retorna datetime si parsea correctamente, None si falla.
    """
    if valor is None:
        return None

    valor = str(valor).strip()

    if not valor:
        return None

    valor = re.sub(r'\s+', ' ', valor.replace('T', ' ')).strip()

    fecha_corta = _parsear_fecha_corta_ambigua(valor)
    if fecha_corta is not None:
        return fecha_corta

    for formato in FORMATOS_ACEPTADOS:
        try:
            return datetime.strptime(valor, formato)
        except ValueError:
            continue

    # Excel a veces entrega float (número de serie de fecha)
    try:
        numero = float(valor)
        # Número de serie de Excel → fecha. Conservamos la parte decimal para la hora.
        from datetime import timedelta
        base = datetime(1899, 12, 30)
        return base + timedelta(days=numero)
    except (ValueError, TypeError):
        pass

    # Fallback conservador solo para formatos no contemplados.
    try:
        import pandas as _pd
        es_anio_primero = bool(
            re.match(r'^\d{4}[-/]', valor)
            or re.match(r'^\d{8}(?:\s|$)', valor)
        )
        resultado = _pd.to_datetime(
            valor,
            dayfirst=not es_anio_primero,
            yearfirst=es_anio_primero,
            errors='coerce',
        )
        if resultado is not _pd.NaT:
            return resultado.to_pydatetime()
    except Exception:
        pass

    return None


def _parsear_fecha_corta_ambigua(valor: str) -> Optional[datetime]:
    coincidencia = re.fullmatch(
        r'(?P<primero>\d{2})(?P<separador>[/-])(?P<segundo>\d{2})(?P=separador)(?P<tercero>\d{2})(?: (?P<hora>\d{1,2}:\d{2}(?::\d{2})?))?',
        valor,
    )
    if not coincidencia:
        return None

    primero = int(coincidencia.group('primero'))
    tercero = int(coincidencia.group('tercero'))
    separador = coincidencia.group('separador')
    hora = coincidencia.group('hora')

    base_dia_primero = f'%d{separador}%m{separador}%y'
    base_anio_primero = f'%y{separador}%m{separador}%d'
    formatos = []

    if hora:
        sufijos = [' %H:%M:%S', ' %H:%M']
    else:
        sufijos = ['']

    if primero >= 20 and tercero <= 31:
        bases = [base_anio_primero, base_dia_primero]
    elif tercero >= 20 and primero <= 31:
        bases = [base_dia_primero, base_anio_primero]
    else:
        bases = [base_dia_primero, base_anio_primero]

    for base in bases:
        for sufijo in sufijos:
            formatos.append(f'{base}{sufijo}')

    for formato in formatos:
        try:
            return datetime.strptime(valor, formato)
        except ValueError:
            continue

    return None


def obtener_semana_iso(fecha: datetime | date | None) -> Optional[int]:
    """
    Retorna el número de semana ISO de una fecha.
    """
    if fecha is None:
        return None
    return fecha.isocalendar()[1]


def obtener_id_tiempo(fecha: datetime | date | None) -> Optional[int]:
    """
    Convierte una fecha al formato ID_Tiempo = YYYYMMDD.
    Referencia directa a Silver.Dim_Tiempo.
    """
    if fecha is None:
        return None
    return int(fecha.strftime('%Y%m%d'))


def es_fecha_valida_campana(fecha: datetime | date | None,
                             inicio: str | None = None,
                             fin: str | None = None) -> bool:
    """
    Verifica que la fecha esté dentro del rango de la campaña activa.
    """
    if fecha is None:
        return False

    if inicio is None or fin is None:
        inicio_default, fin_default = _obtener_rango_campana_configurado()
        inicio = inicio or inicio_default
        fin = fin or fin_default

    fecha_inicio = datetime.strptime(inicio, '%Y-%m-%d').date()
    fecha_fin    = datetime.strptime(fin,    '%Y-%m-%d').date()

    fecha_date = fecha.date() if isinstance(fecha, datetime) else fecha

    # Validacion quirurgica: evitar fechas futuras extremas (error de dedo comun)
    anio_limite = datetime.now().year + 1
    if fecha_date.year > anio_limite:
        return False

    return fecha_inicio <= fecha_date <= fecha_fin


def procesar_fecha(valor: str | None,
                   *,
                   dominio: str | None = None,
                   validar_campana: bool = True,
                   inicio_campana: str | None = None,
                   fin_campana: str | None = None) -> tuple[Optional[datetime], bool]:
    """
    Parsea una fecha y, opcionalmente, valida campana.
    Retorna (fecha_parseada, es_valida_en_el_contexto).
    """
    fecha = parsear_fecha(valor)
    if fecha is None:
        return None, False

    politica = obtener_politica_fecha(dominio)
    if dominio is not None and inicio_campana is None:
        inicio_campana = politica.get('inicio')
    if dominio is not None and fin_campana is None:
        fin_campana = politica.get('fin')
    if dominio is not None:
        validar_campana = bool(politica.get('validar_campana', True))

    if not validar_campana:
        return fecha, True

    valida = es_fecha_valida_campana(
        fecha,
        inicio=inicio_campana,
        fin=fin_campana,
    )
    return fecha, valida
