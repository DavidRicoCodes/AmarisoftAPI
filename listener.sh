#!/bin/bash

# Set base output directory
BASE_OUTPUT_DIR="/root/Desktop/OUTPUT"

# Create a timestamp string in the format YYYY-MM-DD-HH-MM
#TIMESTAMP=$(date "+%Y-%m-%d-%H-%M")

# Create the timestamped directory
# OUTPUT_DIR_LOG="$BASE_OUTPUT_DIR/$TIMESTAMP"

# Verifica si se ha pasado un JSON como argumento
if [ -z "$1" ]; then
    log "Error: Uso: $0 '<json_string>'"
    exit 1
fi

# Usa el primer argumento como el JSON
JSON_STRING="$1"

# Extract the id field from the JSON using jq
ID=$(echo "$JSON_STRING" | jq -r '.id')

OUTPUT_DIR_LOG="$BASE_OUTPUT_DIR/$ID"

mkdir -p "$OUTPUT_DIR_LOG"

# Define the log file path inside the timestamped folder
LOG_FILE="$OUTPUT_DIR_LOG/lteue_execution.log"

# Función para registrar mensajes
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Crea un archivo temporal para almacenar el JSON
#TEMP_JSON_FILE=$(mktemp)
# Escribe el JSON en el archivo temporal
#echo "$JSON_STRING" > "$TEMP_JSON_FILE"

# Save the JSON into request.json inside the output folder
REQUEST_JSON_FILE="$OUTPUT_DIR_LOG/request.json"
echo "$JSON_STRING" > "$REQUEST_JSON_FILE"


# Imprime el contenido del archivo temporal
log "Contenido del archivo temporal generado:"
cat "$REQUEST_JSON_FILE" | tee -a "$LOG_FILE"

# Llama al script de Python y registra su output
log "Ejecutando script de Python..."
python3 /root/Desktop/process_json_v2.py "$REQUEST_JSON_FILE" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    log "Error: la ejecución del script de Python falló."
    #rm -f "$TEMP_JSON_FILE" # Limpia el archivo temporal
    exit 1
fi

# Espera 2 segundos
sleep 2

# Obtiene la carpeta generada más reciente en el directorio de salida sin el trailing slash
OUTPUT_DIR="/root/lteue-linux-2024-06-14/config/erc/generated"
LATEST_DIR=$(ls -td "$OUTPUT_DIR"/* | head -1)

# Verifica si se encontró un directorio
if [ -z "$LATEST_DIR" ]; then
    log "Error: no se encontró el directorio generado."
    exit 1
fi

# Verificar si el JSON está bien formado
if ! echo "$JSON_STRING" | jq empty; then
    log "Error: El JSON proporcionado no es válido."
    exit 1
fi

# Verificar si el campo commands existe y tiene duraciones
if ! echo "$JSON_STRING" | jq '.commands[].duration' > /dev/null 2>&1; then
    log "Error: No se encontraron comandos o duraciones en el JSON."
    exit 1
fi

# Calcular la duración máxima (comandos tienen un array 'duration')
DURACION_MAXIMA=$(jq '[.commands[].duration] | max' "$REQUEST_JSON_FILE")

# Ejecutar el software de prueba en segundo plano y capturar stdout/stderr
log "Ejecutando software de prueba..."
/root/lteue-linux-2024-06-14/lteue "$LATEST_DIR/nr-erc.cfg" >> "$LOG_FILE" 2>&1 &
#( /root/lteue-linux-2024-06-14/lteue "$LATEST_DIR/nr-erc.cfg" 2>&1 | stdbuf -oL tee -a "$LOG_FILE" ) &
LTEUE_PID=$!
#/root/lteue-linux-2024-06-14/lteue "$LATEST_DIR/nr-erc.cfg" 2>&1 | stdbuf -oL tee -a "$LOG_FILE" &
#LTEUE_PID=$(pgrep -f "lteue $LATEST_DIR/nr-erc.cfg")


# Esperar duración + 10 segundos
log "Esperando $((DURACION_MAXIMA + 40)) segundos antes de finalizar el proceso."
sleep $((DURACION_MAXIMA + 40))

# Forzar cierre del proceso si sigue activo
if ps -p $LTEUE_PID > /dev/null; then
    log "El proceso sigue activo. Forzando cierre..."
    kill -SIGTERM $LTEUE_PID
    sleep 5
    # Si no se cierra, matar
    if ps -p $LTEUE_PID > /dev/null; then
        log "El proceso no respondió a SIGTERM. Enviando SIGKILL..."
        kill -SIGKILL $LTEUE_PID
    fi
fi

sleep 2
log "Extrayendo datos."
log "python3 data_extractor_v3.py $OUTPUT_DIR_LOG $REQUEST_JSON_FILE"
python3 /root/Desktop/data_extractor_v3.py $OUTPUT_DIR_LOG $REQUEST_JSON_FILE >> "$LOG_FILE" 2>&1 &
log "Extracción de datos finalizada."

# Limpia el archivo temporal ya que el script de Python lo procesó correctamente
sleep 2
#rm -f "$REQUEST_JSON_FILE"


# Muestra "done" cuando el script ha terminado completamente
log "El script ha terminado correctamente."
echo "done"
