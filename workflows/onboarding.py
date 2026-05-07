ONBOARDING_QUESTIONS = [
    {
        "field": "preferred_language",
        "question": "Namaste. I'm GhostWriter. I'm here to help your family claim everything you're legally owed. What language would you like to talk in?",
        "type": "button",
        "options": ["Telugu", "Hindi", "English", "Tamil", "Kannada"]
    },
    {
        "field": "breadwinner_name", 
        "question": "I'm so sorry for your loss. What was the name of the person who passed away?",
        "type": "text",
        "sensitive": True  # Use softer tone
    },
    {
        "field": "date_of_death",
        "question": "When did they pass away? (DD/MM/YYYY)",
        "type": "date"
    },
    {
        "field": "employment_type",
        "question": "What kind of work did they do?",
        "type": "button", 
        "options": ["Government job", "Private company", "Own business", "Daily wage work"]
    },
    {
        "field": "had_epf",
        "question": "Did they have an EPF (Provident Fund) account through their employer?",
        "type": "button",
        "options": ["Yes", "Not sure", "No"]
    },
    {
        "field": "state",
        "question": "Which state are you in?",
        "type": "button",
        "options": ["Telangana", "Andhra Pradesh", "Maharashtra", "Karnataka", "Other"]
    }
]

class OnboardingWorkflow:
    def __init__(self, whatsapp_service, sarvam_service):
        self.whatsapp = whatsapp_service
        self.sarvam = sarvam_service

    async def get_next_question(self, current_state: dict) -> dict:
        """
        Determine next question based on current state dictionary
        """
        for q in ONBOARDING_QUESTIONS:
            if q["field"] not in current_state:
                return q
        return None
