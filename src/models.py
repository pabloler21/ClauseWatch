"""Modelo Pydantic que estructura y valida la salida del ExtractionAgent."""

from pydantic import BaseModel, Field


class ContractChangeOutput(BaseModel):
    """Structured result of comparing an original contract against its amendment.

    Produced by the extraction agent from the parsed text of both documents.
    """

    # Las description viajan dentro del JSON Schema que se manda a OpenAI: el
    # modelo las lee. No son documentacion para humanos.
    sections_changed: list[str] = Field(
        description=(
            "Exact section/clause identifiers that changed, written as they appear "
            "in the documents (e.g. '2. Plazo'). A clause is listed once however "
            "many changes it holds. Never include clauses identical in both documents."
        )
    )
    topics_touched: list[str] = Field(
        description=(
            "Distinct legal and commercial domains affected by the changes, in "
            "Spanish (e.g. 'Tarifas y pagos', 'Vigencia del contrato')."
        )
    )
    summary_of_the_change: str = Field(
        description=(
            "Objective audit summary in Spanish. Every individual change is reported "
            "separately, quoting the concrete values or wording involved, and stated "
            "explicitly as a modificación, an adición or an eliminación."
        )
    )
