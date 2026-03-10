# Guía de Usuario: OSINT Argentina CLI

Esta guía detalla el uso avanzado de los módulos integrados en `osint_ar.py`, con especial énfasis en las diferencias entre las capacidades de recolección de correos electrónicos.

## Búsqueda de Correos vs Cosecha de Dominios

Es fundamental entender la diferencia entre buscar el registro de un correo (`-e`) y cosechar correos de un dominio (`-H`).

### 1. Búsqueda por Email (`-e` o `--email`)

Este comando actúa como un **comprobante de registro**. Su objetivo es confirmar en qué plataformas de internet existe una cuenta creada con ese correo en particular.
*Utiliza la lógica interna inspirada en la herramienta global `holehe`.*

*   **¿Qué ingresar?:** Una **dirección de correo electrónico completa y válida** (ej. `juan.perez@mercadolibre.com.ar`).
*   **¿Qué NO ingresar?:** Un dominio o una URL (ej. `mercadolibre.com.ar`). Si ingresas un dominio, la herramienta detectará el error de formato y detendrá la ejecución para evitar falsos positivos.
*   **Ejemplo de uso:**
    ```bash
    python osint_ar.py -e contacto@ejemplo.com.ar
    ```
*   **Resultado esperado:** Una lista de plataformas (ej. Twitter, Amazon, Instagram) donde ese correo está registrado.

### 2. Cosecha Perimetral de Emails (`-H` o `--harvest`)

Este comando actúa como un **recolector exploratorio**. Su objetivo es encontrar qué direcciones de correo electrónico pertenecientes a una empresa u organismo están expuestas públicamente en internet.
*Utiliza lógicas inspiradas en `theHarvester` (Scraping pasivo de DuckDuckGo) y `Photon` (Crawling web RegExp).*

*   **¿Qué ingresar?:** Un **dominio web** (ej. `mercadolibre.com.ar` o `argentina.gob.ar`).
*   **¿Qué NO ingresar?:** Una dirección de correo. 
*   **Ejemplo de uso:**
    ```bash
    python osint_ar.py -H afip.gob.ar
    ```
*   **Resultado esperado:** 
    1.  Verificación de existencia de registros MX (comprueba si el dominio puede recibir correos o si es un "falso positivo" estructural).
    2.  Una lista de correos electrónicos descubiertos (ej. `rrhh@afip.gob.ar`, `denuncias@afip.gob.ar`).

---

## Otros Módulos Disponibles

*   **Búsqueda de Usuario (`-u`):** Verifica si un nombre de usuario ("nickname") existe transversalmente en múltiples redes sociales.
    `python osint_ar.py -u osintbrazuca`

*   **Validador de CUIT/CUIL (`-c`):** Utiliza lógica matemática para confirmar que un número de 11 dígitos corresponde a un CUIL/CUIT real en Argentina, informando si pertenece a un hombre, mujer o sociedad.
    `python osint_ar.py -c 20123456781`

*   **Información de Dominio (`-d`):** Consulta la IP de un dominio y estima su estado de registro (útil previo a una consulta manual en NIC.ar).
    `python osint_ar.py -d clarin.com`
