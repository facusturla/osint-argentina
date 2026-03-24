"""
Módulo: georef.py
Descripción: Normalización de domicilios y consulta de entidades geográficas argentinas
             mediante la API pública GeoRef del Instituto Geográfico Nacional (IGN).

API pública, sin API key requerida.
Documentación: https://datosgobar.github.io/georef-ar-api/
"""

import requests
from urllib.parse import quote

GEOREF_API_BASE = "https://apis.datos.gob.ar/georef/api"

HEADERS = {
    "User-Agent": "OSINT-Argentina/1.0 (investigacion academica)",
    "Accept": "application/json"
}

TIMEOUT = 10


def normalize_address(direccion: str, provincia: str = None) -> dict:
    """
    Normaliza un domicilio argentino contra el padrón oficial del IGN.

    Args:
        direccion: Dirección a normalizar (ej: "Av. Corrientes 1234, Buenos Aires")
        provincia: Nombre de provincia para acotar la búsqueda (opcional)

    Returns:
        dict con claves:
            - found (bool): si se encontró coincidencia
            - direccion_normalizada (str): dirección normalizada oficial
            - calle (str): nombre de calle oficial
            - altura (int|None): número de puerta
            - localidad (str): localidad
            - municipio (str): municipio
            - provincia (str): provincia
            - coordenadas (dict): {"lat": float, "lon": float} o None
            - confianza (int): score de confianza (0-100)
            - fuente (str): URL de referencia
            - error (str|None): mensaje de error si ocurrió alguno
    """
    fuente = "https://georef.datos.gob.ar/"

    params = {
        "direccion": direccion,
        "max": 1,
        "exacto": False
    }
    if provincia:
        params["provincia"] = provincia

    try:
        resp = requests.get(
            f"{GEOREF_API_BASE}/direcciones",
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()

        resultados = data.get("direcciones", [])
        if not resultados:
            return {
                "found": False,
                "direccion_normalizada": None,
                "calle": None,
                "altura": None,
                "localidad": None,
                "municipio": None,
                "provincia": None,
                "coordenadas": None,
                "confianza": 0,
                "fuente": fuente,
                "error": None
            }

        res = resultados[0]
        ubicacion = res.get("ubicacion") or {}
        calle = res.get("calle", {})
        localidad = res.get("localidad_censal", {}) or res.get("localidad", {})
        municipio = res.get("municipio", {})
        prov = res.get("provincia", {})

        coordenadas = None
        if ubicacion.get("lat") is not None and ubicacion.get("lon") is not None:
            coordenadas = {
                "lat": ubicacion["lat"],
                "lon": ubicacion["lon"]
            }

        return {
            "found": True,
            "direccion_normalizada": res.get("nomenclatura", direccion),
            "calle": calle.get("nombre", "N/D"),
            "altura": res.get("altura", {}).get("valor"),
            "localidad": localidad.get("nombre", "N/D"),
            "municipio": municipio.get("nombre", "N/D"),
            "provincia": prov.get("nombre", "N/D"),
            "coordenadas": coordenadas,
            "confianza": res.get("confianza", 0),
            "fuente": fuente,
            "error": None
        }

    except requests.exceptions.ConnectionError:
        return {
            "found": False,
            "direccion_normalizada": None,
            "calle": None,
            "altura": None,
            "localidad": None,
            "municipio": None,
            "provincia": None,
            "coordenadas": None,
            "confianza": 0,
            "fuente": fuente,
            "error": "No se pudo conectar con la API GeoRef (georef.datos.gob.ar)."
        }
    except requests.RequestException as exc:
        return {
            "found": False,
            "direccion_normalizada": None,
            "calle": None,
            "altura": None,
            "localidad": None,
            "municipio": None,
            "provincia": None,
            "coordenadas": None,
            "confianza": 0,
            "fuente": fuente,
            "error": f"Error al consultar GeoRef: {exc}"
        }


def search_locality(nombre: str, provincia: str = None) -> list[dict]:
    """
    Busca localidades argentinas por nombre.

    Args:
        nombre: Nombre de la localidad (ej: "Villa María")
        provincia: Nombre de provincia para acotar (opcional)

    Returns:
        Lista de localidades encontradas con nombre, municipio, provincia y coordenadas.
    """
    params = {"nombre": nombre, "max": 5}
    if provincia:
        params["provincia"] = provincia

    try:
        resp = requests.get(
            f"{GEOREF_API_BASE}/localidades",
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        localidades = data.get("localidades", [])

        results = []
        for loc in localidades:
            centroide = loc.get("centroide", {})
            results.append({
                "nombre": loc.get("nombre", "N/D"),
                "municipio": (loc.get("municipio") or {}).get("nombre", "N/D"),
                "departamento": (loc.get("departamento") or {}).get("nombre", "N/D"),
                "provincia": (loc.get("provincia") or {}).get("nombre", "N/D"),
                "coordenadas": {
                    "lat": centroide.get("lat"),
                    "lon": centroide.get("lon")
                } if centroide else None
            })
        return results

    except requests.RequestException:
        return []
