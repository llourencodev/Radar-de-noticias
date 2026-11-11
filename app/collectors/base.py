from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawItem:
    """Item como veio da fonte, antes de qualquer processamento. Nada aqui é inventado."""
    title: str
    url: str
    outlet: str | None = None             # veículo/órgão (quando a fonte informa)
    outlet_url: str | None = None
    published: datetime | None = None
    date_precision: str | None = None     # 'datetime' | 'date' | None
    excerpt: str = ""
    image_url: str | None = None
    image_origin: str = "nenhuma"         # 'feed' | 'pagina' | 'nenhuma'
    via_aggregator: bool = False
    tags: list[str] = field(default_factory=list)


@dataclass
class FetchResult:
    status: str                   # 'ok' | 'inalterado' | 'erro'
    http_status: int | None = None
    items: list[RawItem] = field(default_factory=list)
    etag: str | None = None
    last_modified: str | None = None
    error: str | None = None
