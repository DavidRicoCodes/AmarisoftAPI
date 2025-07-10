#!/usr/bin/env python3

import os
import warnings

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 0) Suprimir warnings innecesarios
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# 1) Directorios base
base_dir = '/root/Desktop/OUTPUT/MBps'
save_dir = '/root/Desktop/validation_tests/MBps'

# 2) Iterar sobre cada experimento (subcarpeta)
for exp in os.listdir(base_dir):
    exp_path  = os.path.join(base_dir, exp)
    save_path = os.path.join(save_dir, exp)

    # Asegurar que exista carpeta de salida
    os.makedirs(save_path, exist_ok=True)

    # Saltar si no es carpeta
    if not os.path.isdir(exp_path):
        continue

    csv_file = os.path.join(exp_path, f"{exp}.csv")
    if not os.path.isfile(csv_file):
        print(f"CSV para el experimento '{exp}' no encontrado, omitiendo.")
        continue

    # 3) Leer CSV y parsear timestamp
    df = pd.read_csv(csv_file)
    df['timestamp'] = pd.to_datetime(df['Timestamp_log'], format='%H:%M:%S.%f')
    df = df.set_index('timestamp')

    # 4) Parámetro tamaño paquete
    packet_size_bytes = 1470

    # 5) Tiempo inicio/fin experimento
    t_min = df.index.min()
    t_max = df.index.max()

    # 6) Bins de 1 segundo (min 's')
    bin_start = t_min.floor('s')
    bin_end   = t_max.ceil('s')
    bins      = pd.date_range(bin_start, bin_end, freq='s')

    # 7) Filtrar puertos de usuario 52XX
    user_ports = sorted(
        int(port) for port in df['Destination Port'].unique()
        if isinstance(port, (int, np.integer)) and 5200 <= int(port) <= 5299
    )
    throughputs = {}

    # 8) Calcular throughput por puerto
    for port in user_ports:
        df_port = df[df['Destination Port'] == port]
        counts  = pd.cut(df_port.index, bins=bins, right=False).value_counts().sort_index()
        bin_starts = bins[:-1]

        occupancy = []
        for bs in bin_starts:
            be = bs + pd.Timedelta(seconds=1)
            occ_start = max(bs, t_min)
            occ_end   = min(be, t_max)
            occupancy.append((occ_end - occ_start).total_seconds())
        occupancy = np.array(occupancy)

        bits = counts.values * packet_size_bytes * 8
        with np.errstate(divide='ignore', invalid='ignore'):
            bps = bits / occupancy
        # Generar serie de throughput en Mbps
        series_mbps = pd.Series(bps / 1e6, index=bin_starts)
        # Recortar ceros iniciales (antes de la primera transmisión)
        nonzero = series_mbps[series_mbps > 0]
        if not nonzero.empty:
            series_mbps = series_mbps.loc[nonzero.index[0]:]
        throughputs[port] = series_mbps

    # 9) Generar y guardar gráficas
    if throughputs:
        # Gráfica completa
        plt.figure(figsize=(12, 6))
        for port, series in throughputs.items():
            plt.plot(series.index, series.values, marker='o', label=f'Puerto {port}')
        plt.xlabel('Tiempo')
        plt.ylabel('Throughput (Mbps)')
        plt.title(f'Throughput por segundo – Experimento {exp}')
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(save_path, f'{exp}_throughput.png'))
        plt.close()

        # Gráfica con zoom
        all_mbps = np.hstack([s.values for s in throughputs.values()])
        all_mbps = all_mbps[~np.isnan(all_mbps)]
        if all_mbps.size:
            p_low, p_high = np.percentile(all_mbps, [5, 95])
            y_margin     = (p_high - p_low) * 0.1
            low_lim      = p_low - y_margin
            high_lim     = p_high + y_margin

            plt.figure(figsize=(12, 6))
            for port, series in throughputs.items():
                plt.plot(series.index, series.values, marker='o', label=f'Puerto {port}')
            plt.xlabel('Tiempo')
            plt.ylabel('Throughput (Mbps)')
            plt.title(f'Throughput con zoom – Experimento {exp}')
            if low_lim < high_lim:
                plt.ylim(low_lim, high_lim)
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(save_path, f'{exp}_throughput_zoom.png'))
            plt.close()

        # 10) Resumen de throughput
        num_users = len(user_ports)
        means = {port: series.mean() for port, series in throughputs.items()}
        total_mean = sum(means.values())

        print(f"Experimento '{exp}': gráficas guardadas para puertos {user_ports}.")
        print(f"Number of users: {num_users}")
        for port, m in means.items():
            print(f"Mean thr user {port}: {m:.2f} Mbps")
        print(f"Total thr all users Mean: {total_mean:.2f} Mbps")
    else:
        print(f"Experimento '{exp}': no se encontraron puertos 52XX.")

