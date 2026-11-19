import polars as pl

from etl.indicadores_disponibles import PATH_DATA_RAW
from etl.extraer_datos_api_indicadores import cargar_indicadores_seleccionados

def fusionar_datos_indicadores(indicador: int) -> bool:
    """
    Fusiona todos los meses de los indicadores recuperados con el sistema de extracción.
    """
    raiz_fichero = PATH_DATA_RAW / f"{indicador}"
    ruta_destino = PATH_DATA_RAW / f"{indicador}" / "total" 

    if not raiz_fichero.exists():
        raise FileNotFoundError(
            f"No existe la carpeta del indicador {indicador} en {raiz_fichero.resolve()}"
        )

    archivos = sorted(raiz_fichero.glob("*.parquet"))
    if not archivos:
        print(f"[AVISO] Carpeta vacía para el indicador {indicador}.")
        return False

    # diagonal_relaxed absorbe meses antiguos donde falte alguna columna o venga como Null
    lf = pl.concat(
        (pl.scan_parquet(f) for f in archivos),
        how="diagonal_relaxed",
    )

    # Incluye geo_id en la clave para no colapsar las provincias de potencia instalada
    columnas = lf.collect_schema().names()
    clave_unica = ["datetime_utc", "id"]
    if "geo_id" in columnas:
        clave_unica.append("geo_id")

    ruta_destino.mkdir(parents=True, exist_ok=True)
    fichero_salida = ruta_destino / f"{indicador}_total.parquet"

    (
        lf.unique(subset=clave_unica)
        .sort(clave_unica)
        .collect()
        .write_parquet(fichero_salida)
    )
    return True



if __name__ == "__main__":
    INDICADORES_SELECCIONADOS = cargar_indicadores_seleccionados()

    RESULTADO = {indicador : fusionar_datos_indicadores(indicador) for indicador, _ in INDICADORES_SELECCIONADOS.items()}

    if False in RESULTADO.values():
        raise RuntimeError("Ha habido fallos al fusionar los datos. Revisar los datos completos.")
