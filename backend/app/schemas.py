from pydantic import BaseModel
from datetime import datetime, date

class LogOut(BaseModel):
    id: int
    datahora: datetime
    acao: str
    detalhes: str
    class Config: from_attributes = True

class ProcessResponse(BaseModel):
    message: str
