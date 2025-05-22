#!/usr/bin/env python3
import json
import sys

if len(sys.argv) != 2:
    print("Usage: parser.py <json_output>")  
    sys.exit(1)

json_log = sys.argv[1]

# 1) Leer la lista de JSONs
with open(json_log, "r", encoding="utf-8") as f:
    data = json.load(f)   # asume que json.log contiene algo como [{…}, {…}, …]

# 2) Deduplicar
seen = set()
unique = []
for obj in data:
    # serializamos con claves ordenadas para que la comparación no dependa del orden
    key = json.dumps(obj, sort_keys=True)
    if key not in seen:
        seen.add(key)
        unique.append(obj)

# 3) Guardar de nuevo
with open(json_log, "w", encoding="utf-8") as f:
    json.dump(unique, f, indent=2, ensure_ascii=False)
print(f"De {len(data)} objetos originales, quedan {len(unique)} únicos.")