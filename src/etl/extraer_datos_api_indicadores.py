import json

import httpx
import polars as pl
from datetime import date
from etl.indicadores_disponibles import HEADERS, PATH_DATA_RAW
from etl.set_parameters import set_parameters, generar_rangos_mensuales


def cargar_indicadores_seleccionados() -> dict:
    JSON_INDICADORES = PATH_DATA_RAW / "indicadores_seleccionados.json"

    with JSON_INDICADORES.open("r") as file:
        return json.load(file)


INDICADORES_SELECCIONADOS = cargar_indicadores_seleccionados()

rango_fechas = generar_rangos_mensuales(date(2020, 1, 1))

with httpx.Client(headers=HEADERS, timeout=40, follow_redirects=True) as client:
    for indicador, nombre_indicador in INDICADORES_SELECCIONADOS.items():
        indicador_path = (PATH_DATA_RAW / f"{indicador}")
        indicador_path.mkdir(parents=True, exist_ok=True)
        print(f"Indicador: {indicador} [{nombre_indicador}]")

        for fecha_inicio, fecha_fin in rango_fechas:
            fecha_inicio_corta = fecha_inicio[0:10]
            fecha_fin_corta = fecha_fin[0:10]
            

            ruta_salida = indicador_path / f"{indicador}_{nombre_indicador}_{fecha_inicio_corta}_{fecha_fin_corta}.parquet"

            if ruta_salida.exists():
                print(".", end="")
                continue

            print(f"Fecha inicio [{fecha_fin_corta}] fecha fin [{fecha_fin_corta}]")

            params = set_parameters(
                indicador=indicador,
                start_date=fecha_inicio,
                end_date=fecha_fin,
            )
            resp = client.get(
                f"https://api.esios.ree.es/indicators/{indicador}", params=params
            )
            resp.raise_for_status()
            ind = resp.json()["indicator"]

            valores = ind.get("values", [])
            if not valores:
                print(f"  [AVISO] Sin datos para {indicador} ({nombre_indicador})")
                continue

            datos = pl.DataFrame(valores).with_columns(
                pl.lit(int(indicador)).alias("id"),
                pl.lit(nombre_indicador).alias("variable"),
                pl.col("value").cast(pl.Float64),
                pl.col("datetime_utc").str.to_datetime(time_zone="UTC"),
            )

            datos.write_parquet(ruta_salida)