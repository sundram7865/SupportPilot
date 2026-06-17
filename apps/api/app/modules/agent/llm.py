import json
import re
from typing import Any

import google.generativeai as genai

from app.core.config import get_settings


class LLMClient:
    def generate_json(self, prompt: str) -> dict[str, Any]:
        settings = get_settings()

        if settings.ai_provider.lower() == "gemini":
            return self._generate_gemini_json(prompt)

        return self._generate_mock_json(prompt)

    def generate_text(self, prompt: str) -> str:
        settings = get_settings()

        if settings.ai_provider.lower() == "gemini":
            return self._generate_gemini_text(prompt)

        return self._generate_mock_text(prompt)

    def _generate_gemini_text(self, prompt: str) -> str:
        settings = get_settings()

        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini")

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        response = model.generate_content(prompt)

        return response.text or ""

    def _generate_gemini_json(self, prompt: str) -> dict[str, Any]:
        text = self._generate_gemini_text(prompt)
        return self._parse_json_from_text(text)

    def _parse_json_from_text(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```json", "", cleaned)
            cleaned = re.sub(r"^```", "", cleaned)
            cleaned = re.sub(r"```$", "", cleaned)
            cleaned = cleaned.strip()

        return json.loads(cleaned)

    def _generate_mock_json(self, prompt: str) -> dict[str, Any]:
        lower_prompt = prompt.lower()

        if "classify" in lower_prompt:
            if "payment" in lower_prompt or "refund" in lower_prompt or "deducted" in lower_prompt:
                return {
                    "category": "PAYMENT_ISSUE",
                    "priority": "HIGH",
                    "summary": "Customer has a payment or refund related issue.",
                }

            if "delivery" in lower_prompt or "shipment" in lower_prompt or "where is my order" in lower_prompt:
                return {
                    "category": "ORDER_STATUS",
                    "priority": "MEDIUM",
                    "summary": "Customer is asking about order or delivery status.",
                }

            if "legal" in lower_prompt or "court" in lower_prompt or "consumer forum" in lower_prompt:
                return {
                    "category": "LEGAL_RISK",
                    "priority": "URGENT",
                    "summary": "Customer message has legal escalation risk.",
                }

            return {
                "category": "OTHER",
                "priority": "MEDIUM",
                "summary": "General customer support request.",
            }

        if "risk" in lower_prompt:
            if "legal" in lower_prompt or "court" in lower_prompt or "consumer forum" in lower_prompt:
                return {
                    "risk_level": "CRITICAL",
                    "risk_reasons": ["Customer mentioned legal/court/consumer forum."],
                }

            if "refund" in lower_prompt and ("1000" in lower_prompt or "above" in lower_prompt):
                return {
                    "risk_level": "HIGH",
                    "risk_reasons": ["Refund may require approval based on amount or policy."],
                }

            return {
                "risk_level": "LOW",
                "risk_reasons": [],
            }

        if "decision" in lower_prompt:
            if "critical" in lower_prompt or "legal_risk" in lower_prompt:
                return {
                    "decision": "ESCALATE_TO_MANAGER",
                    "reasoning_summary": "High-risk or legal-risk ticket should be escalated.",
                }

            if "high" in lower_prompt and "refund" in lower_prompt:
                return {
                    "decision": "NEEDS_HUMAN_APPROVAL",
                    "reasoning_summary": "Refund or payment issue may require manager approval.",
                }

            return {
                "decision": "AUTO_REPLY_DRAFT",
                "reasoning_summary": "Low-risk ticket can receive a drafted response for review.",
            }

        return {}

    def _generate_mock_text(self, prompt: str) -> str:
        lower_prompt = prompt.lower()

        if "draft" in lower_prompt:
            if "payment" in lower_prompt or "refund" in lower_prompt or "deducted" in lower_prompt:
                return (
                    "Hi, thanks for reaching out. I understand that your payment was deducted "
                    "but the order was not created. We will verify the payment and order status. "
                    "If the payment is confirmed and no order exists, we will proceed according "
                    "to UrbanKart's refund policy. Refunds may take 5 to 7 business days after approval."
                )

            if "where is my order" in lower_prompt or "delivery" in lower_prompt or "shipment" in lower_prompt:
                return (
                    "Hi, thanks for contacting UrbanKart support. I will check the latest shipment "
                    "status for your order and share the delivery update with you shortly."
                )

            if "legal" in lower_prompt or "court" in lower_prompt or "consumer forum" in lower_prompt:
                return (
                    "Thank you for sharing your concern. We are escalating this to our internal "
                    "support team for careful review. A team member will get back to you soon."
                )

            return (
                "Hi, thanks for contacting UrbanKart support. We have received your request "
                "and our team will help you with this shortly."
            )

        return "Mock LLM response."