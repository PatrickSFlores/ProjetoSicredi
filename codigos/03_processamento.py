# 03_processamento.py
import time, csv
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
P_LIMPOS = BASE / "dados" / "limpos" / "movimentos_limpos.parquet"
P_PROC = BASE / "dados" / "processados"
P_RESULT = BASE / "dados" / "resultados"
P_PROC.mkdir(parents=True, exist_ok=True)
P_RESULT.mkdir(parents=True, exist_ok=True)

LOG = P_RESULT / "log_pipeline.csv"

def log(stage, msg, rows=None, tstart=None):
    elapsed = round(time.time() - tstart, 3) if tstart else ""
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([stage, msg, rows if rows is not None else "", elapsed])

def main():
    t0 = time.time()
    df = pd.read_parquet(P_LIMPOS)

    # Tipagem defensiva
    df["Debito"] = pd.to_numeric(df["Debito"], errors="coerce")
    df["Credito"] = pd.to_numeric(df["Credito"], errors="coerce")
    df["Id"] = pd.to_numeric(df.get("Id"), errors="coerce").astype("Int64")
    df["DR"] = pd.to_numeric(df.get("DR"), errors="coerce").astype("Int64")

    # Data/Hora → datetime e derivadas
    ts = pd.to_datetime(df["Data"] + " " + df["Hora"], format="%d/%m/%Y %H:%M", errors="coerce")
    df["DataHora"] = ts

    dias = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"]
    df["Dia_da_Semana"] = df["DataHora"].dt.dayofweek.map(lambda i: dias[i] if pd.notna(i) else None)

    df["Diferenca"] = df["Debito"].fillna(0.0) - df["Credito"].fillna(0.0)

    # Ordem de colunas + ordenação para facilitar checagens
    cols = [
        "Origem","Conta","Nome_Correntista","Docto","Cod_Descricao","DR",
        "Debito","Credito","Id","Data","Hora","Dia_da_Semana","Diferenca","DataHora"
    ]
    # Garante que todas existem (caso Docto ou DR tenham faltado em raras linhas)
    cols = [c for c in cols if c in df.columns]
    df = df[cols].sort_values(["Origem","Conta","DataHora","Id"], na_position="last")

    # Persistência
    out_pq = P_PROC / "movimentos_enriquecidos.parquet"
    df.to_parquet(out_pq, index=False)
    log("write_proc", out_pq.name, rows=len(df), tstart=t0)

    out_csv = P_RESULT / "movimentos_enriquecidos_sample.csv"
    df.head(1000).to_csv(out_csv, index=False, encoding="utf-8")
    log("write_csv_sample", out_csv.name, rows=min(1000, len(df)))

if __name__ == "__main__":
    main()