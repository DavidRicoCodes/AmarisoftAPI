#!/bin/bash

# --------------------------------------------------
# Configuración inicial
# --------------------------------------------------
BASE_OUTPUT_DIR="/root/Desktop/OUTPUT"

if [ -z "$1" ]; then
    echo "Error: Uso: $0 '<json_string>'"
    exit 1
fi

# JSON y directorios de salida
JSON_STRING="$1"
ID=$(echo "$JSON_STRING" | jq -r '.id')
OUTPUT_DIR_LOG="$BASE_OUTPUT_DIR/$ID"
mkdir -p "$OUTPUT_DIR_LOG"

LOG_FILE="$OUTPUT_DIR_LOG/lteue_execution.log"
EXPECT_LOG="$OUTPUT_DIR_LOG/expect_trace.log"

# Función de logging (con tee al log principal)
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# --------------------------------------------------
# Guardar y mostrar JSON de petición
# --------------------------------------------------
REQUEST_JSON_FILE="$OUTPUT_DIR_LOG/request.json"
echo "$JSON_STRING" > "$REQUEST_JSON_FILE"
log "JSON de petición guardado en $REQUEST_JSON_FILE"
log "Contenido de JSON:"
cat "$REQUEST_JSON_FILE" | tee -a "$LOG_FILE"

# --------------------------------------------------
# Procesar JSON con Python
# --------------------------------------------------
log "Ejecutando process_json_v2.py..."
python3 /root/Desktop/process_json_v2.py "$REQUEST_JSON_FILE" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    log "Error: process_json_v2.py falló."
    exit 1
fi

# --------------------------------------------------
# Localizar la carpeta generada
# --------------------------------------------------
sleep 2
OUTPUT_DIR="/root/lteue-linux-2024-06-14/config/erc/generated"
LATEST_DIR=$(ls -td "$OUTPUT_DIR"/* | head -1)
if [ -z "$LATEST_DIR" ]; then
    log "Error: no se encontró directorio generado."
    exit 1
fi
log "Directorio generado: $LATEST_DIR"

# --------------------------------------------------
# Validar JSON y extraer duración máxima
# --------------------------------------------------
if ! echo "$JSON_STRING" | jq empty; then
    log "Error: JSON inválido."
    exit 1
fi

if ! echo "$JSON_STRING" | jq '.commands[].duration' > /dev/null 2>&1; then
    log "Error: No se encontraron comandos con duration."
    exit 1
fi

DURACION_MAXIMA=$(jq '[.commands[].duration] | max' "$REQUEST_JSON_FILE")
log "Duración máxima de comandos: $DURACION_MAXIMA s"

# --------------------------------------------------
# Ejecutar lteue con expect + kill automático
# --------------------------------------------------
EXPECT_SCRIPT="/root/Desktop/amari_trace_no_fork.exp"

log "Iniciando lteue con trace y kill tras $((DURACION_MAXIMA+40)) s..."
expect "$EXPECT_SCRIPT" \
    "$LATEST_DIR/nr-erc.cfg" \
    "$EXPECT_LOG" \
    "$DURACION_MAXIMA" \
    "40"

log "Trace completo y kill registrado en $EXPECT_LOG"

JSON_LOG="$OUTPUT_DIR_LOG/json.log"
TRACE_LOG="$OUTPUT_DIR_LOG/traces.log"

log "Copiando source Amari log"
DEST_DIR="/mnt/qnap/AmariDT/OUTPUT/$ID"
mkdir -p $DEST_DIR
rsync -ah --progress $BASE_OUTPUT_DIR/ue0.log $DEST_DIR/ue0.log  >> "$LOG_FILE" 2>&1
log "Copia finalizada."

log "Ejecutando parser.py..."
python3 /root/Desktop/parserv2.py $EXPECT_LOG $TRACE_LOG $JSON_LOG >> "$LOG_FILE" 2>&1
log "Parseo finalizado."

log "Limpiando logs de json"
python3 /root/Desktop/dedupe.py $JSON_LOG >> "$LOG_FILE" 2>&1
log "Limpieza finalizado."

# --------------------------------------------------
# Extracción de datos
# --------------------------------------------------
log "Ejecutando data_extractor_v3.py..."
python3 /root/Desktop/data_extractor_v3.py "$OUTPUT_DIR_LOG" "$REQUEST_JSON_FILE" >> "$LOG_FILE" 2>&1
log "Extracción de datos finalizada."

log "Copiando output del experimento"
rsync -ah --progress $OUTPUT_DIR_LOG/* $DEST_DIR >> "$LOG_FILE" 2>&1
log "Copia finalizada."

# --------------------------------------------------
# Fin de script
# --------------------------------------------------
log "Script finalizado correctamente."
echo "done"
