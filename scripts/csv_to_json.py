import csv
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))
CSV_DIR = os.path.join(ROOT, "csv")
OUT_DIR = os.path.join(ROOT, "json")
os.makedirs(OUT_DIR, exist_ok=True)

def try_parse(v):
    if v is None:
        return None
    v = v.strip()
    if v == "":
        return None
    # remove common non-numeric characters like '*' used in CSV
    v_clean = re.sub(r"[^\d\.\-eE]", "", v)
    # try int then float, fallback to original string
    try:
        if re.fullmatch(r"-?\d+", v_clean):
            return int(v_clean)
        if re.fullmatch(r"-?\d+(\.\d+)?([eE]-?\d+)?", v_clean):
            return float(v_clean)
    except Exception:
        pass
    # return original trimmed string if parsing fails
    return v

def convert_file(in_path, out_path):
    with open(in_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            parsed = {k: try_parse(v) for k, v in r.items()}
            rows.append(parsed)
    with open(out_path, "w", encoding="utf-8") as wf:
        json.dump(rows, wf, ensure_ascii=False, indent=2)

def main():
    for fn in os.listdir(CSV_DIR):
        if not fn.lower().endswith(".csv"):
            continue
        inp = os.path.join(CSV_DIR, fn)
        outp = os.path.join(OUT_DIR, os.path.splitext(fn)[0] + ".json")
        print(f"Converting {fn} -> {os.path.relpath(outp)}")
        convert_file(inp, outp)
    print("Done. JSON files are in:", OUT_DIR)

if __name__ == "__main__":
    main()