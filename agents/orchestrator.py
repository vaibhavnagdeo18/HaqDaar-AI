import logging

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, entitlement_agent, form_agent, dispute_agent, tracker_agent, whatsapp_service, sarvam_service):
        self.entitlement_agent = entitlement_agent
        self.form_agent = form_agent
        self.dispute_agent = dispute_agent
        self.tracker_agent = tracker_agent
        self.whatsapp = whatsapp_service
        self.sarvam = sarvam_service

    async def route_message(self, message_data: dict):
        """
        Main entry point for incoming WhatsApp messages.
        Determine session state and route to appropriate workflow/agent.
        """
        logger.info(f"Routing message: {message_data}")
        # Note: Implement state machine routing here
