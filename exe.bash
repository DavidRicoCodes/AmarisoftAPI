#!/bin/bash
OUTFILE="posiciones.log"
while true; do
  echo -n "t" | nc -u -w1 localhost 9002
  sleep 0.1
done >> "$OUTFILE"
