#!/usr/bin/env python3
import sys
import json
import os
from datetime import datetime
import random

# -------------- Cell Database Setup --------------
cell_database_path = "cell_database.json"

# Ensure a JSON file is passed as an argument
if len(sys.argv) < 2:
    print("Usage: python process_json.py <json_file>")
    sys.exit(1)

# Get the JSON file from the arguments
json_file = sys.argv[1]

# Load or create cell database
if os.path.exists(cell_database_path):
    with open(cell_database_path, "r") as db_file:
        cell_database = json.load(db_file)
else:
    cell_database = {}


# -------------- Load JSON Data --------------
try:
    with open(json_file, 'r') as file:
        data = json.load(file)
except Exception as e:
    print(f"Error loading JSON file: {e}")
    sys.exit(1)


# -------------- Create Timestamped Output Directory --------------
base_output_dir = "/root/lteue-linux-2024-06-14/config/erc/generated/"
timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
id_name= data.get("id", "missing")
output_dir = os.path.join(base_output_dir, id_name)
os.makedirs(output_dir, exist_ok=True)



flag_cell_name = 1
flag_cell_data = 1

try:
    cell_name = data["radio_config"]["cell_name"]
except KeyError:
    print("No cell name detected")
    flag_cell_name = 0

try:
    bandwidth = data["radio_config"]["bandwidth"]
except KeyError:
    print("No bandwidth specified")
    sys.exit(1)
    
try:
    band = data["radio_config"]["band"].replace("B", "")  # Remove "B"
    arfcn = data["radio_config"]["arfcn"]
    ssb_nr_arfcn = data["radio_config"]["ssb_nr_arfcn"]
    subcarrier_spacing = data["radio_config"]["subcarrier_spacing"]
except KeyError as e:
    print(f"No cell data detected - {e}")
    flag_cell_data = 0

if flag_cell_name == 1 and flag_cell_data == 1:
    flag_db = 1
else:
    flag_db = 0

if flag_db == 1:
    if cell_name not in cell_database:
        cell_database[cell_name] = {
            "bandwidth_info": {
                str(bandwidth): {
                    "band": band,
                    "arfcn": arfcn,
                    "ssb_nr_arfcn": ssb_nr_arfcn,
                    "subcarrier_spacing": subcarrier_spacing
                }
            }
        }
        print(f"Added new cell '{cell_name}' with bandwidth {bandwidth} to database.")
    else:
        if "bandwidth_info" not in cell_database[cell_name]:
            cell_database[cell_name]["bandwidth_info"] = {}
        if str(bandwidth) not in cell_database[cell_name]["bandwidth_info"]:
            cell_database[cell_name]["bandwidth_info"][str(bandwidth)] = {
                "band": band,
                "arfcn": arfcn,
                "ssb_nr_arfcn": ssb_nr_arfcn,
                "subcarrier_spacing": subcarrier_spacing
            }
            print(f"Updated '{cell_name}' with new bandwidth {bandwidth}.")
        else:
            print(f"'{cell_name}' already has data for bandwidth {bandwidth}.")

with open(cell_database_path, "w") as db_file:
    json.dump(cell_database, db_file, indent=4)

if flag_cell_name == 1 and flag_cell_data == 0:
    print(f"Retrieving configuration for cell '{cell_name}' and bandwidth '{bandwidth}' from database")
    try:
        cell_data = cell_database[cell_name]["bandwidth_info"][str(bandwidth)]
        band = cell_data["band"]
        arfcn = cell_data["arfcn"]
        ssb_nr_arfcn = cell_data["ssb_nr_arfcn"]
        subcarrier_spacing = cell_data["subcarrier_spacing"]
    except KeyError as e:
        print(f"No data in database for cell '{cell_name}' and bandwidth '{bandwidth}' - {e}")
        sys.exit(1)

if flag_cell_name == 0 and flag_cell_data == 0:
    print("No cell data or cell name specified")
    sys.exit(1)

# -------------- Extract Additional Fields from JSON --------------
try:
    tx_gain = data["radio_config"]["tx_gain"]
    rx_gain = data["radio_config"]["rx_gain"]
    plmn = data["radio_config"]["plmn"]
    commands = data["commands"]
    if data.get("channel_sim", False)== True:
        chan = 1
    else:
        chan = 0
except KeyError as e:
    print(f"Error: Missing field in JSON - {e}")
    sys.exit(1)

