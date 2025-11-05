import os, shutil, sys
from pathlib import Path
import importlib
import pandas as pd
from sqlalchemy.orm import Session
from .models import Movimento, LogAcao
from .utils import now_ts, split_origem

DATA_DIR = Path(os.environ.get("DATA_DIR","/app/dados"))

# permite importar "codigos.01_carga_bruta" etc
sys.path.append("/app")
sys.path.append("/app/codigos")

def log_event(db: Session, acao: str, detalhes: str):
    db.add(LogAcao(datahora=now_ts(), acao=acao, detalhes=detalhes))
    db.commit()

def save_upload(tmp_path: Path, dest_name: str) -> Path:
    dest = DATA_DIR / "brutos" / dest_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(tmp_path, dest)
    return dest

def run_script(module_name: str, func: str = "main"):
    mod = importlib.import_module(module_name)
    getattr(mod, func)()

def load_parquet_to_db(parquet_path: Path, db: Session):
    df = pd.read_parquet(parquet_path)

    rows = []
    for _, r in df.iterrows():
        coop, agencia = split_origem(str(r["Origem"]))
        rows.append(Movimento(
            origem=str(r["Origem"]),
            coop=coop, agencia=agencia,
            conta=str(r["Conta"]),
            nome_correntista=str(r.get("Nome_Correntista","")),
            docto=(None if pd.isna(r.get("Docto")) or r.get("Docto")=="" else str(r.get("Docto"))),
            cod_descricao=str(r.get("Cod_Descricao","")),
            dr=(None if pd.isna(r.get("DR")) else int(r.get("DR"))),
            debito=float(r.get("Debito",0.0) or 0.0),
            credito=float(r.get("Credito",0.0) or 0.0),
            id_linha=(None if pd.isna(r.get("Id")) else int(r.get("Id"))),
            data_ref=pd.to_datetime(r["Data"], format="%d/%m/%Y", errors="coerce").date(),
            hora_txt=str(r["Hora"]),
            datahora=pd.to_datetime(r["DataHora"]),
            dia_semana=str(r.get("Dia_da_Semana","")),
            diferenca=float(r.get("Diferenca",0.0) or 0.0),
        ))
    db.bulk_save_objects(rows)
    db.commit()

def full_pipeline(db: Session, run_metrics: bool = True):
    # 01
    run_script("codigos.01_carga_bruta")
    # 02 (opcional)
    try:
        run_script("codigos.02_limpeza_dados")
    except Exception:
        pass
    # 03
    run_script("codigos.03_processamento")
    # 04 (opcional)
    if run_metrics:
        try:
            run_script("codigos.04_metricas")
        except Exception:
            pass
    # carrega no banco
    parquet_final = DATA_DIR / "processados" / "movimentos_enriquecidos.parquet"
    load_parquet_to_db(parquet_final, db)
