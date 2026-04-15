import os
import json
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic

from tools import load_dataset, analyze_dataset, save_report


load_dotenv()

MODEL_NAME = "claude-haiku-4-5"

SYSTEM_PROMPT = """
Eres un agente autónomo de análisis de datos.

Tu trabajo es completar la tarea usando herramientas cuando sea necesario.
Debes intentar terminar la tarea sin pedir intervención humana.

Reglas:
1. Usa las tools disponibles cuando aporten valor real.
2. Sigue un flujo lógico: cargar datos -> analizarlos -> guardar informe.
3. Si una tool devuelve error, no te bloquees:
   - explica el problema
   - y, si es posible, guarda igualmente un informe con el error.
4. No inventes resultados.
5. Sé breve, claro y operativo.
""".strip()


TOOLS = [
    {
        "name": "load_dataset",
        "description": (
            "Carga un archivo CSV o JSON y devuelve columnas, número de filas y registros. "
            "Úsala siempre al principio antes de analizar los datos."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Ruta del archivo CSV o JSON que hay que cargar."
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "analyze_dataset",
        "description": (
            "Analiza los registros cargados y detecta problemas de calidad de datos: "
            "campos vacíos, duplicados, fechas inválidas, emails inválidos, errores numéricos "
            "e incoherencias en totales."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "records": {
                    "type": "array",
                    "description": "Lista de registros del dataset en formato JSON.",
                    "items": {
                        "type": "object"
                    }
                }
            },
            "required": ["records"]
        }
    },
    {
        "name": "save_report",
        "description": (
            "Guarda un informe final en formato texto o markdown en la ruta indicada."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "report_text": {
                    "type": "string",
                    "description": "Texto completo del informe a guardar."
                },
                "output_path": {
                    "type": "string",
                    "description": "Ruta donde guardar el informe."
                }
            },
            "required": ["report_text", "output_path"]
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Ejecuta la tool solicitada por Claude."""
    try:
        if tool_name == "load_dataset":
            return load_dataset(tool_input["file_path"])

        if tool_name == "analyze_dataset":
            return analyze_dataset(tool_input["records"])

        if tool_name == "save_report":
            return save_report(
                report_text=tool_input["report_text"],
                output_path=tool_input["output_path"]
            )

        return {
            "status": "error",
            "message": f"Tool desconocida: {tool_name}"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error ejecutando la tool {tool_name}: {e}"
        }


def get_text_from_content_blocks(content_blocks) -> str:
    """Extrae solo los bloques de texto de la respuesta del modelo."""
    parts = []

    for block in content_blocks:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)

    return "\n".join(parts).strip()


def normalize_input_path(file_path: str) -> Path:
    """Convierte la ruta de entrada en absoluta."""
    base_dir = Path(__file__).resolve().parent
    path = Path(file_path)

    if not path.is_absolute():
        path = (base_dir / path).resolve()

    return path


def run_agent(file_path: str) -> dict:
    """Lanza el agente y deja que complete la tarea con tools."""
    input_path = normalize_input_path(file_path)
    base_dir = Path(__file__).resolve().parent
    output_path = (base_dir / "outputs" / f"informe_{input_path.stem}.md").resolve()

    try:
        client = Anthropic()

        user_prompt = f"""
Analiza el archivo situado en esta ruta:

{input_path}

Objetivo:
- revisa la calidad de los datos
- detecta errores o anomalías
- genera un informe final y guárdalo en esta ruta:

{output_path}

Flujo esperado:
1. Usa load_dataset con la ruta del archivo.
2. Usa analyze_dataset con los records obtenidos.
3. Usa save_report para guardar el informe final.

Importante:
- Trabaja de forma autónoma.
- No me pidas información adicional.
- Si ocurre un error, intenta igualmente generar y guardar un informe explicándolo.
""".strip()

        messages = [
            {
                "role": "user",
                "content": user_prompt
            }
        ]

        max_iterations = 8

        for iteration in range(1, max_iterations + 1):
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )

            print(f"\n=== Iteración {iteration} | stop_reason={response.stop_reason} ===")

            assistant_text = get_text_from_content_blocks(response.content)
            if assistant_text:
                print(assistant_text)

            messages.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []

            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    print(f"\n-> Claude quiere usar la tool: {block.name}")
                    print(f"   Input: {block.input}")

                    result = execute_tool(block.name, block.input)

                    print(f"<- Resultado de la tool: {result.get('status', 'desconocido')}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False)
                    })

            if not tool_results:
                return {
                    "status": "ok",
                    "final_text": assistant_text or "Tarea completada.",
                    "output_path": str(output_path)
                }

            messages.append({
                "role": "user",
                "content": tool_results
            })

        report_text = f"""# Informe de ejecución del agente

## Estado
No se pudo completar la tarea en el número máximo de iteraciones.

## Archivo analizado
{input_path}

## Resultado
El agente alcanzó el límite de iteraciones sin cerrar la tarea.

## Recomendación
Revisar el prompt, las tools o la conectividad con la API.
"""
        save_report(report_text, str(output_path))

        return {
            "status": "error",
            "final_text": "Se alcanzó el número máximo de iteraciones sin completar la tarea.",
            "output_path": str(output_path)
        }

    except Exception as e:
        error_text = f"""# Informe de error del agente

## Estado
La ejecución del agente falló antes de completarse.

## Archivo solicitado
{input_path}

## Error detectado
{type(e).__name__}: {e}

## Posible causa
- API key ausente
- API key inválida
- falta de acceso o saldo en la cuenta
- problema de conexión con la API

## Qué sí funciona
Las tools locales del proyecto siguen siendo válidas:
- carga de CSV/JSON
- análisis del dataset
- generación de informes

## Siguiente paso recomendado
Configurar una API key válida en el archivo .env y repetir la prueba.
"""
        save_report(error_text, str(output_path))

        return {
            "status": "error",
            "final_text": f"Error de ejecución del agente: {type(e).__name__}: {e}",
            "output_path": str(output_path)
        }