# -------------- Generate nr-erc.cfg --------------
cfg_content = f"""{{
#define N_ANTENNA_DL 2
#define TDD 1
#define CELL_BANDWIDTH {bandwidth}
#define CHANNEL_SIM {chan}

  log_options: "all.level=debug,all.max_size=1,ip.max_size=500,ip.payload=true",
  log_filename: "/root/Desktop/OUTPUT/ue0.log",
  com_addr: "[::]:9002",

  rf_driver: {{
    name: "sdr",
    args: "dev0=/dev/sdr0",
  }},
  tx_gain: {tx_gain},
  rx_gain: {rx_gain},

  cell_groups: [{{
    group_type: "nr",
    multi_ue: true,
#if CHANNEL_SIM == 1
    channel_sim: true, 
#endif
    cells: [{{
      rf_port: 0,
      bandwidth: CELL_BANDWIDTH,
      band: {band},
      dl_nr_arfcn: {arfcn},
      ssb_nr_arfcn: {ssb_nr_arfcn},
      subcarrier_spacing: {subcarrier_spacing},
      n_antenna_dl: N_ANTENNA_DL,
      n_antenna_ul: 1,
      rx_to_tx_latency: 2,
#if CHANNEL_SIM == 1
    position: [0, 0],
    antenna: {{
      type: "isotropic",
    }},
    ref_signal_power: -40, 
    ul_power_attenuation: 30, 
#endif
    }}],
    pdcch_decode_opt: false,
    pdcch_decode_opt_threshold: 0.1
  }}],

  include "users-scenario.cfg"
}}
"""

output_file_1 = os.path.join(output_dir, "nr-erc.cfg")
try:
    with open(output_file_1, 'w') as cfg_file:
        cfg_file.write(cfg_content)
    print(f"File '{output_file_1}' generated successfully.")
except Exception as e:
    print(f"Error writing file '{output_file_1}': {e}")
    sys.exit(1)

# -------------- Generate users-scenario.cfg --------------
ue_list = []
for idx, command_entry in enumerate(commands, start=1):
    ue_id = idx
    imsi = 214050000002000 + ue_id
    ue_entry = {
        "ue_id": ue_id,
        "imsi": str(imsi),
        "imeisv": "1553750000000101",
        "sim_algo": "milenage",
        "channel_sim": data.get("channel_sim", False),
        "op": "0123456789ABCDEF0123456789ABCDEF",
        "K": "0123456789ABCDEF0123456789ABCDEF",
        "apn": "internet",
        "spec_tolerance": False,
        "as_release": 15,
        "ldpc_max_its": 6,
        "ue_category": "nr",
        "cell_index": 0,
        "rrc_initial_selection": False,
        "tun_setup_script": "ue-ifup",
        "preferred_plmn_list": [str(plmn)]
    }

    # If channel simulation is enabled, add additional channel parameters
    if data.get("channel_sim", False):
        cp = data.get("channel_params", {})
        ue_entry["max_distance"] = cp.get("max_distance", 0)    # Example scaling
        ue_entry["min_distance"] = cp.get("min_distance", 0)      # Example scaling
        ue_entry["noise_spd"] = cp.get("noise_spd", 0)
        ue_entry["speed"] = cp.get("speed", 0)                # Example scaling
        channel_obj = cp.get("channel", {})
        channel_obj["A"] = channel_obj.get("A", 0)
        channel_obj["B"] = channel_obj.get("B", 0)
        ue_entry["channel"] = channel_obj
        # Generate random values for position and direction as an example
        ue_entry["position"] = [cp.get("min_distance", 0),0
            #round(random.uniform(1000, 15000), 6),
            #round(random.uniform(1000, 15000), 6)
        ]
        ue_entry["direction"] = round(random.uniform(0, 360), 6)
    
    # Generate sim_events based on the command
    command = command_entry["command"]
    duration = command_entry["duration"]
    command_list = command.split()
    if command_list[0] == "ping":
        sim_events = [
            {"start_time": 5, "event": "power_on"},
            {
                "start_time": 10,
                "end_time": duration + 10,
                "dst_addr": command_list[1],
                "payload_len": 1000,
                "delay": 1,
                "event": command_list[0]
            }
        ]
    elif command_list[0] == "iperf3":
        # Enclose each argument (except the command) in quotes
        iperf_args = [f'"{arg}"' for arg in command_list[1:]]
        args_str = ", ".join(iperf_args)
        sim_events = [
            {"start_time": 5, "event": "power_on"},
            {
                "event": "ext_app",
                "start_time": 10,
                "end_time": duration + 10,
                "prog": "ext_app.sh",
                "args": json.loads(f'["iperf3", {args_str}, "-V", "--debug"]')
            }
        ]
    ue_entry["sim_events"] = sim_events
    ue_list.append(ue_entry)

ue_list_content = json.dumps({"ue_list": ue_list}, indent=2)
users_scenario_content = ue_list_content

output_file_2 = os.path.join(output_dir, "users-scenario.cfg")
try:
    with open(output_file_2, 'w') as users_file:
        users_file.write(users_scenario_content)
    print(f"File '{output_file_2}' generated successfully.")
except Exception as e:
    print(f"Error writing file '{output_file_2}': {e}")
    sys.exit(1)

