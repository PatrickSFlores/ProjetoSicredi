import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import LogAcao
from .schemas import ProcessResponse
from .etl import save_upload, full_pipeline, log_event
from .utils import now_ts

DATA_DIR = Path(os.environ.get("DATA_DIR","/app/dados"))
app = FastAPI(title="ETL Sicredi", version="1.0.0")

# cria as tabelas no Postgres
Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok", "time": str(now_ts())}

@app.post("/upload", response_model=ProcessResponse)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith((".prn", ".txt", ".csv")):
        raise HTTPException(400, "Formato não suportado")
    tmp = DATA_DIR / "brutos" / f"tmp_{file.filename}"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "wb") as f:
        f.write(await file.read())
    final_path = save_upload(tmp, "MOV_CC_OK_V2.PRN")
    log_event(db, "upload", f"arquivo salvo em {final_path}")
    return {"message": "upload concluído"}

@app.post("/processar", response_model=ProcessResponse)
def processar(run_metrics: bool = True, db: Session = Depends(get_db)):
    full_pipeline(db, run_metrics=run_metrics)
    log_event(db, "etl", "pipeline executado com sucesso")
    return {"message": "ETL executado e dados carregados no banco"}

# ====== Endpoints de métricas simples via SQL ======
@app.get("/metrics/extremos")
def extremos(db: Session = Depends(get_db)):
    q = """
    with c as (
      select data_ref, count(*) as qtde, sum(debito+credito) as soma_mov
      from movimentos
      group by data_ref
    )
    select
      (select data_ref from c order by qtde desc limit 1) as data_mais_qtde,
      (select qtde     from c order by qtde desc limit 1) as mais_qtde,
      (select data_ref from c order by qtde asc  limit 1) as data_menos_qtde,
      (select qtde     from c order by qtde asc  limit 1) as menos_qtde,
      (select data_ref from c order by soma_mov desc limit 1) as data_mais_soma,
      (select soma_mov from c order by soma_mov desc limit 1) as mais_soma,
      (select data_ref from c order by soma_mov asc  limit 1) as data_menos_soma,
      (select soma_mov from c order by soma_mov asc  limit 1) as menos_soma
    """
    return dict(db.execute(q).mappings().first())

@app.get("/metrics/origem")
def metricas_origem(db: Session = Depends(get_db)):
    q = """
    select origem,
           count(*) as qtde_registros,
           sum(debito) as total_debito,
           sum(credito) as total_credito,
           sum(credito) - sum(debito) as saldo_final,
           sum(debito + credito) as soma_mov
    from movimentos
    group by origem
    order by origem
    """
    return [dict(r) for r in db.execute(q).mappings().all()]

@app.get("/metrics/codigos_por_dia")
def codigos_por_dia(db: Session = Depends(get_db)):
    q = """
    select
      dia_semana,
      sum(case when position('RX1' in upper(cod_descricao)) > 0 then 1 else 0 end) as rx1_quantidade,
      sum(case when position('PX1' in upper(cod_descricao)) > 0 then 1 else 0 end) as px1_quantidade,
      count(*) as qtde_total
    from movimentos
    group by dia_semana
    order by dia_semana
    """
    return [dict(r) for r in db.execute(q).mappings().all()]
