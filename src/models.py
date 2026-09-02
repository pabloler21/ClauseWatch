from pydantic import BaseModel


class ContractChangeOutput(BaseModel):
    """Structured result of comparing an original contract against its amendment.

    Produced by the extraction agent from the parsed text of both documents.
    """

    sections_changed: list[str]
    topics_touched: list[str]
    summary_of_the_change: str
