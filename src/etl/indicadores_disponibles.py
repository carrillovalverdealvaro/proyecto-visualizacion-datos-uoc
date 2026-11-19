import html
import json
import os
from pathlib import Path

import httpx
import polars as pl
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]

PATH_DATA_RAW = Path(ROOT_DIR / "data/raw")
PATH_DATA_RAW.mkdir(parents=True, exist_ok=True)

load_dotenv()

TOKEN = os.environ["REE_TOKEN"]
HEADERS = {
    "Accept": "application/json; application/vnd.esios-api-v1+json",
    "Content-Type": "application/json",
    "x-api-key": TOKEN,
}

res = httpx.get("https://api.esios.ree.es/indicators", headers=HEADERS).json()

catalogo = pl.DataFrame(
    [
        {
            "id": item["id"],
            "nombre": item["name"],
            "nombre_corto": item.get("short_name", ""),
            # Limpiamos etiquetas HTML básicas de la descripción si las hubiera
            "descripcion": item.get("description", ""),
        }
        for item in res["indicators"]
    ]
)

catalogo = catalogo.with_columns(
    pl.col("descripcion").map_elements(html.unescape, return_dtype=pl.String)
).with_columns(
    pl.col("descripcion")
    .str.replace_all(r"<[^>]*>", "")  # Elimina cualquier etiqueta entre < y >
    .str.strip_chars()  # Limpia espacios en blanco sobrantes a los lados
)

catalogo.write_csv(
    PATH_DATA_RAW / "catalogo_esios_completo.csv", include_bom=True, separator=";"
)

# 1. Generación pura Peninsular
MIX_GENERACION_PENINSULA = {
    546: "hidraulica",
    547: "carbon",
    549: "nuclear",
    550: "ciclo_combinado",
    551: "eolica",
    1294: "termica_renovable",
    1295: "solar_fotovoltaica",
    1296: "solar_termica",
    1297: "cogeneracion_y_residuos",
}

# 2. Flujos de ajuste del balance
BALANCE_Y_ALMACENAMIENTO = {
    553: "consumo_bombeo",
    554: "saldo_intercambios_internacionales",
    555: "enlace_baleares",
}

# 3. Emisiones totales de CO2
IND_EMISIONES = {
    10355: "co2_total_t",  # Toneladas CO2eq totales del mix
}

# 4. Demanda total, por definición, es la suma de 1.
IND_DEMANDA = {1293: "demanda_electrica_total"}

# 5. Precios, spot y pvpc
IND_PRECIOS = {
    600: "precio_omie_spot",  # Filtrar con geo_ids[] = [3] (España)
    1001: "precio_pvpc",  # Filtrar con geo_ids[] = [8741] (Península)
}

# 6. Potencia instalada por cada tipo 
IND_POTENCIA_INSTALADA = {
    10300: "potencia_total",  # Potencia instalada de generación total
    10302: "potencia_renovable",  # Potencia instalada de generación total renovable
    10301: "potencia_no_renovable",  # Potencia instalada de generación total no renovable
    10304: "potencia_libre_emisiones",  # Potencia instalada de generación total libre de emisiones
    10303: "potencia_con_emisiones",  # Potencia instalada de generación total con emisiones
    10003: "potencia_convencional",  # Potencia instalada total de generación convencional
}

listado_final_indicadores = [
    *MIX_GENERACION_PENINSULA.keys(),
    *BALANCE_Y_ALMACENAMIENTO.keys(),
    *IND_EMISIONES.keys(),
    *IND_DEMANDA.keys(),
    *IND_PRECIOS.keys(),
    *IND_POTENCIA_INSTALADA.keys(),
]

catalogo_filtrado = catalogo.filter(pl.col("id").is_in(listado_final_indicadores))

catalogo_filtrado.write_csv(
    PATH_DATA_RAW / "catalogo_esios_seleccionada.csv", include_bom=True, separator=";"
)

TODOS_LOS_INDICADORES = {
    **MIX_GENERACION_PENINSULA,
    **BALANCE_Y_ALMACENAMIENTO,
    **IND_EMISIONES,
    **IND_DEMANDA,
    **IND_PRECIOS,
    **IND_POTENCIA_INSTALADA,
}

ruta = Path(PATH_DATA_RAW / "indicadores_seleccionados.json")

with ruta.open("w", encoding="utf-8") as f:
    json.dump(TODOS_LOS_INDICADORES, f, indent=4, ensure_ascii=False)
