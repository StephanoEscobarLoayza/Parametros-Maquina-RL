# Industrial Motor · Plataforma de Monitoreo de Riesgo

Dashboard interactivo construido con **Streamlit** para monitorear el riesgo operacional de un motor industrial a partir de 4 variables de control: temperatura, vibración, voltaje y corriente. Los datos se leen desde una tabla en **Supabase** (con respaldo a un CSV local), y la aplicación clasifica cada lectura en uno de 4 niveles de riesgo: normal, bajo, moderado y alto.

La base de análisis son 8.000 registros balanceados (2.000 por nivel de riesgo).

## Características

- **Resumen general** — indicadores clave, rango de operación segura y distribución de la flota por nivel de riesgo.
- **Diagnóstico en vivo** — ingresa una lectura de los 4 sensores y el sistema clasifica cada parámetro, emite un veredicto operacional y recomienda una acción.
- **Análisis de datos** — distribución de cada variable por nivel (box plots), promedios y correlaciones entre variables.
- **Referencia operacional** — tabla de umbrales, alertas críticas y la regla de operación segura.
- **Análisis de registros** — búsqueda por condición operacional, hallazgos automáticos e inspector individual de registros con diagnóstico.
- **Modelo de ML** — un clasificador Random Forest que aprende a predecir el nivel de riesgo a partir de los datos, con su precisión, matriz de confusión, importancia de cada variable y predicción en vivo comparada con el diagnóstico por reglas.

## Requisitos

- Python 3.9 o superior
- Una tabla en Supabase con las columnas de voltaje, corriente, temperatura, vibración y etiqueta de nivel (la app detecta automáticamente variaciones en los nombres). Opcional: si no configuras Supabase, la app usa un CSV local de respaldo.

## Instalación

```bash
pip install -r requirements.txt
```

## Configuración

Crea el archivo `.streamlit/secrets.toml` junto a `main.py` con tus credenciales de Supabase:

```toml
SUPABASE_URL   = "https://TU-PROYECTO.supabase.co"
SUPABASE_KEY   = "TU_ANON_KEY"
SUPABASE_TABLE = "motor_sensor_data"
```

Si no configuras Supabase, coloca el archivo `industrial_motor_sensor_data_8000csv.csv` junto a `main.py` y la aplicación lo usará como respaldo automáticamente.

## Ejecución

```bash
streamlit run main.py
```

La aplicación se abrirá en el navegador (por defecto en `http://localhost:8501`).

## Estructura del proyecto

```
.
├── main.py                  # Aplicación principal
├── requirements.txt         # Dependencias
├── README.md                # Este archivo
└── .streamlit/
    ├── config.toml          # Tema oscuro de la aplicación
    └── secrets.toml          # Credenciales de Supabase (NO subir a repositorios)
```

## Reglas de clasificación

Cada parámetro se clasifica según rangos operacionales (temperatura, vibración, voltaje y corriente). El veredicto global aplica la política de operación: si dos o más parámetros caen en riesgo moderado o alto de forma simultánea, el sistema recomienda **detener el equipo** para inspección, aunque la etiqueta original del registro sea menor. Esto refleja la regla de que múltiples parámetros degradados a la vez representan un riesgo mayor que cada uno por separado.

## Notas

- El archivo `.streamlit/secrets.toml` contiene credenciales y **no debe subirse** a repositorios públicos. Agrégalo a tu `.gitignore`.
- Para desplegar en Streamlit Community Cloud, configura las credenciales en la sección de *Secrets* de la plataforma en lugar de incluirlas en el código.
- El reloj del panel de estado muestra la hora de la última carga de la página; se actualiza al navegar o interactuar, no segundo a segundo.
- El modelo de Machine Learning alcanza una precisión cercana al 100% porque el conjunto de datos fue generado con reglas limpias por nivel, lo que hace las clases perfectamente separables. Con datos del mundo real (con ruido) la precisión típica estaría entre 85% y 95%.
