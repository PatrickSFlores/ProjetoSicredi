# 01_carga_bruta.py

import re
import time
import csv
from pathlib import Path
import pandas as pd

# ------------------------- Paths / Pastas -------------------------
BASE = Path(__file__).resolve().parents[1]
P_BRUTOS = BASE / "dados" / "brutos" / "MOV_CC_OK_V2.PRN"
P_INTERM = BASE / "dados" / "intermediarios"
P_RESULT = BASE / "dados" / "resultados"
P_INTERM.mkdir(parents=True, exist_ok=True)
P_RESULT.mkdir(parents=True, exist_ok=True)
LOG = P_RESULT / "log_pipeline.csv"

# ------------------------- Logging -------------------------
def log(stage: str, msg: str, rows: int | None = None, tstart: float | None = None):
    elapsed = round(time.time() - tstart, 3) if tstart else ""
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([stage, msg, rows if rows is not None else "", elapsed])

# ------------------------- Regex / Constantes -------------------------
RE_TOTAL = re.compile(r"^\s*Total UA:")
RE_DATAHORA = re.compile(r"^\s*(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})\s*$")
RE_ORIGEM = re.compile(r"^\s*(\d{4}/\d{2})\s+(.*)$")
RE_PAGEBITS = re.compile(r"(COOP CRED|SISTEMA SICREDI|PAGINA:|POSTO:)")
RE_SEP = re.compile(r"^-{5,}|^={5,}")
RE_VAL = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")       
RE_SMALLINT = re.compile(r"^\d{1,2}$")                  

# Posições do cabeçalho
DEBIT_COL: int | None = None
CREDIT_COL: int | None = None

# ------------------------- Utilidades -------------------------
def to_float_br(v: str | None) -> float:
    if not v:
        return 0.0
    try:
        return float(v.replace(".", "").replace(",", "."))
    except Exception:
        return 0.0

def is_docto_token(tok: str) -> bool:
    """
    Heurística para identificar 'Docto' (sem depender de lista de prefixos):
    - só dígitos com 6–12 dígitos (ex.: 7462148, 383917409)
    - letras (1–3) + dígitos (4–10) (ex.: SI00178, CX972954, CE0109097)
    """
    if re.fullmatch(r"\d{6,12}", tok):
        return True
    if re.fullmatch(r"[A-Z]{1,3}\d{4,10}", tok):
        return True
    return False

# ------------------------- Parser de linha de conteúdo -------------------------
def parse_content_line(raw_line: str, origem_atual: str | None):
    """
    Extrai campos de uma linha de conteúdo.
    - 'Conta' é fixo (99999-9)
    - 'Nome_Correntista' é fixo (ASSOCIADO TESTE).
    - 'Docto' é o token imediatamente após 'TESTE' SE parecer um Docto (regex). Caso contrário, Docto = "".
    - 'Cod_Descricao' é o restante após Docto (ou após TESTE se Docto estiver vazio) até antes do 1º valor monetário.
    - Débito/Crédito: definidos pela posição horizontal relativa às colunas do cabeçalho.
    """
    global DEBIT_COL, CREDIT_COL

    line = raw_line.rstrip("\n\r")

    # Origem no começo da linha?
    m_or = RE_ORIGEM.match(line)
    if m_or:
        origem = m_or.group(1)
        rest = m_or.group(2)
    else:
        origem = origem_atual
        rest = line

    tokens = rest.split()
    if len(tokens) < 3 or "TESTE" not in tokens:
        return None, origem

    conta = "99999-9"
    nome = "ASSOCIADO TESTE"

    idx_teste = tokens.index("TESTE")

    # Candidato a Docto (token após "TESTE")
    docto = ""
    start_desc_idx = idx_teste + 1
    if len(tokens) > idx_teste + 1:
        cand = tokens[idx_teste + 1]
        if is_docto_token(cand):
            docto = cand
            start_desc_idx = idx_teste + 2  # descrição começa após o Docto

    # Cod_Descricao = do start_desc_idx até antes do 1º valor monetário
    desc_tokens = []
    for p in tokens[start_desc_idx:]:
        if RE_VAL.fullmatch(p):
            break
        desc_tokens.append(p)
    cod_desc = " ".join(desc_tokens).strip()

    # Localiza valores com posição horizontal na linha original
    valores = [(m.group(0), m.start()) for m in re.finditer(RE_VAL, line)]
    deb_raw = cred_raw = ""

    if len(valores) >= 2:
        valores.sort(key=lambda x: x[1])
        deb_raw, cred_raw = valores[0][0], valores[-1][0]
    elif len(valores) == 1:
        val, pos = valores[0]
        if DEBIT_COL is not None and CREDIT_COL is not None:
            mid = (DEBIT_COL + CREDIT_COL) // 2
            if pos < mid:
                deb_raw = val
            else:
                cred_raw = val
        else:
            # fallback: se não achou cabeçalho, assume crédito
            cred_raw = val

    # Id = último inteiro curto (1–2 dígitos) presente na linha
    ids = [p for p in tokens if RE_SMALLINT.fullmatch(p)]
    id_ = ids[-1] if ids else ""

    return ({
        "Origem": origem,
        "Conta": conta,
        "Nome_Correntista": nome,
        "Docto": docto,              # pode ser vazio corretamente
        "Cod_Descricao": cod_desc,
        "DR": "",                    # manter em branco
        "Debito_raw": deb_raw,
        "Credito_raw": cred_raw,
        "Id": id_
    }, origem)

