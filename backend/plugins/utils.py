"""
Shared utility functions for plugins
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def call_llm_for_json(
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int = 4096,
    operation_name: str = "LLM operation"
) -> Any:
    """
    Shared utility to call LLM and get JSON response
    
    Args:
        api_key: Anthropic API key
        model: Model name (e.g., "claude-sonnet-4-5-20250929")
        prompt: The prompt to send
        max_tokens: Max tokens for response
        operation_name: Name for logging purposes
    
    Returns:
        Parsed JSON response
    
    Raises:
        Exception if API call fails or JSON parsing fails
    """
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract the response text
        response_text = response.content[0].text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            if len(lines) > 2:
                response_text = "\n".join(lines[1:-1])
        
        # Parse and return JSON
        result = json.loads(response_text)
        logger.info(f"✨ {operation_name} completed successfully")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ {operation_name} - JSON parsing error: {e}")
        logger.error(f"Response text: {response_text[:200]}...")
        raise
    except Exception as e:
        logger.error(f"❌ {operation_name} - API call failed: {e}")
        raise
