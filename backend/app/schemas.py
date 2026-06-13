from pydantic import BaseModel, Field, field_validator


class PromptIn(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1)
    categoria: str = "Geral"
    tags: list[str] = Field(default_factory=list, max_length=3)

    @field_validator("titulo", "prompt", "categoria", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("categoria")
    @classmethod
    def _categoria_vazia_vira_geral(cls, v: str) -> str:
        return v or "Geral"

    @field_validator("tags", mode="before")
    @classmethod
    def _limpar_tags(cls, v):
        if isinstance(v, list):
            return [t.strip() for t in v if isinstance(t, str) and t.strip()]
        return v


PromptUpdate = PromptIn  # mesmos campos, semântica de atualização parcial


class ArquivoOut(BaseModel):
    id: int
    nome: str
    tamanho: int


class PromptOut(PromptIn):
    id: int
    data: str
    fixado: bool
    arquivos: list[ArquivoOut] = Field(default_factory=list)