# ------------------------- Main -------------------------
def main():
    t0 = time.time()
    log("start", "início carga PRN")

    origem_atual: str | None = None
    pending = None            # registro aguardando a linha de Data/Hora
    buffer = []               # registros prontos
    part_idx = 1
    total_rows = 0
    part_size = 250_000       # ajuste conforme memória

    global DEBIT_COL, CREDIT_COL

    with open(P_BRUTOS, "r", encoding="latin1", errors="ignore") as f:
        for raw in f:
            # Não usar strip() total para preservar posições horizontais
            line = raw.rstrip("\n\r")

            if not line.strip():
                continue

            # Captura posições das colunas Debito/Credito do cabeçalho
            if (" Debito" in line) and ("Credito" in line):
                try:
                    DEBIT_COL = line.index(" Debito")
                    CREDIT_COL = line.index("Credito")
                except ValueError:
                    DEBIT_COL = CREDIT_COL = None
                continue

            # Ignora separadores, páginas e linha de cabeçalho "Origem  Conta ..."
            if RE_SEP.match(line) or RE_PAGEBITS.search(line) or line.strip().startswith("Origem"):
                continue

            # Ignora blocos "Total UA:"
            if RE_TOTAL.match(line):
                pending = None
                continue

            # Linha de Data/Hora (segunda linha do registro)
            mdt = RE_DATAHORA.match(line)
            if mdt and pending:
                pending["Data"] = mdt.group(1)
                pending["Hora"] = mdt.group(2)
                buffer.append(pending)
                total_rows += 1
                pending = None

                # Grava em partes
                if len(buffer) >= part_size:
                    tpart = time.time()
                    df = pd.DataFrame(buffer)
                    df["Debito"] = df["Debito_raw"].map(to_float_br)
                    df["Credito"] = df["Credito_raw"].map(to_float_br)
                    df.drop(columns=["Debito_raw", "Credito_raw"], inplace=True)
                    out = P_INTERM / f"part_{part_idx:04d}.parquet"
                    df.to_parquet(out, index=False)
                    log("write_part", f"gravou {out.name}", rows=len(df), tstart=tpart)
                    buffer.clear()
                    part_idx += 1
                continue

            # Linha de conteúdo
            parsed, origem_atual = parse_content_line(line, origem_atual)
            if parsed:
                pending = parsed

    # Flush final
    if pending:
        # registro sem Data/Hora → descarta e loga
        log("warn", "registro ignorado sem Data/Hora casada")

    if buffer:
        tpart = time.time()
        df = pd.DataFrame(buffer)
        if not df.empty:
            df["Debito"] = df["Debito_raw"].map(to_float_br)
            df["Credito"] = df["Credito_raw"].map(to_float_br)
            df.drop(columns=["Debito_raw", "Credito_raw"], inplace=True)
            out = P_INTERM / f"part_{part_idx:04d}.parquet"
            df.to_parquet(out, index=False)
            log("write_part", f"gravou {out.name}", rows=len(df), tstart=tpart)

    log("end", "fim carga PRN", rows=total_rows, tstart=t0)

if __name__ == "__main__":
    main()