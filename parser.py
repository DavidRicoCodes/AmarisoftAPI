#!/usr/bin/env python3
import sys
import os

def split_log_all(input_file, trace_out, json_out):
    """
    Reads the entire log, pulls out every JSON object (balanced braces), and
    writes:
      - trace_out: all lines _outside_ of those JSON objects
      - json_out: all JSON blobs, each separated by a blank line
    """
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    trace_lines = []
    json_blobs = []

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        # look for JSON start anywhere in line
        start = line.find('{')
        if start == -1:
            # no JSON start: it's trace
            trace_lines.append(line)
            i += 1
            continue

        # we found the start of a JSON blob
        depth = 0
        in_json = False
        buf = []

        # process lines until balanced braces close
        while i < n:
            l = lines[i]
            if not in_json:
                # first JSON line: take from the first '{' onward
                l = l[start:]
                in_json = True
            buf.append(l)

            # update brace depth
            for c in l:
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1

            i += 1
            # when depth returns to zero, we've closed the JSON
            if in_json and depth == 0:
                break

        json_blobs.append(''.join(buf))
        # after capturing JSON, continue scanning for more, trace lines
    # end while

    # write trace portion
    with open(trace_out, 'w', encoding='utf-8') as tf:
        tf.writelines(trace_lines)

    # write all JSON blobs, separated by one blank line
    with open(json_out, 'w', encoding='utf-8') as jf:
        for idx, jb in enumerate(json_blobs, start=1):
            jf.write(jb.rstrip() + '\n')
            if idx != len(json_blobs):
                jf.write('\n')  # blank line between JSONs

    print(f"Trace saved to {trace_out}, {len(json_blobs)} JSON blob(s) saved to {json_out}")

def main():
    if len(sys.argv) != 4:
        print("Usage: parser.py <input_log> <trace_output> <json_output>")
        sys.exit(1)

    input_log = sys.argv[1]
    trace_out  = sys.argv[2]
    json_out   = sys.argv[3]

    if not os.path.isfile(input_log):
        print(f"Error: input file '{input_log}' not found.")
        sys.exit(1)

    split_log_all(input_log, trace_out, json_out)

if __name__ == "__main__":
    main()
