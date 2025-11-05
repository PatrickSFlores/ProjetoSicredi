# 02_limpeza_dados.py
import time, csv
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
P_INTERM = BASE / "dados" / "intermediarios"
P_LIMPOS = BASE / "dados" / "limpos"
P_RESULT = BASE / "dados" / "resultados"
P_LIMPOS.mkdir(parents=True, exist_ok=True)
P_RESULT.mkdir(parents=True, exist_ok=True)

LOG = P_RESULT / "log_pipeline.csv"

def log(stage, msg, rows=None, tstart=None):
    import time, csv
    elapsed = round(time.time() - tstart, 3) if tstart else ""
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([stage, msg, rows if rows is not None else "", elapsed])

def main():
    t0 = time.time()
    parts = sorted(P_INTERM.glob("part_*.parquet"))
    dfs = []
    total = 0
    for p in parts:
        t = time.time()
        df = pd.read_parquet(p)
        # filtros mínimos de sanidade
        df = df.dropna(subset=["Conta","Origem","Data","Hora"])
        dfs.append(df)
        total += len(df)
        log("read_part", f"leu {p.name}", rows=len(df), tstart=t)

    if not dfs:
        log("error", "nenhuma parte encontrada")
        return

    t = time.time()
    full = pd.concat(dfs, ignore_index=True)
    # tipagem
    full["Id"] = pd.to_numeric(full["Id"], errors="coerce").astype("Int64")
    full["DR"] = pd.to_numeric(full["DR"], errors="coerce").astype("Int64")
    full.to_parquet(P_LIMPOS / "movimentos_limpos.parquet", index=False)
    log("write_clean", "movimentos_limpos.parquet", rows=len(full), tstart=t)

    # amostra para visualização rápida
    sample = full.head(50)
    sample.to_csv(P_RESULT / "preview_movimentos.csv", index=False, encoding="utf-8")
    log("write_csv_preview", "preview_movimentos.csv", rows=len(sample))

    log("end_clean", "limpeza concluída", rows=total, tstart=t0)

if __name__ == "__main__":
    main()