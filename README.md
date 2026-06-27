# Motor Industrial · Plataforma de Monitoreo de Riesgo

Dashboard interactivo para monitorear el estado operacional de un motor industrial en tiempo real. Analiza 4 variables de control — temperatura, vibración, voltaje y corriente — y clasifica cada lectura en uno de 4 niveles de riesgo.

## ¿Qué puedes hacer con esta app?

### 📊 Resumen general
Visualiza de un vistazo cuántos registros están en zona segura, cuántos requieren intervención y cuál es la temperatura promedio de operación.

### 🩺 Diagnóstico en vivo
Ingresa la lectura actual de los 4 sensores y obtén al instante:
- El nivel de riesgo de cada parámetro
- Un veredicto operacional global
- La acción recomendada (operar, vigilar, inspeccionar o detener)

### 📈 Análisis de datos
Explora cómo se comportan las variables según el nivel de riesgo mediante gráficos de distribución, promedios por nivel y correlaciones entre sensores.

### 🤖 Modelo de Machine Learning
Un modelo de Regresión Lineal entrenado con los datos reales del motor predice la vibración esperada a partir de la temperatura. Incluye:
- Ecuación del modelo con coeficientes reales
- Métricas de precisión (R², MAE, RMSE)
- Detección automática de sobreentrenamiento
- Predicción en vivo con el cálculo paso a paso

### 📋 Referencia operacional
Consulta la tabla de umbrales por parámetro, las alertas críticas y la regla de operación segura del equipo.

### 🔍 Análisis de registros
Filtra registros por condición operacional (temperatura fuera de rango, vibración elevada, etc.), revisa hallazgos automáticos e inspecciona cualquier registro individual con su diagnóstico completo.

## Niveles de riesgo

| Nivel | Descripción | Acción |
|---|---|---|
| 🟢 Normal | Todos los parámetros en zona segura | Sin acción requerida |
| 🟡 Riesgo bajo | Algún parámetro cerca del límite | Monitorear con mayor frecuencia |
| 🟠 Riesgo moderado | Parámetro fuera de rango | Programar mantenimiento |
| 🔴 Riesgo alto | Falla crítica o múltiples parámetros degradados | Detener el equipo de inmediato |

## Rangos de operación segura

| Parámetro | Zona segura |
|---|---|
| 🌡️ Temperatura | 30 – 60 °C |
| 📳 Vibración | 0 – 5 mm/s |
| ⚡ Voltaje | 380 – 420 V |
| 🔌 Corriente | 10 – 20 A |

> Si dos o más parámetros están en riesgo moderado o alto al mismo tiempo, el sistema recomienda detener el equipo aunque cada parámetro individualmente no sea crítico.
