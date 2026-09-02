from pydantic import BaseModel, Field
    
class ContractChangeOutput(BaseModel):
    sections_changed: list[str] = Field(
        description=(
            "Identifiers of the contract sections modified by the amendment, "
            "as they appear literally in the source document. Keep the original "
            "Spanish wording and numbering. Example: ['Cláusula 4.2', 'Cláusula 7']. "
            "Empty list if no section was modified."
        )
    )

    topics_touched: list[str] = Field(
        description=(
            "Legal or commercial categories affected by the changes, in Spanish. "
            "Use short noun phrases, not sentences. "
            "Example: ['plazo de pago', 'confidencialidad', 'jurisdicción']."
        )
    )

    summary_of_the_change: str = Field(
        description=(
            "Detailed description of every change, written in Spanish. For each "
            "change, state the section identifier, whether it is an addition, "
            "a deletion or a modification, and what the clause said before versus "
            "after. Do not generalize: cite the specific terms that changed."
        )
    )