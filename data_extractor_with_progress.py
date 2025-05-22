#!/usr/bin/env python3
import sys
import os
import json
import csv
import re
import string

# ----------------------------------------
# Streamlined Amarisoft log extractor with minimal RAM usage
# Usage: python3 data_extractor_fast.py <output_dir> <json_file>
# ----------------------------------------

if len(sys.argv) < 3:
    print("Usage: python3 data_extractor_fast.py <output_dir> <json_file>")
    sys.exit(1)

output_dir = sys.argv[1]
json_file_path = sys.argv[2]

# Load JSON to get ID
try:
    with open(json_file_path, 'r', encoding='utf-8') as jf:
        jdata = json.load(jf)
except Exception as e:
    print(f"Error reading JSON file: {e}")
    sys.exit(1)
id_value = jdata.get('id', 'id_missing')

# Prepare paths
os.makedirs(output_dir, exist_ok=True)
log_file = "/root/Desktop/OUTPUT/ue0.log" 
output_csv = os.path.join(output_dir, f"{id_value}.csv")

# Prep CSV writer in streaming mode
o_csv = open(output_csv, 'w', newline='', encoding='utf-8')
writer = csv.writer(o_csv)
writer.writerow([
    'Timestamp_log','Source_IP','Destination_IP',
    'IP_ID_hex','IP_ID_dec','IP_Checksum_hex','IP_Checksum_dec',
    'Source_Port','Destination_Port','UDP_Checksum_hex','UDP_Checksum_dec',
    'MCS','Timestamp_iperf','Timestamp_iperf_hex',
    'Sequence_num_iperf','Sequence_num_iperf_hex'
])

# Helper sets and regex
hexdigits = set(string.hexdigits)
hex_line_re = re.compile(r"^\s*([0-9A-Fa-f]{4}):\s*(.*)")

def is_hex_line(line):
    ls = line.lstrip()
    return len(ls) >= 5 and ls[4] == ':' and all(ch in hexdigits for ch in ls[:4])

def extract_ip_id(line):
    m = hex_line_re.match(line)
    if not m: return ('','')
    d = m.group(2).replace(' ', '')
    if len(d) < 12: return ('','')
    h = d[8:12]
    try: dec = int(h,16)
    except: dec = ''
    hexfmt = ' '.join(h[i:i+2] for i in range(0,4,2))
    return (hexfmt, dec)

def extract_ip_checksum(line):
    m = hex_line_re.match(line)
    if not m: return ('','')
    d = m.group(2).replace(' ', '')
    if len(d) < 24: return ('','')
    h = d[20:24]
    try: dec = int(h,16)
    except: dec = ''
    hexfmt = ' '.join(h[i:i+2] for i in range(0,4,2))
    return (hexfmt, dec)

def extract_udp_checksum(line):
    m = hex_line_re.match(line)
    if not m: return ('','')
    d = m.group(2).replace(' ', '')
    if len(d) < 24: return ('','')
    hdr = d[8:24]
    h = hdr[12:16]
    try: dec = int(h,16)
    except: dec = ''
    hexfmt = ' '.join(h[i:i+2] for i in range(0,4,2))
    return (hexfmt, dec)

def extract_iperf_header(hexs):
    for hl in hexs:
        m = hex_line_re.match(hl)
        if not m: continue
        off = int(m.group(1),16)
        if off >= 0x20:
            d = m.group(2).replace(' ', '')
            if len(d) >= 16:
                t_h, s_h = d[:8], d[8:16]
                try: t_d = int(t_h,16); s_d = int(s_h,16)
                except: t_d=s_d=None
                th = ' '.join(t_h[i:i+2] for i in range(0,8,2))
                sh = ' '.join(s_h[i:i+2] for i in range(0,8,2))
                return t_d, s_d, th, sh
    return (None,None,'','')

def extract_mcs(line):
    low = line.lower()
    if 'mcs=' in low:
        num='' 
        for ch in low.split('mcs=')[1]:
            if ch.isdigit(): num+=ch
            else: break
        return int(num) if num else None
    return None

def parse_ip_line(line):
    parts = line.split()
    if '[IP]' not in parts: return None
    try:
        tlog = parts[0]
        idx = parts.index('[IP]')
        src = parts[idx+1]; dst = parts[idx+3]
        sip,sp = src.rsplit(':',1)
        dip,dp = dst.rsplit(':',1)
        return tlog, sip, sp, dip, dp
    except:
        return None

# Stream parse log file
last_mcs = None
with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        # MCS
        m = extract_mcs(line)
        if m is not None:
            last_mcs = m; continue
        # IP packet
        if '[IP]' in line:
            info = parse_ip_line(line)
            if not info: continue
            tlog, sip, sp, dip, dp = info
            # collect hex dump
            hexs=[]
            for sub in f:
                if is_hex_line(sub): hexs.append(sub)
                else:
                    line = sub
                    break
            # extract fields
            ipid_h, ipid_d = extract_ip_id(hexs[0]) if hexs else ('','')
            ipcs_h, ipcs_d = extract_ip_checksum(hexs[0]) if hexs else ('','')
            udpcs_h, udpcs_d = extract_udp_checksum(hexs[1]) if len(hexs)>1 else ('','')
            t_i, s_i, th, sh = extract_iperf_header(hexs)
            writer.writerow([
                tlog, sip, dip,
                ipid_h, ipid_d, ipcs_h, ipcs_d,
                sp, dp, udpcs_h, udpcs_d,
                last_mcs, t_i, th, s_i, sh
            ])

# Close CSV
o_csv.close()
print(f"Data extracted and saved in {output_csv}")
