import requests
import json
from typing import List, Dict
from models import ClassifiedItem
from config import cfg

class AIClient:
    def __init__(self):
        pass

    def _get_api_config(self):
        mode = cfg.llm_mode
        if mode == "cloud":
            return cfg.cloud_config
        elif mode == "local":
            return cfg.local_config
        return None

    def _send_request(self, system_prompt: str, user_prompt: str) -> str:
        mode = cfg.llm_mode
        if mode == "none":
            return "AI Mode is disabled. Please enable it in Settings to get advice."

        conf = self._get_api_config()
        if not conf:
            return "Configuration Error: No AI settings found."

        model = conf.get("model", "gpt-4o-mini")
        
        # Prepare headers and payload usually compatible with OpenAI/Ollama Chat Completions
        headers = {
            "Content-Type": "application/json"
        }
        
        url = ""
        
        if mode == "cloud":
            api_key = conf.get("api_key", "")
            if not api_key or "YOUR_KEY" in api_key:
                 return "Missing API Key. Please configure it in Settings."
            headers["Authorization"] = f"Bearer {api_key}"
            
            # OpenAI Default
            if conf.get("provider", "openai") == "openai":
                url = "https://api.openai.com/v1/chat/completions"
            # Google Gemini (OpenAI compat or specialized - let's stick to OpenAI compat for now or generic HTTP)
            # Simplification: Assume OpenAI compatible for "cloud" generic or adjust logic.
        
        elif mode == "local":
            url = conf.get("base_url", "http://localhost:11434/v1/chat/completions")
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"AI Error {resp.status_code}: {resp.text}"
        except Exception as e:
            return f"Connection Failed: {e}"

    def explain_risks(self, item: ClassifiedItem) -> str:
        """Ask AI to explain why an item is risky or safe."""
        # Anonymize path
        safe_path = item.item.path if "Users" not in item.item.path else "User Profile Data"
        
        sys_prompt = (
            "You are a Windows System Expert. "
            "Explain clearly but briefly why moving this folder might be safe or risky. "
            "Do not instruct the user to execute commands. Just explain."
        )
        user_prompt = (
            f"App Name: {item.item.name}\n"
            f"Type: {item.item.type}\n"
            f"Classification: {item.category}\n"
            f"Reason: {item.reason}\n\n"
            "Why is this classified this way?"
        )
        return self._send_request(sys_prompt, user_prompt)

    def suggest_optimization(self, items: List[ClassifiedItem]) -> str:
        """Suggest which items to move."""
        # Filter for top 10 biggest SAFE items to save tokens
        safe_items = [x for x in items if x.category == "SAFE"]
        safe_items.sort(key=lambda x: x.item.size_gb, reverse=True)
        top_items = safe_items[:10]
        
        item_list_str = "\n".join([
            f"- {i.item.name} ({i.item.size_gb} GB)" for i in top_items
        ])
        
        if not item_list_str:
            return "No SAFE items found to analyze."

        sys_prompt = (
            "You are a helpful Storage Assistant. "
            "Passively advice the user on which folders are better to move to a secondary drive to save space on C:. "
            "Prioritize games and cache folders."
        )
        user_prompt = (
            "Here are the largest safe-to-move items found:\n"
            f"{item_list_str}\n\n"
            "Which 3 would you recommend moving first and why?"
        )
        return self._send_request(sys_prompt, user_prompt)

ai_client = AIClient()
