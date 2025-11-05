# 04_metricas.py
import time, csv, re
from pathlib import Path
import pandas as pd

# ------------------------- Paths -------------------------
BASE = Path(__file__).resolve().parents[1]
P_PROC = BASE / "dados" / "processados" / "movimentos_enriquecidos.parquet"
P_METRICAS = BASE / "dados" / "metricas"
P_RESULT = BASE / "dados" / "resultados"
P_METRICAS.mkdir(parents=True, exist_ok=True)
P_RESULT.mkdir(parents=True, exist_ok=True)
LOG = P_RESULT / "log_pipeline.csv"

# ------------------------- Logging -------------------------
def log(stage, msg, rows=None, tstart=None):
    elapsed = round(time.time() - tstart, 3) if tstart else ""
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([stage, msg, rows if rows is not None else "", elapsed])

# ------------------------- Principal -------------------------
def main():
    t0 = time.time()
    log("start", "início métricas")

    df = pd.read_parquet(P_PROC)

    # Tipagem/derivadas defensivas
    df["Debito"] = pd.to_numeric(df["Debito"], errors="coerce").fillna(0.0)
    df["Credito"] = pd.to_numeric(df["Credito"], errors="coerce").fillna(0.0)
    df["Diferenca"] = df["Debito"] - df["Credito"]
    # Data em tipo date para agregações por dia
    df["DataRef"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce").dt.date

    # =================== Métricas por Origem ===================
    t1 = time.time()
    met_origem = (
        df.groupby("Origem", as_index=False)
          .agg(
              Qtde_Registros=("Origem", "count"),
              Total_Debito=("Debito", "sum"),
              Total_Credito=("Credito", "sum"),
              Total_Diferenca=("Diferenca", "sum"),
          )
          .sort_values("Origem")
    )
    met_origem["Saldo_Final"] = met_origem["Total_Credito"] - met_origem["Total_Debito"]
    # NOVA: soma de débitos + créditos por origem
    met_origem["Soma_Mov"] = met_origem["Total_Debito"] + met_origem["Total_Credito"]

    met_origem.to_parquet(P_METRICAS / "metricas_por_origem.parquet", index=False)
    met_origem.to_csv(P_RESULT / "metricas_por_origem.csv", index=False, encoding="utf-8")
    log("metricas", "por origem (inclui Soma_Mov)", rows=len(met_origem), tstart=t1)

    # =================== Métricas por Dia da Semana ===================
    t2 = time.time()
    met_dia = (
        df.groupby("Dia_da_Semana", as_index=False)
          .agg(
              Qtde_Registros=("Dia_da_Semana", "count"),
              Total_Debito=("Debito", "sum"),
              Total_Credito=("Credito", "sum"),
              Total_Diferenca=("Diferenca", "sum"),
          )
          .sort_values("Dia_da_Semana")
    )
    met_dia["Saldo_Final"] = met_dia["Total_Credito"] - met_dia["Total_Debito"]

    met_dia.to_parquet(P_METRICAS / "metricas_por_dia.parquet", index=False)
    met_dia.to_csv(P_RESULT / "metricas_por_dia.csv", index=False, encoding="utf-8")
    log("metricas", "por dia da semana", rows=len(met_dia), tstart=t2)

    # =================== Extremos por Data ===================
    # 1) contagem por data
    t3 = time.time()
    por_data_count = (
        df.groupby("DataRef", as_index=False)
          .agg(Qtde_Registros=("DataRef", "count"))
          .sort_values("DataRef")
    )
    por_data_count.to_parquet(P_METRICAS / "metricas_por_data_qtd.parquet", index=False)
    por_data_count.to_csv(P_RESULT / "metricas_por_data_qtd.csv", index=False, encoding="utf-8")

    # data com maior/menor quantidade
    max_qtd = por_data_count.loc[por_data_count["Qtde_Registros"].idxmax()]
    min_qtd = por_data_count.loc[por_data_count["Qtde_Registros"].idxmin()]

    # 2) soma de movimentações por data (Débito + Crédito)
    por_data_soma = (
        df.assign(Soma_Mov=df["Debito"] + df["Credito"])
          .groupby("DataRef", as_index=False)
          .agg(Soma_Mov=("Soma_Mov", "sum"))
          .sort_values("DataRef")
    )
    por_data_soma.to_parquet(P_METRICAS / "metricas_por_data_soma.parquet", index=False)
    por_data_soma.to_csv(P_RESULT / "metricas_por_data_soma.csv", index=False, encoding="utf-8")

    max_soma = por_data_soma.loc[por_data_soma["Soma_Mov"].idxmax()]
    min_soma = por_data_soma.loc[por_data_soma["Soma_Mov"].idxmin()]

    # Tabela-resumo dos extremos
    extremos = pd.DataFrame([
        {"Metrica": "Maior Qtde", "Data": max_qtd["DataRef"], "Valor": int(max_qtd["Qtde_Registros"])},
        {"Metrica": "Menor Qtde", "Data": min_qtd["DataRef"], "Valor": int(min_qtd["Qtde_Registros"])},
        {"Metrica": "Maior Soma Mov.", "Data": max_soma["DataRef"], "Valor": float(max_soma["Soma_Mov"])},
        {"Metrica": "Menor Soma Mov.", "Data": min_soma["DataRef"], "Valor": float(min_soma["Soma_Mov"])},
    ])
    extremos.to_parquet(P_METRICAS / "metricas_extremos_por_data.parquet", index=False)
    extremos.to_csv(P_RESULT / "metricas_extremos_por_data.csv", index=False, encoding="utf-8")
    log("metricas", "extremos por data (qtde e soma)", rows=len(extremos), tstart=t3)

    # =================== RX1 / PX1 por Dia da Semana ===================
    t4 = time.time()
    # segurança com NaN e normalização simples
    cod = df["Cod_Descricao"].fillna("")
    mask_rx1 = cod.str.contains(r"\bRX1\b", regex=True, case=False)
    mask_px1 = cod.str.contains(r"\bPX1\b", regex=True, case=False)

    por_dia_cod = (
        df.assign(RX1=mask_rx1, PX1=mask_px1)
          .groupby("Dia_da_Semana", as_index=False)
          .agg(
              RX1_Quantidade=("RX1", "sum"),
              PX1_Quantidade=("PX1", "sum"),
              Qtde_Total=("Dia_da_Semana", "count"),
          )
          .sort_values("Dia_da_Semana")
    )
    por_dia_cod.to_parquet(P_METRICAS / "metricas_codigos_por_dia.parquet", index=False)
    por_dia_cod.to_csv(P_RESULT / "metricas_codigos_por_dia.csv", index=False, encoding="utf-8")
    log("metricas", "RX1/PX1 por dia da semana", rows=len(por_dia_cod), tstart=t4)

    # =================== Totais gerais ===================
    t5 = time.time()
    total = {
        "Total_Registros": len(df),
        "Debito_Total": df["Debito"].sum(),
        "Credito_Total": df["Credito"].sum(),
        "Saldo_Final": df["Credito"].sum() - df["Debito"].sum(),
        "Soma_Mov_Total": (df["Debito"] + df["Credito"]).sum(),
    }
    df_total = pd.DataFrame([total])
    df_total.to_parquet(P_METRICAS / "metricas_totais.parquet", index=False)
    df_total.to_csv(P_RESULT / "metricas_totais.csv", index=False, encoding="utf-8")
    log("metricas", "totais gerais", rows=1, tstart=t5)

    log("end", "fim métricas", rows=len(df), tstart=t0)

if __name__ == "__main__":
    main()