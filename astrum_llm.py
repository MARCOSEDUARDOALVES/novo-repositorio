"""
astrum_llm.py
Cadeia LLM para ASTRUM: Groq (rapido/free) -> OpenRouter -> Gemini (fallback).
"""

from __future__ import annotations

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY       = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "")

# Modelos em ordem de preferencia
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
]

OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct",
    "google/gemini-2.0-flash-001",
    "anthropic/claude-3-haiku",
]

GEMINI_MODEL = "gemini-2.0-flash"


async def generate(
    prompt: str,
    system: str = "",
    temperature: float = 0.75,
    max_tokens: int = 4096,
) -> str:
    """
    Gera texto passando pela cadeia:
    Groq (free, rapido) -> OpenRouter -> Gemini direto
    """
    # 1. Tentar Groq
    if GROQ_API_KEY:
        for model in GROQ_MODELS:
            try:
                result = await _call_groq(prompt, system, temperature, max_tokens, model)
                if result:
                    return result
            except Exception as e:
                print(f"[llm] Groq {model} falhou: {e}")

    # 2. Tentar OpenRouter
    if OPENROUTER_API_KEY:
        for model in OPENROUTER_MODELS:
            try:
                result = await _call_openrouter(prompt, system, temperature, max_tokens, model)
                if result:
                    return result
            except Exception as e:
                print(f"[llm] OpenRouter {model} falhou: {e}")

    # 3. Gemini direto (fallback final)
    if GEMINI_API_KEY:
        return await _call_gemini(prompt, system, temperature, max_tokens)

    raise RuntimeError(
        "[llm] Nenhum provedor disponivel. Configure GROQ_API_KEY ou GEMINI_API_KEY."
    )


async def _call_groq(
    prompt: str,
    system: str,
    temperature: float,
    max_tokens: int,
    model: str,
) -> str:
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_openrouter(
    prompt: str,
    system: str,
    temperature: float,
    max_tokens: int,
    model: str,
) -> str:
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://astrum-portal.web.app",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_gemini(
    prompt: str,
    system: str,
    temperature: float,
    max_tokens: int,
) -> str:
    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return _sanitize(text)


def _sanitize(text: str) -> str:
    """Remove caracteres de controle e garante UTF-8 limpo."""
    if not text:
        return ""
    return "".join(c for c in text if ord(c) >= 32 or c in "\n\r\t")
