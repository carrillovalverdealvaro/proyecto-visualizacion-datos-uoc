import calendar
from collections.abc import Callable
from datetime import date, timedelta
from functools import partial
from typing import Any

ParamStrategy = Callable[[str, str], dict[str, Any]]


def media_horaria(start_date: str, end_date: str) -> dict[str, Any]:
    """Potencia en tiempo real (MW): generación, demanda e intercambios."""
    return {
        "start_date": start_date,
        "end_date": end_date,
        "time_trunc": "hour",
        "time_agg": "avg",
    }


def suma_horaria(start_date: str, end_date: str) -> dict[str, Any]:
    """Magnitudes acumulables en la hora (toneladas de CO2)."""
    return {
        "start_date": start_date,
        "end_date": end_date,
        "time_trunc": "hour",
        "time_agg": "sum",
    }


def precio_horario(start_date: str, end_date: str, *, geo_id: int) -> dict[str, Any]:
    """Precios horarios filtrados por ámbito geográfico."""
    return {
        "start_date": start_date,
        "end_date": end_date,
        "time_trunc": "hour",
        "time_agg": "avg",
        "geo_ids[]": geo_id,
    }


def sin_truncado(start_date: str, end_date: str) -> dict[str, Any]:
    """Series estructurales no horarias (potencia instalada)."""
    return {
        "start_date": start_date,
        "end_date": end_date,
    }


# --- Registro de estrategias ---
IDS_MEDIA_HORARIA = {
    546, 547, 549, 550, 551,
    1294, 1295, 1296, 1297,
    553, 554, 555, 1293,
}
IDS_POTENCIA_INSTALADA = {10300, 10301, 10302, 10303, 10304, 10003}

ESTRATEGIAS_ESIOS: dict[int, ParamStrategy] = {
    **{i: media_horaria for i in IDS_MEDIA_HORARIA},
    **{i: sin_truncado for i in IDS_POTENCIA_INSTALADA},
    10355: suma_horaria,
    600: partial(precio_horario, geo_id=3),      # OMIE España
    1001: partial(precio_horario, geo_id=8741),  # PVPC Península
}


def set_parameters(
    indicador: int | str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Resuelve y ejecuta la estrategia de parámetros para el indicador."""
    strategy = ESTRATEGIAS_ESIOS.get(int(indicador), sin_truncado)
    return strategy(start_date, end_date)


def generar_rangos_mensuales(
    fecha_inicio: date,
    fecha_fin: date | None = None,
) -> list[tuple[str, str]]:
    """Genera tuplas (start_date, end_date) mes a mes en formato ISO 8601 UTC."""
    # Por defecto hasta ayer
    fecha_fin = fecha_fin or (date.today() - timedelta(days=1))
    rangos: list[tuple[str, str]] = []

    anio, mes = fecha_inicio.year, fecha_inicio.month

    while (anio, mes) <= (fecha_fin.year, fecha_fin.month):
        dia_inicio = (
            fecha_inicio.day
            if (anio, mes) == (fecha_inicio.year, fecha_inicio.month)
            else 1
        )
        ultimo_dia_mes = calendar.monthrange(anio, mes)[1]
        dia_fin = (
            fecha_fin.day
            if (anio, mes) == (fecha_fin.year, fecha_fin.month)
            else ultimo_dia_mes
        )

        inicio = f"{anio:04d}-{mes:02d}-{dia_inicio:02d}T00:00:00Z"
        fin = f"{anio:04d}-{mes:02d}-{dia_fin:02d}T23:59:59Z"
        rangos.append((inicio, fin))

        if mes == 12:
            anio += 1
            mes = 1
        else:
            mes += 1

    return rangos