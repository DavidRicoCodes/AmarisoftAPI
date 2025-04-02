#!/bin/bash

# Verifica si se ha pasado un JSON como argumento
if [ -z "$1" ]; then
    echo "Uso: $0 '<json_string>'"
    exit 1
fi

# Usa el primer argumento como el JSON
JSON_STRING="$1"

# Crea un archivo temporal para almacenar el JSON
TEMP_JSON_FILE=$(mktemp)

# Escribe el JSON en el archivo temporal
echo "$JSON_STRING" > "$TEMP_JSON_FILE"

# Imprime el contenido del archivo temporal
echo "Contenido del archivo temporal generado:"
cat "$TEMP_JSON_FILE"

# Llama al script de Python y espera a que termine
python3 /root/Desktop/process_json.py "$TEMP_JSON_FILE"
if [ $? -ne 0 ]; then
    echo "Error: la ejecución del script de Python falló."
    rm -f "$TEMP_JSON_FILE" # Limpia el archivo temporal
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

# Verificar si el JSON está bien formado
if ! echo "$JSON_STRING" | jq empty; then
    echo "Error: El JSON proporcionado no es válido."
    exit 1
fi

# Verificar si el campo commands existe y tiene duraciones
if ! echo "$JSON_STRING" | jq '.commands[].duration' > /dev/null 2>&1; then
    echo "Error: No se encontraron comandos o duraciones en el JSON."
    exit 1
fi

# Calcular la duración máxima (comandos tienen un array 'duration')
DURACION_MAXIMA=$(jq '[.commands[].duration] | max' "$TEMP_JSON_FILE")

# Ejecutar el software de prueba en segundo plano
/root/lteue-linux-2024-06-14/lteue "$LATEST_DIR/nr-erc.cfg" &
LTEUE_PID=$!

# Esperar duración + 10 segundos
echo "Timer set to for $((DURACION_MAXIMA + 20)) seconds"
sleep $((DURACION_MAXIMA + 20))

# Forzar cierre del proceso si sigue activo
if ps -p $LTEUE_PID > /dev/null; then
    echo "El proceso sigue activo. Forzando cierre..."
    kill -SIGTERM $LTEUE_PID
    sleep 5
    # Si no se cierra, matar
    if ps -p $LTEUE_PID > /dev/null; then
        echo "El proceso no respondió a SIGTERM. Enviando SIGKILL..."
        kill -SIGKILL $LTEUE_PID
    fi
fi

# Limpia el archivo temporal ya que el script de Python lo procesó correctamente
rm -f "$TEMP_JSON_FILE"
sleep 2

# Ejecuta el comando lterue con el archivo de configuración generado
#/root/lteue-linux-2024-06-14/lteue "$LATEST_DIR/nr-erc.cfg"

# Muestra "done" cuando el script ha terminado completamente
echo "done"
