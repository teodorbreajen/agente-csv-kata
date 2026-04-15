# Agente CSV con Kata

Agente CSV que utiliza herramientas para procesamiento y análisis de datos mediante llamadas a API.

## Estructura

`
main.py          - Punto de entrada del agente
tools.py         - Herramientas disponibles
data/            - Archivos CSV de entrada
outputs/         - Informes generados
.env             - Configuración de API
`

## Uso

\\\ash
pip install -r requirements.txt
python main.py
\\\

## Herramientas

- Análisis de archivos CSV
- Generación de informes
- Validación de datos
- Conexión a APIs externas

## Configuración

1. Configurar API key en \.env\
2. Colocar archivos CSV en \data/\
3. Ejecutar el agente

## Recursos

- \Guia_Agente_CSV_Con_API_Claude.docx\ - Guía con API
- \Guia_Agente_CSV_Simulacion_Sin_API.docx\ - Guía sin API

## Tecnologías

- Python 3.11+
- Claude API / mock mode
- CSV parsing