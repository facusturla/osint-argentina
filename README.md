# OSINT Argentina

<p align="center">
  <img src="assets/banner.png" alt="OSINT Argentina Banner" width="100%">
</p>

![OSINT](https://img.shields.io/badge/OSINT-Argentina-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Contributions](https://img.shields.io/badge/Contributions-Welcome-brightgreen?style=for-the-badge)

Repositorio dedicado a la recopilación y organización de herramientas, bases de datos públicas, registros gubernamentales y fuentes de información abierta (OSINT) centradas exclusivamente en la República Argentina.

Este proyecto tiene como objetivo centralizar los recursos dispersos para facilitar la investigación, el periodismo de datos y el análisis de inteligencia de fuentes abiertas en el contexto local. Ninguno de los enlaces o herramientas publicados aquí alojan datos per se, sino que dirigen a sitios de dominio público o herramientas de terceros.

## Avisos Legales y Éticos

La información listada en este repositorio apunta a fuentes de acceso público y legal. El uso de estos recursos debe realizarse en el marco de la **Ley 25.326 de Protección de los Datos Personales** y demás normativas vigentes en el territorio argentino. Los autores y contribuyentes no se responsabilizan por el mal uso de la información obtenida a través de los enlaces aquí provistos. Toda recolección y tratamiento de datos es bajo estricta responsabilidad del analista.

##  Herramienta OSINT Argentina (HIFA ARGENTINA)

Junto al repositorio documental, hemos desarrollado un script modular en Python (`osint_ar.py`) para automatizar las búsquedas iniciales más comunes. **La herramienta es 100% segura, de código abierto, corre localmente en tu máquina y NO requiere ni expone ninguna API Key externa.**

### Instalación

1. Clona el repositorio e ingresa al directorio:
   ```bash
   git clone https://github.com/facusturla/osint-argentina.git
   cd osint-argentina
   ```
2. Instala los requerimientos de Python:
   ```bash
   pip install -r requirements.txt
   ```

### Uso

Actualmente, el script cuenta con 3 módulos principales:

*   **Búsqueda de Usuario (`-u`):** Rastrea la existencia de un *username* específico en redes sociales globales y plataformas locales (MercadoLibre, Taringa histórico, etc.).
    `python osint_ar.py -u usuario`
*   **Averiguación de Dominio (`-d`):** Recupera la dirección IP de un dominio y verifica si está registrado (especialmente útil para entender el estado de dominios `.ar` frente a NIC.ar).
    `python osint_ar.py -d pagina web`
*   **Validador de CUIT/CUIL (`-c`):** Valida matemáticamente (vía dígito verificador) si un número de CUIT o CUIL es real, e infiere el género o el tipo de persona/sociedad.
    `python osint_ar.py -c 12345678910`

---

## Directorio de Fuentes y Registros

1. [Identidad y Registros de Personas](#identidad-y-registros-de-personas)
- [OSINT Argentina](#osint-argentina)
  - [Avisos Legales y Éticos](#avisos-legales-y-éticos)
  - [Herramienta OSINT Argentina (HIFA ARGENTINA)](#herramienta-osint-argentina-hifa-argentina)
    - [Instalación](#instalación)
    - [Uso](#uso)
  - [Directorio de Fuentes y Registros](#directorio-de-fuentes-y-registros)
    - [Identidad y Registros de Personas](#identidad-y-registros-de-personas)
    - [Empresas, Finanzas y Tributación](#empresas-finanzas-y-tributación)
    - [Poder Judicial y Antecedentes](#poder-judicial-y-antecedentes)
    - [Vehículos y Transporte](#vehículos-y-transporte)
    - [Transparencia y Compras Públicas](#transparencia-y-compras-públicas)
    - [Telecomunicaciones y Dominios](#telecomunicaciones-y-dominios)
    - [Datos Abiertos y Estadísticas](#datos-abiertos-y-estadísticas)
    - [Fuentes No Oficiales y Herramientas a Terceros](#fuentes-no-oficiales-y-herramientas-a-terceros)
    - [Herramientas Internacionales Recomendadas](#herramientas-internacionales-recomendadas)
  - [Contribuciones](#contribuciones)

---

### Identidad y Registros de Personas

Fuentes gubernamentales para la validación de identidad y registros civiles.

*   [Constancia de CUIL (ANSES)](https://www.anses.gob.ar/consultas/constancia-de-cuil) - Verificación de Código Único de Identificación Laboral.
*   [Consulta de Obra Social / CODEM (ANSES)](https://www.anses.gob.ar/consultas/obra-social-codem) - Comprobante de empadronamiento.
*   [Padrón Electoral (CNE)](https://www.padron.gob.ar/) - Consulta de datos electorales y lugar de votación. Puede revelar el último domicilio actualizado del elector.
*   [Registro Nacional de las Personas (RENAPER)](https://www.argentina.gob.ar/interior/renaper) - Validacion de identidad vinculada a trámites gubernamentales.
*   [Sistema de Identificación Nacional Tributario y Social (SINTyS)](https://www.argentina.gob.ar/jefatura/innovacion-publica/sintys) - Coordinación de datos e intercambio de información entre organismos del Estado.

### Empresas, Finanzas y Tributación

Herramientas para el rastreo de sociedades, historiales crediticios y estado tributario.

*   [Boletín Oficial de la República Argentina (BORA)](https://www.boletinoficial.gob.ar/) - Publicación de edictos, constitución de sociedades (SRL, SA), concursos, quiebras y nombramientos.
*   [Central de Deudores (BCRA)](https://www.bcra.gob.ar/BCRAyVos/Situacion_Crediticia.asp) - Historial crediticio, cheques rechazados y deudas financieras registradas en el Banco Central (Cálculo de riesgo crediticio).
*   [Constancia de CUIT (AFIP)](https://cuitonline.afip.gob.ar/constancia/jrun/InicioMac.do) - Verificación de inscripción tributaria y actividades inscriptas.
*   [Facturación y Registros Apócrifos (AFIP)](https://serviciosweb.afip.gob.ar/genericos/facturasApocrifas/default.aspx) - Base de datos pública de contribuyentes con facturación irregular.
*   [Inspección General de Justicia (IGJ)](https://www.argentina.gob.ar/justicia/igj) - Trámites y búsqueda de entidades comerciales y civiles en la órbita nacional.
*   [Personas Jurídicas PBA (DPPJ)](https://www.gba.gob.ar/dppj) - Dirección Provincial de Personas Jurídicas de la Provincia de Buenos Aires.
*   [Nomenclador de Actividades Económicas (AFIP)](https://www.afip.gob.ar/actividades/) - Consulta de códigos de actividad económica (CLAE).

### Poder Judicial y Antecedentes

Sistemas de búsqueda de expedientes, resoluciones y jurisprudencia.

*   [Consulta de Causas (Poder Judicial de la Nación)](http://scw.pjn.gov.ar/scw/home.seam) - Búsqueda pública de expedientes federales y nacionales (Penal, Comercial, Civil).
*   [Mesa de Entradas Virtual (MEV) - PBA](https://mev.scba.gov.ar/) - Suprema Corte de Justicia de la Provincia de Buenos Aires. Requiere registro gratuito.
*   [Centro de Información Judicial (CIJ)](https://www.cij.gov.ar/) - Resoluciones, fallos emblemáticos y noticias del Máximo Tribunal y Casación.
*   [Información Útil del Poder Judicial CABA (Iurix)](https://eje.juscaba.gob.ar/iol-ui/p/inicio) - Consulta de expedientes de la Justicia de la Ciudad Autónoma de Buenos Aires.
*   [Datos de la Justicia Argentina (DatosJus)](https://datos.jus.gob.ar/) - Estadísticas y portales de datos abiertos del Ministerio de Justicia.

### Vehículos y Transporte

Rastreo de dominios, multas e infracciones, y titularidad vehicular.

*   [Radicación de Dominio (DNRPA)](https://www.dnrpa.gov.ar/portal_dnrpa/radicacion.php) - Consulta de la seccional (registro automotor) donde se encuentra radicado el vehículo según la patente.
*   [Consulta de Infracciones y Multas (CABA)](https://buenosaires.gob.ar/licencias-de-conducir/consulta-de-infracciones) - Multas de tránsito en la Ciudad Autónoma de Buenos Aires.
*   [Consulta de Infracciones (PBA)](https://infraccionesba.mgob.gba.gob.ar/consulta-infraccion) - Multas de tránsito en la Provincia de Buenos Aires.
*   [Caminera Córdoba - Consulta de Multas](https://caminera.cba.gov.ar/) - Policía Caminera de la Provincia de Córdoba.
*   [Deuda de Patentes (AGIP)](https://www.agip.gob.ar/) - Consulta de estado de cuenta de automotores radicados en CABA.
*   [Deuda de Patentes (ARBA)](https://www.arba.gov.ar/) - Consulta de estado de cuenta de automotores radicados en PBA.
*   [Registro de Buques (Prefectura Naval Argentina)](https://www.argentina.gob.ar/prefecturanaval/registro-nacional-de-buques) - Regulaciones y matrículas.
*   [Registro Nacional de Aeronaves (ANAC)](https://www.argentina.gob.ar/anac/registro-nacional-de-aeronaves) - Matrículas de aeronaves civiles.

### Transparencia y Compras Públicas

Seguimiento de fondos públicos, licitaciones y patrimonio de funcionarios.

*   [Portal Nacional de Datos Abiertos](https://datos.gob.ar/) - Dataset consolidado del Estado Nacional.
*   [Compr.AR](https://comprar.gob.ar/) - Portal del Sistema Electrónico de Contrataciones Públicas.
*   [Contrat.AR](https://contratar.gob.ar/) - Sistema Electrónico de Contrataciones de Obra Pública.
*   [Buenos Aires Compras (BAC)](https://buenosairescompras.gob.ar/) - Sistema de compras de CABA.
*   [Declaraciones Juradas Abiertas (Oficina Anticorrupción)](https://www.argentina.gob.ar/anticorrupcion/declaraciones-juradas) - Consultas de patrimonio declarado de funcionarios públicos nacionales.
*   [Registro de Audiencias de Gestión de Intereses](https://audiencias.mininterior.gob.ar/) - Registro público de audiencias de funcionarios del Poder Ejecutivo Nacional.

### Telecomunicaciones y Dominios

Información de licenciatarios, infraestructura de red y registros web.

*   [NIC Argentina (WHOIS)](https://nic.ar/es/dominios/herramientas) - Registro de dominios `.ar` y `.com.ar`. Permite conocer la titularidad parcial de un dominio si los datos fuesen públicos.
*   [ENACOM - Datos Abiertos](https://datosabiertos.enacom.gob.ar/) - Registros de radiodifusión, prestadores de servicios de internet y bases de antenas.
*   [Portabilidad Numérica](https://www.portabilidad.gob.ar/) - Información sobre el régimen de portabilidad en Argentina.

### Datos Abiertos y Estadísticas

Estadísticas sociodemográficas, mapas y datos para análisis en bruto.

*   [Instituto Nacional de Estadística y Censos (INDEC)](https://www.indec.gob.ar/) - Bases de datos y censos nacionales. Microdatos útiles para análisis sociodemográfico.
*   [IGN - Instituto Geográfico Nacional](https://www.ign.gob.ar/) - Información geoespacial, mapas oficiales y capas GIS.
*   [IDE - Infraestructura de Datos Espaciales](https://www.idera.gob.ar/) - Mapas interactivos y geoservicios de Argentina.
*   [Base de Datos de Suelos (INTA)](https://geointa.inta.gob.ar/) - Información sobre tipos de suelos e imágenes satelitales agrícolas.

---

### Fuentes No Oficiales y Herramientas a Terceros

> **AVISO IMPORTANTE:** Los siguientes sitios operan bajo dominios y servidores privados ajenos a cualquier dependencia gubernamental del Estado Argentino. **El autor de este repositorio no aprueba ni se hace responsable por la precisión, origen legal, tratamiento de datos o políticas de privacidad de dichas plataformas.** El investigador asume toda la responsabilidad civil y penal derivada de su uso, como así también la verificación cruzada de la información allí recabada. Se proveen netamente con fines documentales e investigativos.

*   [CuitOnline](https://www.cuitonline.com/) - Directorio comercial derivado del padrón de AFIP. Ofrece información tributaria pública agregada de personas físicas y jurídicas.
*   [Dateas](https://www.dateas.com/es/argentina) - Buscador privado de información pública e informes de riesgo comercial e identidad en Argentina.
*   [Nosis](https://www.nosis.com/es) - Buró de crédito e información comercial. Provee reportes financieros avanzados (generalmente bajo suscripción).
*   [Veraz (Equifax)](https://www.veraz.com.ar/) - Principal base de datos privada de historiales financieros y deudas crediticias.
*   [BuscarDatos](https://buscardatos.com/) - Buscador privado (a menudo con datos desactualizados) que indexa padrones telefónicos, DNI y CUIT.
*   [Telexplorer](https://www.telexplorer.com.ar/) - Guía telefónica inversa (residencial y comercial) para Argentina.
*   [Voligoma.com.ar (Internet Archive)](https://web.archive.org/web/*/voligoma.com.ar) - [Histórico] Indexador de registros que actualmente suele requerir WayBack Machine para análisis retrospectivos.

---

### Herramientas Internacionales Recomendadas

Aunque este repositorio se enfoca en fuentes de Argentina, existen frameworks globales esenciales que son el estándar de la industria para complementar la investigación OSINT:

*   [Sherlock](https://github.com/sherlock-project/sherlock) - Herramienta fundamental para la búsqueda de cuentas de usuario por *username* a través de cientos de redes sociales y foros.
*   [Maigret](https://github.com/soxoj/maigret) - Un avanzado *fork* de Sherlock enfocado en recopilar un dossier completo de un usuario, buscar en perfiles públicos y generar reportes analíticos.
*   [Photon](https://github.com/s0md3v/Photon) - Increíblemente veloz *web crawler* extrae inteligentemente URLs, archivos, correos electrónicos, cuentas en redes y claves de API del sitio objetivo.
*   [theHarvester](https://github.com/laramies/theHarvester) - Herramienta diseñada para la recolección temprana de inteligencia perimetral (emails, subdominios, IPs y URLs) utilizando fuentes públicas.

---

## Contribuciones

Se agradecen las sugerencias, reportes de enlaces caídos y sumas de nuevas herramientas orientadas a **OSINT Argentina**. Por favor, abrí un *Issue* o enviá un *Pull Request* considerando que la documentación añadida sea legal, pública y mantenga un estándar profesional.

