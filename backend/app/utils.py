from datetime import datetime

def now_ts():
    return datetime.now()

def split_origem(origem: str):
    # "0109/07" -> ("0109","07")
    try:
        coop, agencia = origem.strip().split("/")
        return coop, agencia
    except Exception:
        return "", ""