# -------------- Generate ext_app.sh --------------
ext_app_content = """#!/bin/bash

ue_id="$1"      # UE id
duration="$2"   # Sim duration

shift
shift

function end {
    exit 0
}
trap end INT TERM

echo "ip netns exec $ue_id $@"
ip netns exec $ue_id $@
"""

output_file_3 = os.path.join(output_dir, "ext_app.sh")
try:
    with open(output_file_3, 'w') as ext_app_file:
        ext_app_file.write(ext_app_content)
    os.chmod(output_file_3, 0o755)
    print(f"File '{output_file_3}' generated successfully.")
except Exception as e:
    print(f"Error writing file '{output_file_3}': {e}")
    sys.exit(1)

# -------------- Generate ue-ifup Script --------------
ue_ifup_content = """#!/bin/bash
# Copyright (C) 2022-2024 Amarisoft
# lteue PDN configurator script version 2024-06-14

ue_id="$1"           # UE ID
pdn_id="$2"          # PDN unique id (start from 0)
ifname="$3"          # Interface name
ipv4_addr="$4"       # IPv4 address
ipv4_dns="$5"        # IPv4 DNS
ipv6_local_addr="$6" # IPv6 local address
ipv6_dns="$7"        # IPv6 DNS
param="$8"           # UE param
old_link_local=""

# Optional parameters
shift; shift; shift; shift; shift; shift; shift; shift;
while [ "$1" != "" ] ; do
    case "$1" in
    --mtu)
        mtu="$2"
        shift
        ;;
    *)
        echo "Bad parameter: $1" >&2
        exit 1
        ;;
    esac
    shift
done

if [ "$pdn_id" = "0" ] ; then
    if [ -e /var/run/netns/$ue_id ] ; then
        ip netns del $ue_id
    fi
    ip netns add $ue_id
fi

if [ "$ipv4_dns" != "" ] || [ "$ipv6_dns" != "" ] ; then
    mkdir -p /etc/netns/$ue_id
    rm -f /etc/netns/$ue_id/resolv.conf
    if [ "$ipv4_dns" != "" ] ; then
        echo "nameserver $ipv4_dns" >> /etc/netns/$ue_id/resolv.conf
    fi
    if [ "$ipv6_dns" != "" ] ; then
        echo "nameserver $ipv6_dns" >> /etc/netns/$ue_id/resolv.conf
    fi
else
    rm -f /etc/netns/$ue_id/resolv.conf
fi

ifname1="pdn$pdn_id"
ip link set dev $ifname name $ifname1 netns $ue_id
ifname="$ifname1"

if [ "$ipv6_local_addr" != "" ] ; then
    ip netns exec $ue_id bash -c "echo '0' > /proc/sys/net/ipv6/conf/$ifname/disable_ipv6"
    ip netns exec $ue_id bash -c "echo '1' > /proc/sys/net/ipv6/conf/$ifname/accept_ra"
    ip netns exec $ue_id bash -c "echo '1' > /proc/sys/net/ipv6/conf/$ifname/router_solicitation_delay"
    ip netns exec $ue_id bash -c "echo '1' > /proc/sys/net/ipv6/conf/$ifname/autoconf"
else
    ip netns exec $ue_id bash -c "echo '1' > /proc/sys/net/ipv6/conf/$ifname/disable_ipv6"
fi

if [ "$pdn_id" = "0" ] ; then
    ip netns exec $ue_id ifconfig lo up
fi

ip netns exec $ue_id ifconfig $ifname up
if [ "$ipv4_addr" != "" ] ; then
    ip netns exec $ue_id ifconfig $ifname $ipv4_addr/24
    if [ "$pdn_id" = "0" ] ; then
        ip netns exec $ue_id ip route add default via $ipv4_addr
    fi
    if [ "$mtu" != "" ] ; then
        ip netns exec $ue_id ifconfig $ifname mtu $mtu
    fi
fi
if [ "$ipv6_local_addr" != "" ] ; then
    old_link_local=`ip netns exec $ue_id ip addr show dev $ifname | sed -e's/^.*inet6 \([^ ]*\)\/.*$/\1/;t;d'`
    if [ "$old_link_local" != "" ] ; then
        ip netns exec $ue_id ifconfig $ifname inet6 del $old_link_local/64
    fi
    ip netns exec $ue_id ifconfig $ifname inet6 add $ipv6_local_addr/64
fi

if [ "$ipv4_addr" != "" -a "$ipv6_local_addr" != "" ] ; then
    echo "MAC_ADDR="$(ip netns exec $ue_id ip link show dev $ifname | grep -oP "ether \K[\d:a-f]+")
fi
"""

output_file_4 = os.path.join(output_dir, "ue-ifup")
try:
    with open(output_file_4, 'w') as ue_ifup_file:
        ue_ifup_file.write(ue_ifup_content)
    os.chmod(output_file_4, 0o755)
    print(f"File '{output_file_4}' generated successfully.")
except Exception as e:
    print(f"Error writing file '{output_file_4}': {e}")
    sys.exit(1)
