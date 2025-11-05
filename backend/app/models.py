from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Float, DateTime, Date, Text
from .db import Base

class Movimento(Base):
    __tablename__ = "movimentos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    origem: Mapped[str] = mapped_column(String(16), index=True)     # ex: "0109/07"
    coop: Mapped[str] = mapped_column(String(8))                     # "0109"
    agencia: Mapped[str] = mapped_column(String(8))                  # "07"

    conta: Mapped[str] = mapped_column(String(32), index=True)
    nome_correntista: Mapped[str] = mapped_column(String(128))
    docto: Mapped[str] = mapped_column(String(32), nullable=True)
    cod_descricao: Mapped[str] = mapped_column(Text)

    dr: Mapped[int] = mapped_column(Integer, nullable=True)
    debito: Mapped[float] = mapped_column(Float)
    credito: Mapped[float] = mapped_column(Float)
    id_linha: Mapped[int] = mapped_column(Integer, nullable=True)

    data_ref: Mapped[Date] = mapped_column(Date, index=True)         # só a data
    hora_txt: Mapped[str] = mapped_column(String(5))                 # "HH:MM"
    datahora: Mapped[DateTime] = mapped_column(DateTime, index=True) # datetime

    dia_semana: Mapped[str] = mapped_column(String(16))
    diferenca: Mapped[float] = mapped_column(Float)

class LogAcao(Base):
    __tablename__ = "logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datahora: Mapped[DateTime] = mapped_column(DateTime, index=True)
    acao: Mapped[str] = mapped_column(String(128))
    detalhes: Mapped[str] = mapped_column(Text)