from pathlib import Path
from datetime import datetime
import re
import pandas as pd


# Columnas que esperamos en el CSV
REQUIRED_COLUMNS = [
    "id_venta",
    "fecha",
    "cliente",
    "producto",
    "cantidad",
    "precio",
    "total",
    "email",
]

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_value(value) -> str:
    """Convierte valores vacíos o NaN a cadena vacía y limpia espacios."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def _to_float(value: str):
    """Intenta convertir a float. Si no puede, devuelve None."""
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


def _is_valid_date(date_text: str) -> bool:
    """Valida fecha en formato YYYY-MM-DD."""
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def load_dataset(file_path: str) -> dict:
    """
    Tool 1: carga un CSV o JSON y devuelve los registros en formato estructurado.
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return {
                "status": "error",
                "message": f"El archivo no existe: {file_path}"
            }

        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path, dtype=str)
        elif path.suffix.lower() == ".json":
            df = pd.read_json(path)
        else:
            return {
                "status": "error",
                "message": "Formato no soportado. Usa .csv o .json"
            }

        df = df.fillna("").astype(str)

        return {
            "status": "ok",
            "file_path": str(path),
            "columns": list(df.columns),
            "row_count": int(len(df)),
            "records": df.to_dict(orient="records")
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error al cargar el archivo: {e}"
        }


def analyze_dataset(records: list) -> dict:
    """
    Tool 2: analiza los registros y detecta problemas de calidad de datos.
    """
    try:
        if not records:
            return {
                "status": "error",
                "message": "No hay registros para analizar."
            }

        df = pd.DataFrame(records).fillna("").astype(str)

        issues = []
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]

        def add_issue(row_number, severity, field, message, value=""):
            issues.append({
                "row": row_number,
                "severity": severity,
                "field": field,
                "message": message,
                "value": value
            })

        # 1) Validar columnas obligatorias
        if missing_columns:
            for col in missing_columns:
                add_issue(
                    row_number="estructura",
                    severity="error",
                    field=col,
                    message="Falta columna obligatoria",
                    value=""
                )

        # Si faltan columnas importantes, seguimos igualmente para mostrar robustez,
        # pero solo analizaremos lo que exista.
        available_columns = set(df.columns)

        # 2) Validar campos vacíos por fila
        for idx, row in df.iterrows():
            row_number = idx + 2  # +2 porque la línea 1 es la cabecera del CSV

            for col in REQUIRED_COLUMNS:
                if col in available_columns:
                    value = _clean_value(row[col])
                    if value == "":
                        add_issue(
                            row_number=row_number,
                            severity="error",
                            field=col,
                            message="Campo obligatorio vacío",
                            value=value
                        )

        # 3) Detectar duplicados de id_venta
        if "id_venta" in available_columns:
            ids = df["id_venta"].apply(_clean_value)
            duplicated_mask = ids.duplicated(keep=False) & (ids != "")
            for idx in df[duplicated_mask].index:
                add_issue(
                    row_number=idx + 2,
                    severity="error",
                    field="id_venta",
                    message="ID de venta duplicado",
                    value=_clean_value(df.loc[idx, "id_venta"])
                )

        # 4) Validar fecha
        if "fecha" in available_columns:
            for idx, value in df["fecha"].items():
                value = _clean_value(value)
                if value and not _is_valid_date(value):
                    add_issue(
                        row_number=idx + 2,
                        severity="error",
                        field="fecha",
                        message="Fecha inválida. Se espera formato YYYY-MM-DD",
                        value=value
                    )

        # 5) Validar email
        if "email" in available_columns:
            for idx, value in df["email"].items():
                value = _clean_value(value)
                if value and not EMAIL_REGEX.match(value):
                    add_issue(
                        row_number=idx + 2,
                        severity="error",
                        field="email",
                        message="Email inválido",
                        value=value
                    )

        # 6) Validar cantidad, precio y total
        numeric_fields = ["cantidad", "precio", "total"]

        for field in numeric_fields:
            if field in available_columns:
                for idx, value in df[field].items():
                    clean_value = _clean_value(value)
                    if clean_value == "":
                        continue

                    numeric_value = _to_float(clean_value)
                    if numeric_value is None:
                        add_issue(
                            row_number=idx + 2,
                            severity="error",
                            field=field,
                            message="Valor numérico inválido",
                            value=clean_value
                        )
                    elif numeric_value < 0:
                        add_issue(
                            row_number=idx + 2,
                            severity="error",
                            field=field,
                            message="Valor negativo no permitido",
                            value=clean_value
                        )

        # 7) Validar coherencia total = cantidad * precio
        if {"cantidad", "precio", "total"}.issubset(available_columns):
            for idx, row in df.iterrows():
                cantidad = _to_float(_clean_value(row["cantidad"]))
                precio = _to_float(_clean_value(row["precio"]))
                total = _to_float(_clean_value(row["total"]))

                if cantidad is None or precio is None or total is None:
                    continue

                expected_total = round(cantidad * precio, 2)
                real_total = round(total, 2)

                if expected_total != real_total:
                    add_issue(
                        row_number=idx + 2,
                        severity="error",
                        field="total",
                        message="Total incoherente con cantidad × precio",
                        value=f"esperado={expected_total}, recibido={real_total}"
                    )

        error_count = sum(1 for issue in issues if issue["severity"] == "error")
        warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

        # Crear informe en texto
        report_lines = []
        report_lines.append("# Informe de análisis del dataset")
        report_lines.append("")
        report_lines.append(f"- Registros analizados: {len(df)}")
        report_lines.append(f"- Errores detectados: {error_count}")
        report_lines.append(f"- Avisos detectados: {warning_count}")
        report_lines.append("")

        if missing_columns:
            report_lines.append("## Problemas de estructura")
            for col in missing_columns:
                report_lines.append(f"- Falta la columna obligatoria: `{col}`")
            report_lines.append("")

        if issues:
            report_lines.append("## Detalle de incidencias")
            for issue in issues:
                report_lines.append(
                    f"- Fila {issue['row']} | {issue['severity'].upper()} | "
                    f"Campo: `{issue['field']}` | {issue['message']} | Valor: `{issue['value']}`"
                )
        else:
            report_lines.append("## Resultado")
            report_lines.append("- No se han detectado incidencias. El dataset parece correcto.")

        report_lines.append("")
        report_lines.append("## Recomendaciones")
        report_lines.append("- Revisar filas con errores antes de usar los datos.")
        report_lines.append("- Normalizar fechas al formato YYYY-MM-DD.")
        report_lines.append("- Validar emails y campos numéricos en origen.")
        report_lines.append("- Evitar IDs duplicados y totales incoherentes.")

        report_text = "\n".join(report_lines)

        return {
            "status": "ok",
            "summary": {
                "rows_analyzed": int(len(df)),
                "error_count": error_count,
                "warning_count": warning_count
            },
            "issues": issues,
            "report_text": report_text
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error al analizar el dataset: {e}"
        }


