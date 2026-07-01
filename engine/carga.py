"""
Carga de catálogos clínicos (NANDA, NOC, NIC y vínculos) desde CSV.

Antes: cargar_datos() vivía dentro de app.py, decorada con @st.cache_data,
y devolvía una tupla posicional de 6 dataframes que el resto del código
tenía que desempacar en el orden correcto cada vez. Aquí se devuelve un
único objeto Catalogos con atributos nombrados: menos frágil, más legible,
y usable fuera de Streamlit (tests, scripts, notebooks).
"""
from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class Catalogos:
    nanda: pd.DataFrame
    enlaces: pd.DataFrame
    noc_indicadores: pd.DataFrame
    nic_actividades: pd.DataFrame
    fundamentos: pd.DataFrame
    metas: pd.DataFrame


def cargar_catalogos(data_dir: str = "data") -> Catalogos:
    nanda = pd.read_csv(f"{data_dir}/nanda.csv", dtype={"codigo": str})
    nanda["codigo"] = nanda["codigo"].str.zfill(5)

    return Catalogos(
        nanda=nanda,
        enlaces=pd.read_csv(f"{data_dir}/enlaces.csv"),
        noc_indicadores=pd.read_csv(f"{data_dir}/noc_indicadores.csv"),
        nic_actividades=pd.read_csv(f"{data_dir}/nic_actividades.csv"),
        fundamentos=pd.read_csv(f"{data_dir}/fundamentos.csv"),
        metas=pd.read_csv(f"{data_dir}/metas.csv"),
    )
