"""
Módulo: bcra_lookup.py
Descripción: Consulta del historial crediticio de una persona física o jurídica
             en la Central de Deudores del BCRA (Banco Central de la República Argentina).

API pública del BCRA — sin API key requerida.
Documentación: https://api.bcra.gob.ar/
"""

import re
import requests

BCRA_API_BASE = "https://api.bcra.gob.ar"
BCRA_WEB_DEUDORES = "https://www.bcra.gob.ar/BCRAyVos/Situacion_Crediticia.asp"

HEADERS = {
    "User-Agent": "OSINT-Argentina/1.0 (investigacion academica)",
    "Accept": "application/json"
}

TIMEOUT = 10

# Códigos de situación crediticia según normativa BCRA (Com. A 2216 y modificatorias)
SITUACION_LABELS = {
    1: "Situación normal (sin atrasos)",
    2: "Riesgo bajo (atraso hasta 90 días)",
    3: "Riesgo medio (atraso 91-180 días)",
    4: "Riesgo alto (atraso 181-365 días)",
    5: "Irrecuperable (atraso > 365 días)",
    6: "Irrecuperable por disposición técnica"
}


def _clean_cuit(cuit: str) -> str:
    """Elimina guiones y espacios del CUIT/CUIL para normalizarlo."""
    return re.sub(r"[\-\s]", "", cuit.strip())


def lookup_bcra_deudores(cuit: str) -> dict:
    """
    Consulta la Central de Deudores del BCRA para un CUIT/CUIL dado.

    Args:
        cuit: Número de CUIT/CUIL (con o sin guiones, ej: "20-12345678-9" o "20123456789")

    Returns:
        dict con claves:
            - found (bool): si se encontró información crediticia
            - cuit (str): CUIT consultado normalizado
            - situacion_maxima (int|None): peor situación registrada en el período
            - entidades (list): lista de entidades que reportaron al BCRA
            - periodo (str): período del reporte (AAAAMM)
            - fuente (str): URL de la fuente para verificación manual
            - error (str|None): mensaje de error si ocurrió alguno
    """
    cuit_clean = _clean_cuit(cuit)

    if len(cuit_clean) != 11 or not cuit_clean.isdigit():
        return {
            "found": False,
            "cuit": cuit_clean,
            "situacion_maxima": None,
            "entidades": [],
            "periodo": None,
            "fuente": BCRA_WEB_DEUDORES,
            "error": f"CUIT inválido: '{cuit}'. Debe tener 11 dígitos numéricos."
        }

    # Intentar el endpoint de deudas por identificación
    url = f"{BCRA_API_BASE}/CentralDeDeudores/v1.0/Deudas/{cuit_clean}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

        if resp.status_code == 404:
            return {
                "found": False,
                "cuit": cuit_clean,
                "situacion_maxima": None,
                "entidades": [],
                "periodo": None,
                "fuente": BCRA_WEB_DEUDORES,
                "error": None  # 404 significa que no hay deudas registradas
            }

        resp.raise_for_status()
        data = resp.json()

        # La respuesta del BCRA tiene estructura: { "results": { "identificacion": ..., "periodos": [...] } }
        results = data.get("results", {})
        periodos = results.get("periodos", [])

        if not periodos:
            return {
                "found": False,
                "cuit": cuit_clean,
                "situacion_maxima": None,
                "entidades": [],
                "periodo": None,
                "fuente": BCRA_WEB_DEUDORES,
                "error": None
            }

        # Tomar el período más reciente
        ultimo_periodo = periodos[0]
        periodo_str = str(ultimo_periodo.get("periodo", ""))
        entidades_raw = ultimo_periodo.get("entidades", [])

        entidades = []
        situacion_max = 1
        for ent in entidades_raw:
            sit = ent.get("situacion", 1)
            if sit > situacion_max:
                situacion_max = sit
            entidades.append({
                "entidad": ent.get("entidad", "N/D"),
                "situacion": sit,
                "situacion_descripcion": SITUACION_LABELS.get(sit, f"Código {sit}"),
                "monto_pesos": ent.get("monto", None)
            })

        return {
            "found": True,
            "cuit": cuit_clean,
            "situacion_maxima": situacion_max,
            "situacion_descripcion": SITUACION_LABELS.get(situacion_max, f"Código {situacion_max}"),
            "entidades": entidades,
            "periodo": periodo_str,
            "fuente": BCRA_WEB_DEUDORES,
            "error": None
        }

    except requests.exceptions.ConnectionError:
        return {
            "found": False,
            "cuit": cuit_clean,
            "situacion_maxima": None,
            "entidades": [],
            "periodo": None,
            "fuente": BCRA_WEB_DEUDORES,
            "error": "No se pudo conectar con la API del BCRA. Verificar manualmente en: "
                     + BCRA_WEB_DEUDORES
        }
    except requests.RequestException as exc:
        return {
            "found": False,
            "cuit": cuit_clean,
            "situacion_maxima": None,
            "entidades": [],
            "periodo": None,
            "fuente": BCRA_WEB_DEUDORES,
            "error": f"Error al consultar la API del BCRA: {exc}"
        }
