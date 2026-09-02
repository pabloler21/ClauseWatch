from pydantic import BaseModel, Field

class ContractChangeOutput(BaseModel):
    sections_changed: list[str] = Field(description="...")
    topics_touched: list[str] = Field(description="...")
    summary_of_the_change: str = Field(description="...")