#!/usr/bin/env python3

import os
import json
import warnings

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 0) Suprimir warnings innecesarios
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# 1) Directorios base
base_dir = '/root/Desktop/OUTPUT/MBps'
save_dir = '/root/Desktop/validation_tests/MBps_MB_exp'

# 2) Iterar sobre cada experimento (subcarpeta)
for exp in os.listdir(base_dir):
    exp_path  = os.path.join(base_dir, exp)
    save_path = os.path.join(save_dir, exp)

    # Asegurar que exista carpeta de salida
    os.makedirs(save_path, exist_ok=True)

    # Saltar si no es carpeta
    if not os.path.isdir(exp_path):
        continue

    # Archivos de entrada
    csv_file  = os.path.join(exp_path, f"{exp}.csv")
    json_file = os.path.join(exp_path, 'request.json')

    if not os.path.isfile(csv_file):
        print(f"CSV para el experimento '{exp}' no encontrado, omitiendo.")
        continue

    # 3) Leer JSON de request para extraer BW solicitada (convertida a MBps)
    requested_bw = {}
    if os.path.isfile(json_file):
        with open(json_file) as f:
            req = json.load(f)
        for cmd in req.get('commands', []):
            cmd_str = cmd.get('command', '')
            parts = cmd_str.split()
            if '-b' in parts and '-p' in parts:
                bw_str = parts[parts.index('-b') + 1]
                port_val = int(parts[parts.index('-p') + 1])
                # Interpretar megabits (iperf usa bits)
                if bw_str.lower().endswith('m'):
                    mbits = float(bw_str[:-1])
                elif bw_str.lower().endswith('k'):
                    mbits = float(bw_str[:-1]) / 1024
                else:
                    mbits = float(bw_str)
                # Convertir a MBps: (Mbit/s) / 8
                requested_bw[port_val] = mbits / 8.0

    # 4) Leer CSV y parsear timestamp
    df = pd.read_csv(csv_file)
    df['timestamp'] = pd.to_datetime(df['Timestamp_log'], format='%H:%M:%S.%f')
    df = df.set_index('timestamp')

    # 5) Parámetro tamaño paquete
    packet_size_bytes = 1470

    # 6) Tiempo inicio/fin experimento
    t_min = df.index.min()
    t_max = df.index.max()

    # 7) Bins de 1 segundo (minúscula 's')
    bin_start = t_min.floor('s')
    bin_end   = t_max.ceil('s')
    bins      = pd.date_range(bin_start, bin_end, freq='s')

    # 8) Filtrar puertos de usuario 52XX
    user_ports = sorted(
        int(port) for port in df['Destination Port'].unique()
        if isinstance(port, (int, np.integer)) and 5200 <= int(port) <= 5299
    )
    throughputs = {}

    # 9) Calcular throughput por puerto en MBps
    for port in user_ports:
        df_port = df[df['Destination Port'] == port]
        counts  = pd.cut(df_port.index, bins=bins, right=False).value_counts().sort_index()
        bin_starts = bins[:-1]

        occupancy = [(min(bs + pd.Timedelta(seconds=1), t_max) - max(bs, t_min)).total_seconds()
                     for bs in bin_starts]
        occupancy = np.array(occupancy)

        bits = counts.values * packet_size_bytes * 8
        with np.errstate(divide='ignore', invalid='ignore'):
            bps = bits / occupancy
        # Convertir bits/s a MBps: bits/s /8 /1e6
        series_mb = pd.Series(bps / 8.0 / 1e6, index=bin_starts)
        # Recortar ceros iniciales
        nonzero = series_mb[series_mb > 0]
        if not nonzero.empty:
            series_mb = series_mb.loc[nonzero.index[0]:]
        throughputs[port] = series_mb

    # 10) Generar y guardar gráficas
    if throughputs:
        # Gráfica completa
        plt.figure(figsize=(12, 6))
        for port, series in throughputs.items():
            plt.plot(series.index, series.values,
                     marker='o', label=f'Puerto {port}')
        plt.xlabel('Tiempo')
        plt.ylabel('Throughput (MBps)')
        plt.title(f'Throughput por segundo – Experimento {exp}')
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(save_path, f'{exp}_throughput.png'))
        plt.close()

        # Gráfica con zoom
        all_mb = np.hstack([s.values for s in throughputs.values()])
        all_mb = all_mb[~np.isnan(all_mb)]
        if all_mb.size:
            p_low, p_high = np.percentile(all_mb, [5, 95])
            margin = (p_high - p_low) * 0.1
            low_lim  = p_low - margin
            high_lim = p_high + margin

            plt.figure(figsize=(12, 6))
            for port, series in throughputs.items():
                plt.plot(series.index, series.values,
                         marker='o', label=f'Puerto {port}')
            plt.xlabel('Tiempo')
            plt.ylabel('Throughput (MBps)')
            plt.title(f'Throughput con zoom – Experimento {exp}')
            if low_lim < high_lim:
                plt.ylim(low_lim, high_lim)
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(save_path, f'{exp}_throughput_zoom.png'))
            plt.close()

        # 11) Resumen de throughput y solicitado
        num_users   = len(user_ports)
        means       = {port: series.mean() for port, series in throughputs.items()}
        total_mean  = sum(means.values())
        total_req   = sum(requested_bw.get(p, 0) for p in user_ports)

        print(f"Experimento '{exp}': gráficas guardadas para puertos {user_ports}.")
        print(f"Number of users: {num_users}")
        for port, m in means.items():
            req = requested_bw.get(port)
            req_str = f"Requested: {req:.2f} MBps" if req is not None else ""
            print(f"Mean thr user {port}: {m:.2f} MBps  {req_str}")
        print(f"Total thr all users Mean: {total_mean:.2f} MBps    Requested: {total_req:.2f} MBps")
    else:
        print(f"Experimento '{exp}': no se encontraron puertos 52XX.")
