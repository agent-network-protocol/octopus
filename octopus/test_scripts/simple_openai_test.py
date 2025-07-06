#!/usr/bin/env python3
"""
Simple OpenAI test to verify connection and response.
"""

import json
from openai import OpenAI
from octopus.config.settings import get_settings
from octopus.utils.log_base import setup_enhanced_logging

# Setup logging
logger = setup_enhanced_logging()

def main():
    """Simple OpenAI test."""
    try:
        # Get settings
        settings = get_settings()
        
        # Create OpenAI client
        client_kwargs = {"api_key": settings.openai_api_key}
        
        # For Azure OpenAI, construct the full base URL with deployment
        if settings.openai_base_url and settings.openai_deployment:
            # Azure OpenAI format: https://{resource}.openai.azure.com/openai/deployments/{deployment}/
            base_url = settings.openai_base_url.rstrip('/')
            if not base_url.endswith('/openai'):
                base_url = base_url + '/openai'
            full_url = f"{base_url}/deployments/{settings.openai_deployment}/"
            client_kwargs["base_url"] = full_url
        elif settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
            
        if settings.openai_api_version:
            client_kwargs["default_query"] = {"api-version": settings.openai_api_version}
            
        client = OpenAI(**client_kwargs)
        
        # Use deployment name if available, otherwise use model name
        effective_model = settings.openai_deployment if settings.openai_deployment else settings.openai_model
        
        print(f"Using model: {effective_model}")
        print(f"Using base URL: {settings.openai_base_url}")
        if settings.openai_api_version:
            print(f"Using API version: {settings.openai_api_version}")
        if settings.openai_deployment:
            print(f"Using deployment: {settings.openai_deployment}")
        
        # Show the actual URL being used
        if "base_url" in client_kwargs:
            print(f"Constructed URL: {client_kwargs['base_url']}")
        
        # Simple test
        simple_prompt = "Return a JSON object with 'test': 'success'"
        
        print(f"\nTesting simple request: {simple_prompt}")
        
        response = client.chat.completions.create(
            model=effective_model,
            messages=[
                {"role": "user", "content": simple_prompt}
            ],
            temperature=0.1,
            max_tokens=100
        )
        
        content = response.choices[0].message.content
        print(f"Response content: {repr(content)}")
        
        # Test with JSON object format
        print("\nTesting JSON object format...")
        
        response2 = client.chat.completions.create(
            model=effective_model,
            messages=[
                {"role": "user", "content": "Return a JSON object with 'agent_name': 'test_agent', 'method_name': 'test_method', 'confidence': 0.9"}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=100
        )
        
        content2 = response2.choices[0].message.content
        print(f"JSON response content: {repr(content2)}")
        
        # Test parsing
        try:
            parsed = json.loads(content2)
            print(f"Parsed JSON: {parsed}")
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
        
    except Exception as e:
        logger.error(f"Error in simple OpenAI test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 