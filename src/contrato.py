"""Contrato da resposta entre recuperação, API e interface (issue #2)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Modo = Literal["graphrag", "vetorial"]
Nivel = Literal["alta", "media", "baixa"]


class Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Confianca(Modelo):
    valor: float = Field(ge=0, le=1)
    nivel: Nivel
    criterio: str


class Caminho(Modelo):
    id: str              # "C1", citado na resposta
    nos: list[str]       # ids das entidades, na ordem do caminho
    relacoes: list[str]
    fontes: list[str]    # chunk_ids que sustentam as relações


class No(Modelo):
    id: str
    nome: str
    tipo: str
    pagerank: float | None = None
    comunidade: int | None = None


class Aresta(Modelo):
    origem: str
    destino: str
    tipo: str
    fontes: list[str]


class Subgrafo(Modelo):
    nos: list[No] = []
    arestas: list[Aresta] = []


class Fonte(Modelo):
    id: str              # "F1", citado na resposta
    chunk_id: str
    trecho: str
    documento: str
    url: str
    score: float | None = None


class Resposta(Modelo):
    pergunta: str
    modo: Modo
    resposta: str
    confianca: Confianca
    cypher: str | None = None
    caminhos: list[Caminho] = []
    subgrafo: Subgrafo = Subgrafo()
    nos_consultados: list[str] = []
    fontes: list[Fonte] = []
    avisos: list[str] = []