import re
import csv

# Patrón para capturar el valor de MCS (líneas que contengan "mcs=NUM")
mcs_line_pattern = re.compile(r"^\s*mcs=(\d+)", re.IGNORECASE)

# Patrón para capturar la línea IP con timestamp (formato HH:MM:SS.mmm)
ip_line_pattern = re.compile(
    r"^(\d{2}:\d{2}:\d{2}\.\d{3}).*\[IP\].*? (\d+\.\d+\.\d+\.\d+):(\d+) > (\d+\.\d+\.\d+\.\d+):(\d+)"
)

# Patrón para identificar líneas de volcado hexadecimal (líneas que empiezan con un offset, ej. "0000:")
hex_line_pattern = re.compile(r"^\s*[0-9a-fA-F]{4}:")

def extract_iperf_header(hex_dump):
    """
    Dado el volcado hexadecimal (una cadena continua) del paquete,
    determina el offset a usar. Si el volcado comienza con "45",
    se asume que incluye la cabecera IP (20 bytes) y UDP (8 bytes),
    por lo que se saltean 28 bytes (56 caracteres hexadecimales).
    Luego se extraen los siguientes 8 bytes, que corresponden al encabezado iperf:
      - Primeros 4 bytes: timestamp_iperf.
      - Siguientes 4 bytes: sequencenum_iperf.
    """
    if hex_dump.startswith("45"):
        offset = 28 * 2  # 56 caracteres
    else:
        offset = 0

    header_length = 8 * 2  # 16 caracteres (8 bytes)
    if len(hex_dump) < offset + header_length:
        return None, None

    header_hex = hex_dump[offset:offset+header_length]
    # Extraer los 4 primeros bytes para el timestamp
    timestamp_hex = header_hex[:8]
    # Extraer los 4 siguientes bytes para el número de secuencia
    seq_hex = header_hex[8:16]

    try:
        timestamp_iperf = int(timestamp_hex, 16)
        seq_num = int(seq_hex, 16)
    except ValueError:
        timestamp_iperf = None
        seq_num = None

    return timestamp_iperf, seq_num

def parse_amarisoft_log(log_file, output_csv):
    last_mcs = None
    parsed_data = []
    
    with open(log_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i]
        # Actualiza el último valor de MCS si la línea contiene "mcs="
        mcs_match = mcs_line_pattern.search(line)
        if mcs_match:
            last_mcs = int(mcs_match.group(1))
            i += 1
            continue
        
        # Busca la línea IP con información básica (timestamp, IP, puertos)
        ip_match = ip_line_pattern.search(line)
        if ip_match:
            timestamp_log, src_ip, src_port, dst_ip, dst_port = ip_match.groups()
            # Acumula las líneas siguientes correspondientes al volcado hexadecimal
            hex_lines = []
            j = i + 1
            while j < len(lines) and hex_line_pattern.match(lines[j]):
                hex_part = lines[j].split(":", 1)[1].strip()
                hex_lines.append(hex_part.replace(" ", ""))
                j += 1
            hex_dump = "".join(hex_lines)
            timestamp_iperf, seq_num = extract_iperf_header(hex_dump)
            parsed_data.append([
                timestamp_log, src_ip, src_port, dst_ip, dst_port,
                last_mcs, timestamp_iperf, seq_num
            ])
            i = j
            continue
        
        i += 1

    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Timestamp_log", "Source IP", "Source Port", "Destination IP",
            "Destination Port", "MCS", "Timestamp_iperf", "Sequence_num_iperf"
        ])
        writer.writerows(parsed_data)

# Uso del script
log_filename = "OUTPUT/ue0.log"  # Cambia al nombre de tu archivo de log
output_filename = "parsed_data4.csv"  
parse_amarisoft_log(log_filename, output_filename)

print(f"Datos extraídos y guardados en {output_filename}")
