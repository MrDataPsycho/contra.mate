"""Contract models for CUAD dataset"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, Text


class ContractAsmd(SQLModel, table=True):
    """Contract Analysis and Summarization Metadata (ASMD) table for CUAD dataset"""

    __tablename__ = "contract_asmd"

    # Composite primary key
    project_id: str = Field(primary_key=True, max_length=50, description="Project identifier")
    reference_doc_id: str = Field(primary_key=True, max_length=100, description="Reference document identifier")

    # Core contract identifiers
    document_title: str = Field(max_length=500, index=True, description="Contract document title/filename")

    # Document metadata
    document_name: Optional[str] = Field(default=None, sa_column=Column(Text), description="Document name from contract")
    document_name_answer: Optional[str] = Field(default=None, sa_column=Column(Text), description="Processed document name")

    # Parties
    parties: Optional[str] = Field(default=None, sa_column=Column(Text), description="Contract parties (raw)")
    parties_answer: Optional[str] = Field(default=None, sa_column=Column(Text), description="Processed parties information")

    # Key dates
    agreement_date: Optional[str] = Field(default=None, sa_column=Column(Text), description="Agreement date (raw)")
    agreement_date_answer: Optional[str] = Field(default=None, max_length=50, description="Processed agreement date")

    effective_date: Optional[str] = Field(default=None, sa_column=Column(Text), description="Effective date (raw)")
    effective_date_answer: Optional[str] = Field(default=None, max_length=50, description="Processed effective date")

    expiration_date: Optional[str] = Field(default=None, sa_column=Column(Text), description="Expiration date (raw)")
    expiration_date_answer: Optional[str] = Field(default=None, max_length=50, description="Processed expiration date")

    # Renewal terms
    renewal_term: Optional[str] = Field(default=None, sa_column=Column(Text), description="Renewal term (raw)")
    renewal_term_answer: Optional[str] = Field(default=None, max_length=200, description="Processed renewal term")

    notice_period_to_terminate_renewal: Optional[str] = Field(default=None, sa_column=Column(Text), description="Notice period (raw)")
    notice_period_to_terminate_renewal_answer: Optional[str] = Field(default=None, max_length=200, description="Processed notice period")

    # Legal
    governing_law: Optional[str] = Field(default=None, sa_column=Column(Text), description="Governing law (raw)")
    governing_law_answer: Optional[str] = Field(default=None, max_length=100, description="Processed governing law")

    # Contract clauses (Boolean indicators with raw text)
    most_favored_nation: Optional[str] = Field(default=None, sa_column=Column(Text), description="Most favored nation clause (raw)")
    most_favored_nation_answer: Optional[str] = Field(default=None, max_length=10, description="MFN answer (Yes/No)")

    competitive_restriction_exception: Optional[str] = Field(default=None, sa_column=Column(Text), description="Competitive restriction exception (raw)")
    competitive_restriction_exception_answer: Optional[str] = Field(default=None, max_length=10, description="Competitive restriction answer")

    non_compete: Optional[str] = Field(default=None, sa_column=Column(Text), description="Non-compete clause (raw)")
    non_compete_answer: Optional[str] = Field(default=None, max_length=10, description="Non-compete answer")

    exclusivity: Optional[str] = Field(default=None, sa_column=Column(Text), description="Exclusivity clause (raw)")
    exclusivity_answer: Optional[str] = Field(default=None, max_length=10, description="Exclusivity answer")

    no_solicit_of_customers: Optional[str] = Field(default=None, sa_column=Column(Text), description="No-solicit customers (raw)")
    no_solicit_of_customers_answer: Optional[str] = Field(default=None, max_length=10, description="No-solicit customers answer")

    no_solicit_of_employees: Optional[str] = Field(default=None, sa_column=Column(Text), description="No-solicit employees (raw)")
    no_solicit_of_employees_answer: Optional[str] = Field(default=None, max_length=10, description="No-solicit employees answer")

    non_disparagement: Optional[str] = Field(default=None, sa_column=Column(Text), description="Non-disparagement clause (raw)")
    non_disparagement_answer: Optional[str] = Field(default=None, max_length=10, description="Non-disparagement answer")

    termination_for_convenience: Optional[str] = Field(default=None, sa_column=Column(Text), description="Termination for convenience (raw)")
    termination_for_convenience_answer: Optional[str] = Field(default=None, max_length=10, description="Termination for convenience answer")

    # Rights and ownership
    rofr_rofo_rofn: Optional[str] = Field(default=None, sa_column=Column(Text), description="Right of first refusal/offer/negotiation (raw)")
    rofr_rofo_rofn_answer: Optional[str] = Field(default=None, max_length=10, description="ROFR/ROFO/ROFN answer")

    change_of_control: Optional[str] = Field(default=None, sa_column=Column(Text), description="Change of control clause (raw)")
    change_of_control_answer: Optional[str] = Field(default=None, max_length=10, description="Change of control answer")

    anti_assignment: Optional[str] = Field(default=None, sa_column=Column(Text), description="Anti-assignment clause (raw)")
    anti_assignment_answer: Optional[str] = Field(default=None, max_length=10, description="Anti-assignment answer")

    # Financial terms
    revenue_profit_sharing: Optional[str] = Field(default=None, sa_column=Column(Text), description="Revenue/profit sharing (raw)")
    revenue_profit_sharing_answer: Optional[str] = Field(default=None, max_length=10, description="Revenue/profit sharing answer")

    price_restrictions: Optional[str] = Field(default=None, sa_column=Column(Text), description="Price restrictions (raw)")
    price_restrictions_answer: Optional[str] = Field(default=None, max_length=10, description="Price restrictions answer")

    minimum_commitment: Optional[str] = Field(default=None, sa_column=Column(Text), description="Minimum commitment (raw)")
    minimum_commitment_answer: Optional[str] = Field(default=None, max_length=10, description="Minimum commitment answer")

    volume_restriction: Optional[str] = Field(default=None, sa_column=Column(Text), description="Volume restriction (raw)")
    volume_restriction_answer: Optional[str] = Field(default=None, max_length=10, description="Volume restriction answer")

    # IP and licensing
    ip_ownership_assignment: Optional[str] = Field(default=None, sa_column=Column(Text), description="IP ownership assignment (raw)")
    ip_ownership_assignment_answer: Optional[str] = Field(default=None, max_length=10, description="IP ownership assignment answer")

    joint_ip_ownership: Optional[str] = Field(default=None, sa_column=Column(Text), description="Joint IP ownership (raw)")
    joint_ip_ownership_answer: Optional[str] = Field(default=None, max_length=10, description="Joint IP ownership answer")

    license_grant: Optional[str] = Field(default=None, sa_column=Column(Text), description="License grant (raw)")
    license_grant_answer: Optional[str] = Field(default=None, max_length=10, description="License grant answer")

    non_transferable_license: Optional[str] = Field(default=None, sa_column=Column(Text), description="Non-transferable license (raw)")
    non_transferable_license_answer: Optional[str] = Field(default=None, max_length=10, description="Non-transferable license answer")

    # Liability and warranty
    uncapped_liability: Optional[str] = Field(default=None, sa_column=Column(Text), description="Uncapped liability (raw)")
    uncapped_liability_answer: Optional[str] = Field(default=None, max_length=10, description="Uncapped liability answer")

    cap_on_liability: Optional[str] = Field(default=None, sa_column=Column(Text), description="Cap on liability (raw)")
    cap_on_liability_answer: Optional[str] = Field(default=None, max_length=10, description="Cap on liability answer")

    liquidated_damages: Optional[str] = Field(default=None, sa_column=Column(Text), description="Liquidated damages (raw)")
    liquidated_damages_answer: Optional[str] = Field(default=None, max_length=10, description="Liquidated damages answer")

    warranty_duration: Optional[str] = Field(default=None, sa_column=Column(Text), description="Warranty duration (raw)")
    warranty_duration_answer: Optional[str] = Field(default=None, max_length=10, description="Warranty duration answer")

    # Other provisions
    insurance: Optional[str] = Field(default=None, sa_column=Column(Text), description="Insurance requirements (raw)")
    insurance_answer: Optional[str] = Field(default=None, max_length=10, description="Insurance answer")

    audit_rights: Optional[str] = Field(default=None, sa_column=Column(Text), description="Audit rights (raw)")
    audit_rights_answer: Optional[str] = Field(default=None, max_length=10, description="Audit rights answer")

    covenant_not_to_sue: Optional[str] = Field(default=None, sa_column=Column(Text), description="Covenant not to sue (raw)")
    covenant_not_to_sue_answer: Optional[str] = Field(default=None, max_length=10, description="Covenant not to sue answer")

    third_party_beneficiary: Optional[str] = Field(default=None, sa_column=Column(Text), description="Third party beneficiary (raw)")
    third_party_beneficiary_answer: Optional[str] = Field(default=None, max_length=10, description="Third party beneficiary answer")

    # Metadata
    created_at: Optional[datetime] = Field(default=None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Record last update timestamp")

    class Config:
        """SQLModel configuration"""
        schema_extra = {
            "example": {
                "project_id": "cuad_v1",
                "reference_doc_id": "doc_001",
                "document_title": "contract_example.pdf",
                "document_name": "Software License Agreement",
                "parties_answer": "Company A; Company B",
                "agreement_date_answer": "2023-01-15",
                "governing_law_answer": "California",
                "exclusivity_answer": "Yes",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }