"""Modelos Pydantic que estructuran y validan las salidas de los modelos del pipeline."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ClauseChange(BaseModel):
    """A single atomic change detected between the original contract and its amendment."""

    section: str = Field(
        description=(
            "Exact section/clause identifier this change belongs to, written as it "
            "appears in the documents (e.g. '2. Plazo')."
        )
    )
    change_type: Literal["addition", "deletion", "modification"] = Field(
        description=(
            "'addition' only for a clause entirely absent from the original, "
            "'deletion' for wording present in the original and missing from the "
            "amendment, 'modification' for altered values or wording inside a clause "
            "that exists in both documents."
        )
    )
    detail: str = Field(
        description=(
            "What changed, in Spanish, quoting the concrete values or wording involved."
        )
    )


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
    # Campo adicional a los tres que pide la consigna: mueve la clasificacion de
    # los tres tipos de cambio de la prosa a un enum consultable por codigo.
    changes: list[ClauseChange] = Field(
        description=(
            "One entry per individual change. A clause holding three changes produces "
            "three entries. Must cover exactly the clauses listed in sections_changed."
        )
    )

    @model_validator(mode="after")
    def sections_must_match_changes(self) -> "ContractChangeOutput":
        """Verifica que `sections_changed` y `changes` no se contradigan entre si.

        El JSON Schema garantiza los tipos de cada campo, pero no que dos campos
        sean coherentes: el modelo puede listar seis secciones y detallar cinco.

        Returns:
            La instancia validada, sin modificar.

        Raises:
            ValueError: Si el conjunto de secciones de `changes` no coincide
                exactamente con `sections_changed`.
        """
        detalladas = {cambio.section for cambio in self.changes}
        declaradas = set(self.sections_changed)

        if detalladas != declaradas:
            raise ValueError(
                "Inconsistencia interna entre los campos de salida. "
                f"Declaradas en sections_changed y sin detallar en changes: "
                f"{sorted(declaradas - detalladas)}. "
                f"Detalladas en changes y ausentes de sections_changed: "
                f"{sorted(detalladas - declaradas)}."
            )

        return self


class DocumentMatchVerdict(BaseModel):
    """Verdict on whether two documents belong to the same agreement.

    Produced by the document match check before the two agents run, so that an
    unrelated pair of documents is rejected instead of compared.
    """

    # Una sola decision y no "mismas partes AND mismo objeto": una enmienda puede
    # cambiar una parte (cesion, fusion) y seguir siendo el mismo contrato.
    same_agreement: bool = Field(
        description=(
            "True if the second document amends, restates or replaces the specific "
            "agreement in the first document. False if it is a different agreement, "
            "even between the same parties."
        )
    )
    matching_evidence: list[str] = Field(
        description=(
            "Verbatim quotes from either document that support correspondence: "
            "title, execution date, parties, explicit reference to the original."
        )
    )
    mismatch_evidence: list[str] = Field(
        description=(
            "Verbatim quotes from either document that contradict correspondence: "
            "a different agreement type, date, subject matter or unrelated parties."
        )
    )
    reason: str = Field(
        description=(
            "One or two sentences in Spanish explaining the verdict, suitable to "
            "show to the user if the pair is rejected."
        )
    )
