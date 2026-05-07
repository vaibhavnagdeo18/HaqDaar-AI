import logging
from pydantic import BaseModel
from typing import List

logger = logging.getLogger(__name__)

class ComplianceReport(BaseModel):
    compliance_grade: int
    missing_fields: List[str]
    blocking_issues: List[str]
    is_ready_to_file: bool
    message: str

class ComplianceAgent:
    def __init__(self, gemini_service=None):
        # Gemini is optional for this specific rule-based audit
        self.gemini = gemini_service
        self.REQUIRED_FIELDS = ["breadwinner_name", "date_of_death", "employment_type", "had_epf", "state"]

    async def audit_family_data(self, family_data: dict) -> ComplianceReport:
        logger.info(f"Running compliance audit for data: {family_data}")
        
        score = 0
        missing = []
        
        for field in self.REQUIRED_FIELDS:
            val = family_data.get(field)
            if val and str(val).strip():
                score += 20
            else:
                missing.append(field.replace("_", " ").title())
        
        is_ready = (score == 100)
        
        if is_ready:
            # Note: The entitlement amount logic will be handled in main.py 
            # as it comes from the EntitlementAgent. 
            # We just provide the base message here.
            message = f"Compliance Score: 100/100. All information verified. Ready to file."
        else:
            missing_str = ", ".join(missing)
            message = f"Compliance Score: {score}/100. Missing: {missing_str}. Please provide this before we can file your claim."
            
        return ComplianceReport(
            compliance_grade=score,
            missing_fields=missing,
            blocking_issues=missing, # In this rule-set, missing fields are blocking
            is_ready_to_file=is_ready,
            message=message
        )
