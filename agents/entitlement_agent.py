import json
import os
import datetime
from typing import List, Dict, Any
from pydantic import BaseModel

class SchemeEntitlement(BaseModel):
    name: str
    amount: float
    deadline: str
    days_remaining: int
    required_documents: List[str]
    epfo_office: str = None
    priority: str

class EntitlementReport(BaseModel):
    total_entitlement: float
    schemes: List[SchemeEntitlement]

class EntitlementAgent:
    def __init__(self, gemini_service, sarvam_service):
        self.gemini = gemini_service
        self.sarvam = sarvam_service

    async def discover_entitlements(self, family_data: dict) -> EntitlementReport:
        """
        Input: Dictionary of family data collected from onboarding.
        Output: List of every scheme with amount, deadline, required documents.
        Reads from data/schemes JSON files.
        """
        schemes = []
        total_amount = 0.0
        
        # Load JSON files
        base_dir = os.path.dirname(os.path.dirname(__file__))
        central_path = os.path.join(base_dir, "data", "schemes", "central_schemes.json")
        
        with open(central_path, "r") as f:
            central_schemes = json.load(f).get("schemes", [])
            
        emp_type = family_data.get("employment_type", "").lower()
        had_epf = family_data.get("had_epf", "").lower() == "yes"
        state = family_data.get("state", "").lower()

        for scheme in central_schemes:
            name = scheme.get("name")
            eligibility = scheme.get("eligibility", {})
            
            is_eligible = False
            amount = 0.0
            docs = ["death_certificate", "aadhaar", "passbook"]
            
            if name == "EPF Form 20":
                if had_epf or "government" in emp_type or "private" in emp_type:
                    is_eligible = True
                    amount = 450000.0  # Mock calculation
                    
            elif name == "PMJJBY":
                # Assuming everyone with a bank account (which we assume they have if they have Aadhaar/EPF)
                is_eligible = True
                amount = float(scheme.get("amount_flat", 200000))
                docs.append("pmjjby_policy_number")
                
            elif name == "EDLI":
                if had_epf or "government" in emp_type or "private" in emp_type:
                    is_eligible = True
                    amount = 700000.0  # Mock calculation
                    
            if is_eligible:
                days_left = scheme.get("deadline_days", 30)
                deadline_date = (datetime.date.today() + datetime.timedelta(days=days_left)).isoformat()
                
                schemes.append(SchemeEntitlement(
                    name=name,
                    amount=amount,
                    deadline=deadline_date,
                    days_remaining=days_left,
                    required_documents=docs,
                    priority="URGENT" if days_left <= 30 else "HIGH"
                ))
                total_amount += amount

        # State Schemes
        if state == "telangana":
            state_path = os.path.join(base_dir, "data", "schemes", "state_schemes", "telangana.json")
            if os.path.exists(state_path):
                with open(state_path, "r") as f:
                    state_data = json.load(f)
                    for scheme in state_data.get("schemes", []):
                        if scheme.get("name") == "Aasara Pension":
                            # Monthly pension, let's value it at 1 year for total entitlement mock or just a monthly addition
                            amount = float(scheme.get("amount_monthly", 2016)) * 12
                            days_left = scheme.get("deadline_days", 90)
                            deadline_date = (datetime.date.today() + datetime.timedelta(days=days_left)).isoformat()
                            
                            schemes.append(SchemeEntitlement(
                                name=scheme.get("name"),
                                amount=amount,
                                deadline=deadline_date,
                                days_remaining=days_left,
                                required_documents=scheme.get("required_documents", []),
                                priority="MEDIUM"
                            ))
                            total_amount += amount

        return EntitlementReport(total_entitlement=total_amount, schemes=schemes)

    async def generate_one_number_message(self, report: EntitlementReport, language: str) -> str:
        """
        Generates: "You are entitled to ₹X across Y schemes..."
        """
        count = len(report.schemes)
        
        # English message
        english_msg = f"You are entitled to ₹{report.total_entitlement:,.0f} across {count} schemes. You have currently claimed ₹0. Let's fix that."
        
        # Optionally translate
        if language and language.lower() not in ["english", "english (default)"]:
            translated = await self.sarvam.translate(english_msg, "English", language)
            return translated
        
        return english_msg
