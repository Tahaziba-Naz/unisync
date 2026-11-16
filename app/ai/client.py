import os, requests

class LLMError(RuntimeError): pass

def configured(): return bool(os.getenv("LLM_API_KEY") and os.getenv("LLM_MODEL") and os.getenv("LLM_BASE_URL"))

def complete(system_prompt, payload):
    key, model, base = os.getenv("LLM_API_KEY"), os.getenv("LLM_MODEL"), os.getenv("LLM_BASE_URL")
    if not key or not model or not base:
        raise LLMError("LLM is not configured. Set LLM_API_KEY, LLM_MODEL, and LLM_BASE_URL.")
    try:
        response = requests.post(base.rstrip("/") + "/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": model, "temperature": 0, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": payload}]}, timeout=45)
    except requests.Timeout as exc: raise LLMError("LLM request timed out.") from exc
    except requests.RequestException as exc: raise LLMError(f"LLM request failed: {exc.__class__.__name__}.") from exc
    if response.status_code in (401, 403): raise LLMError("LLM authentication failed; verify the configured API key.")
    if response.status_code == 429: raise LLMError("LLM rate limit reached; retry later.")
    if not response.ok: raise LLMError(f"LLM service returned HTTP {response.status_code}.")
    try: return response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc: raise LLMError("LLM returned an invalid response.") from exc
