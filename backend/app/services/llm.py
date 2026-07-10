from __future__ import annotations

import httpx

from ..config import get_settings


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def explain_validation(self, validation: dict) -> list[str]:
        fallback = validation.get("missing_questions") or validation.get("errors")[:5]
        if not self.settings.openai_compat_api_key:
            return fallback
        prompt = (
            "你是频谱规划助手。请把以下校验结果改写成用户可执行的补充问题，"
            "不要编造规则，不要要求用户提供已经存在的数据。\n"
            f"{_safe_summary(validation)}"
        )
        content = await self._chat(prompt)
        return [line.strip("- 1234567890.、") for line in content.splitlines() if line.strip()] or fallback

    async def explain_plan(self, summary: dict, risk_items: list[dict]) -> str:
        fallback = _fallback_plan_explanation(summary, risk_items)
        if not self.settings.openai_compat_api_key:
            return fallback
        prompt = (
            "你是频谱规划助手。根据脱敏规划摘要解释结果。"
            "强调频率由确定性优化器生成，合规和干扰由工具箱计算。不要输出台站经纬度。\n"
            f"摘要：{summary}\n风险项前五条：{risk_items[:5]}"
        )
        return await self._chat(prompt) or fallback

    async def _chat(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.settings.openai_compat_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.openai_compat_model,
            "messages": [
                {"role": "system", "content": "你只解释确定性工具结果，不直接决定频率。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self.settings.openai_compat_base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()


def _safe_summary(data: dict) -> dict:
    return {
        "ok": data.get("ok"),
        "errors": data.get("errors", [])[:20],
        "warnings": data.get("warnings", [])[:20],
        "summary": data.get("summary", {}),
    }


def _fallback_plan_explanation(summary: dict, risk_items: list[dict]) -> str:
    high = summary.get("high_risk_count", 0)
    medium = summary.get("medium_risk_count", 0)
    if not risk_items:
        return "确定性优化器已完成频率分配，当前方案未发现明显同频、邻频或近距离高功率风险。"
    return f"确定性优化器已完成频率分配，检测到 {high} 项高风险和 {medium} 项中风险。请优先查看风险明细中的同频、邻频和保护距离说明。"
