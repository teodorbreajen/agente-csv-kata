# Informe de análisis del dataset

- Registros analizados: 5
- Errores detectados: 11
- Avisos detectados: 0

## Detalle de incidencias
- Fila 4 | ERROR | Campo: `fecha` | Campo obligatorio vacío | Valor: ``
- Fila 6 | ERROR | Campo: `email` | Campo obligatorio vacío | Valor: ``
- Fila 4 | ERROR | Campo: `id_venta` | ID de venta duplicado | Valor: `3`
- Fila 5 | ERROR | Campo: `id_venta` | ID de venta duplicado | Valor: `3`
- Fila 3 | ERROR | Campo: `fecha` | Fecha inválida. Se espera formato YYYY-MM-DD | Valor: `03/02/2026`
- Fila 6 | ERROR | Campo: `fecha` | Fecha inválida. Se espera formato YYYY-MM-DD | Valor: `2026-15-05`
- Fila 3 | ERROR | Campo: `email` | Email inválido | Valor: `luis@email`
- Fila 5 | ERROR | Campo: `cantidad` | Valor negativo no permitido | Valor: `-1`
- Fila 6 | ERROR | Campo: `precio` | Valor numérico inválido | Valor: `abc`
- Fila 5 | ERROR | Campo: `total` | Valor negativo no permitido | Valor: `-110`
- Fila 3 | ERROR | Campo: `total` | Total incoherente con cantidad × precio | Valor: `esperado=180.0, recibido=999.0`

## Recomendaciones
- Revisar filas con errores antes de usar los datos.
- Normalizar fechas al formato YYYY-MM-DD.
- Validar emails y campos numéricos en origen.
- Evitar IDs duplicados y totales incoherentes.