def save_report(report_text: str, output_path: str) -> dict:
    """
    Tool 3: guarda el informe en disco.
    """
    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(report_text, encoding="utf-8")

        return {
            "status": "ok",
            "message": f"Informe guardado correctamente en {path}",
            "output_path": str(path)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error al guardar el informe: {e}"
        }


if __name__ == "__main__":
    """
    Prueba local sin usar la API.
    Esto nos permite verificar que las tools funcionan antes de conectarlas al agente.
    """
    base_dir = Path(__file__).resolve().parent

    test_files = [
        base_dir / "data" / "ventas_ok.csv",
        base_dir / "data" / "ventas_error.csv"
    ]

    for file_path in test_files:
        print(f"\n--- Probando archivo: {file_path.name} ---")

        loaded = load_dataset(str(file_path))
        print("LOAD:", loaded["status"])

        if loaded["status"] != "ok":
            print(loaded["message"])
            continue

        analyzed = analyze_dataset(loaded["records"])
        print("ANALYZE:", analyzed["status"])

        if analyzed["status"] != "ok":
            print(analyzed["message"])
            continue

        output_name = f"informe_{file_path.stem}.md"
        output_path = base_dir / "outputs" / output_name

        saved = save_report(analyzed["report_text"], str(output_path))
        print("SAVE:", saved["status"])
        print(saved.get("message", ""))

        print("Resumen:", analyzed["summary"])