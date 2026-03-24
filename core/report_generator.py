"""
Módulo: report_generator.py
Descripción: Generación de reportes OSINT estructurados en formato JSON o HTML.
             Consolida los resultados de todos los módulos en un dossier exportable.
"""

import json
import os
from datetime import datetime


def _html_section(title: str, content: str) -> str:
    return f"""
    <section>
        <h2>{title}</h2>
        <div class="content">{content}</div>
    </section>"""


def _dict_to_html_table(data: dict) -> str:
    if not data:
        return "<p><em>Sin datos.</em></p>"
    rows = "".join(
        f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>"
        for k, v in data.items()
    )
    return f"<table><tbody>{rows}</tbody></table>"


def _list_to_html(items: list) -> str:
    if not items:
        return "<p><em>Sin resultados.</em></p>"
    if isinstance(items[0], dict):
        html = ""
        for item in items:
            html += _dict_to_html_table(item) + "<hr>"
        return html
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def generate_report(target: str, results: dict, output_format: str = "json") -> str:
    """
    Genera un reporte OSINT con los resultados recopilados.

    Args:
        target: El objetivo investigado (username, email, CUIT, dominio, etc.)
        results: Diccionario con los resultados de cada módulo ejecutado.
                 Ej: {"cuit": {...}, "username": {...}, "bcra": {...}}
        output_format: "json" o "html"

    Returns:
        Ruta al archivo generado.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_target = "".join(c for c in target if c.isalnum() or c in "._-@")
    filename = f"reporte_{safe_target}_{timestamp}.{output_format}"

    report_data = {
        "meta": {
            "herramienta": "OSINT Argentina (HIFA)",
            "version": "1.0",
            "objetivo": target,
            "timestamp": datetime.now().isoformat(),
            "aviso_legal": (
                "Este reporte fue generado con fines investigativos mediante fuentes públicas. "
                "El uso debe enmarcarse en la Ley 25.326 de Protección de los Datos Personales."
            )
        },
        "resultados": results
    }

    if output_format == "json":
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

    elif output_format == "html":
        sections_html = ""
        module_titles = {
            "cuit": "Validación CUIT/CUIL",
            "username": "Búsqueda de Usuario",
            "email": "Búsqueda de Email",
            "harvest": "Cosecha de Emails por Dominio",
            "domain": "Información de Dominio",
            "ddjj": "Declaraciones Juradas (DDJJ)",
            "bcra": "Central de Deudores BCRA",
            "georef": "Normalización de Domicilio"
        }

        for module, data in results.items():
            title = module_titles.get(module, module.upper())
            if isinstance(data, dict):
                content = _dict_to_html_table(data)
            elif isinstance(data, list):
                content = _list_to_html(data)
            else:
                content = f"<p>{data}</p>"
            sections_html += _html_section(title, content)

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte OSINT — {target}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
        h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
        h2 {{ color: #79c0ff; margin-top: 30px; }}
        section {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; margin: 16px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
        td {{ padding: 8px 12px; border-bottom: 1px solid #21262d; vertical-align: top; }}
        td:first-child {{ width: 35%; color: #8b949e; }}
        .meta {{ background: #1c2128; border: 1px solid #30363d; border-radius: 6px; padding: 12px; margin-bottom: 20px; font-size: 0.85em; color: #8b949e; }}
        .aviso {{ background: #2d1a00; border: 1px solid #bb8009; border-radius: 6px; padding: 12px; margin-top: 20px; color: #e3b341; font-size: 0.85em; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 4px 0; }}
        hr {{ border: none; border-top: 1px solid #21262d; margin: 12px 0; }}
    </style>
</head>
<body>
    <h1>Reporte OSINT Argentina</h1>
    <div class="meta">
        <strong>Objetivo:</strong> {target} &nbsp;|&nbsp;
        <strong>Generado:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} &nbsp;|&nbsp;
        <strong>Herramienta:</strong> HIFA Argentina v1.0
    </div>
    {sections_html}
    <div class="aviso">
        <strong>Aviso Legal:</strong> Este reporte fue generado con fines investigativos mediante fuentes públicas.
        El uso debe enmarcarse en la <strong>Ley 25.326 de Protección de los Datos Personales</strong>.
    </div>
</body>
</html>"""

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

    return os.path.abspath(filename)
