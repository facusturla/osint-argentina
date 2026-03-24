"""
Módulo: ddjj_lookup.py
Descripción: Búsqueda de Declaraciones Juradas Patrimoniales de funcionarios públicos
             argentinos, vía el portal de datos abiertos de la Justicia (datos.jus.gob.ar)
             y la Oficina Anticorrupción (anticorrupcion.gob.ar).

Fuente pública, sin API key requerida.
"""

import requests

# CKAN endpoint del portal de datos del Ministerio de Justicia
DATAJUS_API = "https://datos.jus.gob.ar/api/3/action"

# ID del dataset de Declaraciones Juradas Patrimoniales Integrales de la OA
# Obtenido de: https://datos.jus.gob.ar/dataset/declaraciones-juradas-patrimoniales-integrales-de-funcionarios-publicos
DDJJ_PACKAGE_ID = "declaraciones-juradas-patrimoniales-integrales-de-funcionarios-publicos"

HEADERS = {
    "User-Agent": "OSINT-Argentina/1.0 (investigacion academica)"
}

TIMEOUT = 10


def _get_ddjj_resources() -> list[dict]:
    """Obtiene los recursos (archivos CSV) del dataset de DDJJ de la OA."""
    try:
        url = f"{DATAJUS_API}/package_show"
        resp = requests.get(url, params={"id": DDJJ_PACKAGE_ID}, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            return data["result"].get("resources", [])
    except requests.RequestException:
        pass
    return []


def _search_in_resource(resource_id: str, nombre: str) -> list[dict]:
    """Busca un nombre en un recurso CKAN específico via datastore_search."""
    try:
        url = f"{DATAJUS_API}/datastore_search"
        params = {
            "resource_id": resource_id,
            "q": nombre,
            "limit": 10
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            return data["result"].get("records", [])
    except requests.RequestException:
        pass
    return []


def lookup_ddjj(nombre: str) -> dict:
    """
    Busca declaraciones juradas patrimoniales de funcionarios públicos por nombre.

    Args:
        nombre: Nombre completo del funcionario a buscar (ej: "Juan Perez")

    Returns:
        dict con claves:
            - found (bool): si se encontraron resultados
            - results (list): lista de declaraciones encontradas
            - fuente (str): URL de la fuente para verificación manual
            - error (str|None): mensaje de error si ocurrió alguno
    """
    fuente = f"https://datos.jus.gob.ar/dataset/{DDJJ_PACKAGE_ID}"

    resources = _get_ddjj_resources()
    if not resources:
        # Fallback: búsqueda general en el portal de la OA
        return {
            "found": False,
            "results": [],
            "fuente": fuente,
            "error": "No se pudo acceder al portal datos.jus.gob.ar. Verificar manualmente en: "
                     "https://www.argentina.gob.ar/anticorrupcion/declaraciones-juradas"
        }

    all_records = []
    # Buscar en los recursos datastore-habilitados (generalmente los CSV más recientes)
    for resource in resources[:3]:  # Limitar a los 3 más recientes para no sobrecargar
        if resource.get("datastore_active"):
            records = _search_in_resource(resource["id"], nombre)
            for rec in records:
                rec["_recurso_nombre"] = resource.get("name", "")
                rec["_recurso_url"] = resource.get("url", "")
            all_records.extend(records)

    if not all_records:
        return {
            "found": False,
            "results": [],
            "fuente": fuente,
            "error": None
        }

    # Normalizar campos clave que pueden variar entre datasets
    normalized = []
    for rec in all_records:
        normalized.append({
            "nombre": rec.get("nombre_apellido") or rec.get("nombre") or rec.get("funcionario", "N/D"),
            "cargo": rec.get("cargo") or rec.get("funcion", "N/D"),
            "jurisdiccion": rec.get("jurisdiccion") or rec.get("organismo", "N/D"),
            "año": rec.get("anio") or rec.get("año") or rec.get("periodo", "N/D"),
            "tipo": rec.get("tipo_declaracion", "N/D"),
            "fuente_recurso": rec.get("_recurso_url", fuente)
        })

    return {
        "found": True,
        "results": normalized,
        "fuente": fuente,
        "error": None
    }
