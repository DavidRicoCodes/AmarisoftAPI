import re
import csv

# Expresión regular para capturar el valor de MCS (en una línea que contenga "mcs=NUM")
mcs_line_pattern = re.compile(r"^\s*mcs=(\d+)")

# Expresión regular para capturar la línea IP con timestamp
# Se asume que el timestamp aparece al inicio de la línea en formato HH:MM:SS.mmm
ip_line_pattern = re.compile(
    r"^(\d{2}:\d{2}:\d{2}\.\d{3}).*\[IP\].*? (\d+\.\d+\.\d+\.\d+):(\d+) > (\d+\.\d+\.\d+\.\d+):(\d+)"
)

# Expresión regular para identificar líneas de volcado hexadecimal (hex dump)
hex_line_pattern = re.compile(r"^\s*[0-9a-fA-F]{4}:")

def extract_iperf_header(hex_dump):
    """
    Dado un volcado hexadecimal (una cadena continua) de la totalidad del paquete IP,
    se omiten los primeros 28 bytes (20 de IP + 8 de UDP) y se extraen los siguientes 12 bytes,
    que corresponden al encabezado de iperf:
      - Primeros 4 bytes: número de secuencia.
      - Siguientes 8 bytes: timestamp.
    """
    # Cada byte se representa con 2 dígitos hexadecimales.
    offset = 28 * 2  # 56 caracteres
    header_length = 12 * 2  # 24 caracteres (12 bytes)
    if len(hex_dump) < offset + header_length:
        return None, None  # No hay suficientes datos
    udp_payload_hex = hex_dump[offset:offset+header_length]
    seq_hex = udp_payload_hex[:8]         # 4 bytes = 8 hex dígitos
    timestamp_hex = udp_payload_hex[8:24]   # 8 bytes = 16 hex dígitos
    try:
        seq_num = int(seq_hex, 16)
        timestamp_iperf = int(timestamp_hex, 16)
    except ValueError:
        seq_num = None
        timestamp_iperf = None
    return timestamp_iperf, seq_num

def parse_amarisoft_log(log_file, output_csv):
    last_mcs = None
    parsed_data = []
    
    # Leemos todas las líneas del archivo
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
        
        # Busca la línea IP que contiene la información básica (timestamp, IP, puertos)
        ip_match = ip_line_pattern.search(line)
        if ip_match:
            timestamp_log, src_ip, src_port, dst_ip, dst_port = ip_match.groups()
            # Acumula las líneas siguientes que correspondan al volcado hexadecimal
            hex_lines = []
            j = i + 1
            while j < len(lines) and hex_line_pattern.match(lines[j]):
                # Separa la parte hexadecimal descartando el offset
                hex_part = lines[j].split(":", 1)[1].strip()
                hex_lines.append(hex_part.replace(" ", ""))
                j += 1
            hex_dump = "".join(hex_lines)
            # Extrae los campos del encabezado de iperf
            timestamp_iperf, seq_num = extract_iperf_header(hex_dump)
            parsed_data.append([
                timestamp_log, src_ip, src_port, dst_ip, dst_port,
                last_mcs, timestamp_iperf, seq_num
            ])
            i = j
            continue
        
        i += 1

    # Guarda los datos extraídos en un archivo CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Timestamp_log", "Source IP", "Source Port",
            "Destination IP", "Destination Port", "MCS",
            "Timestamp_iperf", "Sequence_num_iperf"
        ])
        writer.writerows(parsed_data)

# Uso del script
log_filename = "OUTPUT/ue0.log"  # Cambia al nombre de tu archivo de log
output_filename = "parsed_data3.csv"  
parse_amarisoft_log(log_filename, output_filename)

print(f"Datos extraídos y guardados en {output_filename}")
