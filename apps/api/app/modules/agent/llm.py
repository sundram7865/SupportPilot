import json
import re
from typing import Any

import google.generativeai as genai

from app.core.config import get_settings


class LLMClient:
    def generate_json(
        self,
        prompt: str,
        fallback: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        settings = get_settings()

        if settings.ai_provider.lower() == "gemini":
            try:
                return self._generate_gemini_json(prompt)
            except Exception:
                if fallback is not None:
                    return fallback
                raise

        return self._generate_mock_json(prompt)

    def generate_text(
        self,
        prompt: str,
        fallback: str | None = None,
    ) -> str:
        settings = get_settings()

        if settings.ai_provider.lower() == "gemini":
            try:
                return self._generate_gemini_text(prompt)
            except Exception:
                if fallback is not None:
                    return fallback
                raise

        return self._generate_mock_text(prompt)

    def _get_gemini_model(self):
        settings = get_settings()

        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini")

        genai.configure(api_key=settings.gemini_api_key)

        return genai.GenerativeModel(
            model_name=settings.gemini_model,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            },
        )

    def _generate_gemini_text(self, prompt: str) -> str:
        model = self._get_gemini_model()
        response = model.generate_content(prompt)

        text = getattr(response, "text", None)

        if not text:
            raise ValueError("Gemini returned empty response.")

        return text.strip()

    def _generate_gemini_json(self, prompt: str) -> dict[str, Any]:
        model = self._get_gemini_model()

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            },
        )

        text = getattr(response, "text", None)

        if not text:
            raise ValueError("Gemini returned empty JSON response.")

        return self._parse_json_from_text(text)

    def _parse_json_from_text(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()

        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"\{[\s\S]*\}", cleaned)

        if not json_match:
            raise ValueError(f"No JSON object found in LLM response: {text[:500]}")

        candidate = json_match.group(0)

        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Failed to parse JSON from LLM response: {candidate[:500]}"
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError("LLM JSON response must be an object.")

        return parsed

    def _generate_mock_json(self, prompt: str) -> dict[str, Any]:
        lower_prompt = prompt.lower()

        if "classify" in lower_prompt:
            if (
                "consumer court" in lower_prompt
                or "legal" in lower_prompt
                or "court" in lower_prompt
                or "lawyer" in lower_prompt
                or "complaint" in lower_prompt
            ):
                return {
                    "category": "LEGAL_RISK",
                    "priority": "URGENT",
                    "confidence": 0.95,
                    "summary": "Customer message has legal or escalation risk.",
                }

            if (
                "payment" in lower_prompt
                or "refund" in lower_prompt
                or "deducted" in lower_prompt
                or "money" in lower_prompt
            ):
                return {
                    "category": "PAYMENT_ISSUE",
                    "priority": "HIGH",
                    "confidence": 0.9,
                    "summary": "Customer has a payment or refund related issue.",
                }

            if (
                "delivery" in lower_prompt
                or "shipment" in lower_prompt
                or "where is my order" in lower_prompt
                or "tracking" in lower_prompt
            ):
                return {
                    "category": "ORDER_STATUS",
                    "priority": "MEDIUM",
                    "confidence": 0.9,
                    "summary": "Customer is asking about order or delivery status.",
                }

            return {
                "category": "OTHER",
                "priority": "MEDIUM",
                "confidence": 0.75,
                "summary": "General customer support request.",
            }

        if "detecting risk" in lower_prompt or "risk_level" in lower_prompt:
            if (
                "consumer court" in lower_prompt
                or "legal" in lower_prompt
                or "court" in lower_prompt
                or "lawyer" in lower_prompt
            ):
                return {
                    "risk_level": "CRITICAL",
                    "risk_reasons": ["Customer mentioned legal/court escalation."],
                }

            if (
                "refund" in lower_prompt
                or "payment" in lower_prompt
                or "deducted" in lower_prompt
            ):
                return {
                    "risk_level": "HIGH",
                    "risk_reasons": ["Money-related ticket may require approval."],
                }

            return {
                "risk_level": "LOW",
                "risk_reasons": [],
            }

        if "automation decision" in lower_prompt or "decision" in lower_prompt:
            if "critical" in lower_prompt or "legal_risk" in lower_prompt:
                return {
                    "decision": "ESCALATE_TO_MANAGER",
                    "reasoning_summary": "Legal or critical risk should be escalated.",
                }

            if "high" in lower_prompt or "refund" in lower_prompt or "payment" in lower_prompt:
                return {
                    "decision": "NEEDS_HUMAN_APPROVAL",
                    "reasoning_summary": "Money-related or high-risk action requires approval.",
                }

            return {
                "decision": "AUTO_REPLY_DRAFT",
                "reasoning_summary": "Low-risk ticket can receive a drafted response.",
            }

        return {}

    def _generate_mock_text(self, prompt: str) -> str:
        lower_prompt = prompt.lower()

        if "payment" in lower_prompt or "refund" in lower_prompt or "deducted" in lower_prompt:
            return (
                "Hi, thanks for reaching out. I understand that your payment-related "
                "issue needs attention. We will verify the payment and order details. "
                "If a refund is applicable, it will be processed only after the required "
                "review and approval."
            )

        if "where is my order" in lower_prompt or "delivery" in lower_prompt or "shipment" in lower_prompt:
            return (
                "Hi, thanks for contacting UrbanKart support. We are checking the latest "
                "shipment status for your order and will share an update shortly."
            )

        if "legal" in lower_prompt or "court" in lower_prompt or "consumer forum" in lower_prompt:
            return (
                "Thank you for sharing your concern. We are escalating this to our internal "
                "support team for careful review. A team member will get back to you soon."
            )

        return (
            "Hi, thanks for contacting UrbanKart support. We have received your request "
            "and our team will help you shortly."
        )