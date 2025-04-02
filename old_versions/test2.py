import re
import csv

# Expresión regular para capturar el valor de MCS (en una línea que contenga "mcs=NUM")
mcs_line_pattern = re.compile(r"^\s*mcs=(\d+)")

# Expresión regular para capturar los paquetes IP, incluyendo el timestamp.
# Se asume que el timestamp aparece al inicio de la línea en formato HH:MM:SS.mmm
ip_pattern = re.compile(
    r"^(\d{2}:\d{2}:\d{2}\.\d{3}).*\[IP\].*? (\d+\.\d+\.\d+\.\d+):(\d+) > (\d+\.\d+\.\d+\.\d+):(\d+)"
)

def parse_amarisoft_log(log_file, output_csv):
    last_mcs = None
    parsed_data = []
    
    with open(log_file, 'r', encoding='utf-8') as file:
        for line in file:
            # Actualiza el último valor de MCS si la línea contiene "mcs="
            mcs_match = mcs_line_pattern.search(line)
            if mcs_match:
                last_mcs = int(mcs_match.group(1))
                continue

            # Captura datos del paquete IP, incluyendo el timestamp
            ip_match = ip_pattern.search(line)
            if ip_match:
                timestamp, src_ip, src_port, dst_ip, dst_port = ip_match.groups()
                parsed_data.append([timestamp, src_ip, src_port, dst_ip, dst_port, last_mcs])
    
    # Guarda los datos extraídos en un archivo CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Timestamp", "Source IP", "Source Port", "Destination IP", "Destination Port", "MCS"])
        writer.writerows(parsed_data)

# Uso del script
log_filename = "OUTPUT/ue0.log"  # Cambia al nombre de tu archivo de log
output_filename = "parsed_data2.csv"  
parse_amarisoft_log(log_filename, output_filename)

print(f"Datos extraídos y guardados en {output_filename}")
