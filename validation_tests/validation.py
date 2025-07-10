#!/usr/bin/env python3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1) Leer CSV y parsear la columna Time
df = pd.read_csv('/root/Desktop/validation_tests/Timeclean.csv')
df['timestamp'] = pd.to_datetime(df['Time'], format='%H:%M:%S.%f')
df = df.set_index('timestamp')

# 2) Parámetros
packet_size_bytes = 1470

# 3) Tiempo de inicio y fin del experimento
t_min = df.index.min()
t_max = df.index.max()

# 4) Crear bordes de ventana de 1 segundo alineados a segundos de reloj
bin_start = t_min.floor('S')
bin_end   = t_max.ceil('S')
bins = pd.date_range(bin_start, bin_end, freq='S')

# 5) Para cada puerto, contar paquetes y calcular throughput
throughputs = {}
for port in sorted(df['D-Port'].unique()):
    df_port = df[df['D-Port'] == port]
    counts = pd.cut(df_port.index, bins=bins, right=False).value_counts().sort_index()
    bin_starts = bins[:-1]

    # c) Calcular duración real de cada intervalo (primer/último segundo parciales)
    occupancy = []
    for bs in bin_starts:
        be = bs + pd.Timedelta(seconds=1)
        occ_start = max(bs, t_min)
        occ_end   = min(be, t_max)
        occupancy.append((occ_end - occ_start).total_seconds())
    occupancy = np.array(occupancy)

    # d) Throughput en bps y conversión a Mbps
    bits = counts.values * packet_size_bytes * 8
    with np.errstate(divide='ignore', invalid='ignore'):
        bps = bits / occupancy
    throughputs[port] = pd.Series(bps / 1e6, index=bin_starts)

# 6) Dibujar y guardar la gráfica completa
plt.figure(figsize=(12, 6))
for port, series in throughputs.items():
    plt.plot(series.index, series.values, marker='o', label=f'Puerto {port}')
plt.xlabel('Tiempo')
plt.ylabel('Throughput (Mbps)')
plt.title('Throughput por segundo por flujo (puertos 5201–5204)')
plt.legend()
plt.tight_layout()
plt.savefig('validation_tests/throughput.png')

# 7) Dibujar y guardar la gráfica con zoom en la zona de interés
all_mbps = np.hstack([s.values for s in throughputs.values()])
all_mbps = all_mbps[~np.isnan(all_mbps)]
# Calcular percentiles para centrar zoom (5%–95%)
p_low, p_high = np.percentile(all_mbps, [5, 95])
# Añadir un margen del 10%
y_margin = (p_high - p_low) * 0.1

plt.figure(figsize=(12, 6))
for port, series in throughputs.items():
    plt.plot(series.index, series.values, marker='o', label=f'Puerto {port}')
plt.xlabel('Tiempo')
plt.ylabel('Throughput (Mbps)')
plt.title('Throughput con zoom (%5–%95 percentiles)')
plt.ylim(p_low - y_margin, p_high + y_margin)
plt.legend()
plt.tight_layout()
plt.savefig('validation_tests/throughput_zoom.png')

print("Gráficas guardadas en 'throughput.png' y 'throughput_zoom.png'")

