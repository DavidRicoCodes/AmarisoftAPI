#!/bin/bash

# Verifica si se ha pasado un archivo como argumento
if [ -z "$1" ]; then
    echo "Uso: $0 <archivo_json>"
    exit 1
fi

# Usa el primer argumento como archivo JSON
JSON_FILE="$1"

# Comprueba que el archivo existe
if [ ! -f "$JSON_FILE" ]; then
    echo "Error: el archivo $JSON_FILE no existe."
    exit 1
fi

# Llama al script de Python y espera a que termine
python3 process_json.py "$JSON_FILE"
if [ $? -ne 0 ]; then
    echo "Error: la ejecución del script de Python falló."
    exit 1
fi

# Espera 2 segundos
sleep 2

# Obtiene la carpeta generada más reciente en el directorio de salida sin el trailing slash
OUTPUT_DIR="/root/lteue-linux-2024-06-14/config/erc/generated"
LATEST_DIR=$(ls -td "$OUTPUT_DIR"/* | head -1)

# Verifica si se encontró un directorio
if [ -z "$LATEST_DIR" ]; then
    echo "Error: no se encontró el directorio generado."
    exit 1
fi

# Ejecuta el comando lterue con el archivo de configuración generado
/root/lteue-linux-2024-06-14/lteue "$LATEST_DIR/nr-erc.cfg"

# Muestra "done" cuando el script ha terminado completamente
echo "done"
