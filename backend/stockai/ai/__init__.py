"""AI layer: provider abstraction, prompts, schemas, caching service.

AIService -> AIProvider -> concrete provider (Mock now; OpenAI/Anthropic/Gemini
addable later). The rest of the app never imports a concrete provider directly.
"""
