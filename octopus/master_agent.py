"""
Master Agent - Natural language interface for the Octopus multi-agent system.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from openai import OpenAI, AsyncOpenAI

from octopus.agents.base_agent import BaseAgent
from octopus.router.agents_router import router, register_agent, agent_method
from octopus.config.settings import get_settings


logger = logging.getLogger(__name__)


@register_agent(
    name="master_agent",
    description="Master agent that provides natural language interface and delegates tasks to appropriate sub-agents",
    version="1.0.0",
    tags=["master", "coordinator", "natural_language"]
)
class MasterAgent(BaseAgent):
    """
    Master Agent responsible for:
    1. Providing natural language interface
    2. Agent discovery and selection
    3. Task delegation to appropriate agents
    """
    
    def __init__(self, api_key: str = None, model: str = None, base_url: str = None, **kwargs):
        """
        Initialize the Master Agent.
        
        Args:
            api_key: OpenAI API key (optional, will use settings if not provided)
            model: OpenAI model to use (optional, will use settings if not provided)
            base_url: OpenAI base URL (optional, will use settings if not provided)
            **kwargs: Additional configuration
        """
        super().__init__(name="MasterAgent", description="Natural language interface", **kwargs)
        
        # Get settings
        settings = get_settings()
        
        # Validate model provider
        self.model_provider = settings.model_provider.lower()
        if self.model_provider != "openai":
            raise ValueError(f"Unsupported model provider: {self.model_provider}. Currently only 'openai' is supported.")
        
        # OpenAI setup using settings
        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env file or pass api_key parameter.")
        
        self.model = model or settings.openai_model
        self.base_url = base_url or settings.openai_base_url
        self.deployment = settings.openai_deployment
        self.api_version = settings.openai_api_version
        self.temperature = settings.openai_temperature
        self.max_tokens = settings.openai_max_tokens
        
        # Create client based on provider
        self._initialize_client()
        
        # For Azure OpenAI, use deployment name if available
        self.effective_model = self.deployment if self.deployment else self.model
        
        self.logger.info(f"MasterAgent initialized with provider: {self.model_provider}, model: {self.effective_model}")
        if self.base_url:
            self.logger.info(f"Using {self.model_provider.upper()} base URL: {self.base_url}")
        if self.api_version:
            self.logger.info(f"Using API version: {self.api_version}")
        if self.deployment:
            self.logger.info(f"Using deployment: {self.deployment}")
        self.logger.info(f"{self.model_provider.upper()} settings - Temperature: {self.temperature}, Max tokens: {self.max_tokens}")
    
    def _initialize_client(self):
        """Initialize the appropriate client based on model provider."""
        if self.model_provider == "openai":
            # Create OpenAI client with proper Azure OpenAI configuration
            client_kwargs = {"api_key": self.api_key}
            
            # For Azure OpenAI, construct the full base URL with deployment
            if self.base_url and self.deployment:
                # Azure OpenAI format: https://{resource}.openai.azure.com/openai/deployments/{deployment}/
                base_url = self.base_url.rstrip('/')
                if not base_url.endswith('/openai'):
                    base_url = base_url + '/openai'
                full_url = f"{base_url}/deployments/{self.deployment}/"
                client_kwargs["base_url"] = full_url
            elif self.base_url:
                client_kwargs["base_url"] = self.base_url
                
            if self.api_version:
                client_kwargs["default_query"] = {"api-version": self.api_version}
                
            self.client = OpenAI(**client_kwargs)
            self.async_client = AsyncOpenAI(**client_kwargs)
        else:
            raise ValueError(f"Unsupported model provider: {self.model_provider}")
    
    def initialize(self):
        """Custom initialization."""
        # Discover available agents
        self._discover_agents()
    
    def cleanup(self):
        """Cleanup resources."""
        pass
    
    def _discover_agents(self):
        """Discover and catalog available agents."""
        agents = router.list_agents()
        self.logger.info(f"Discovered {len(agents)} agents:")
        for agent in agents:
            self.logger.info(f"  - {agent['name']}: {agent['description']}")
    
    def _get_agent_capabilities(self) -> List[Dict[str, Any]]:
        """Get detailed capabilities of all available agents."""
        agents = router.list_agents()
        capabilities = []
        
        for agent in agents:
            # Skip self
            if agent['name'] == 'master_agent':
                continue
                
            # Get agent registration to access methods
            agent_registration = router.get_agent(agent['name'])
            if agent_registration and agent_registration.methods:
                # Convert MethodInfo objects to dict for serialization
                methods_dict = {}
                for method_name, method_info in agent_registration.methods.items():
                    methods_dict[method_name] = {
                        'description': method_info.description,
                        'parameters': method_info.parameters,
                        'returns': method_info.returns
                    }
                
                capabilities.append({
                    'name': agent['name'],
                    'description': agent['description'],
                    'methods': methods_dict
                })
        
        return capabilities
    
    @agent_method(
        description="Process natural language request and delegate to appropriate agent",
        parameters={
            "request": {"type": "string", "description": "Natural language request or task"},
            "request_id": {"type": "string", "description": "Unique identifier for this request"}
        },
        returns="string"
    )
    def process_natural_language(self, request: str, request_id: str) -> str:
        """
        Process natural language request and delegate to appropriate agent.
        
        Args:
            request: Natural language request or task
            request_id: Unique identifier for this request
            
        Returns:
            String response from the delegated agent
        """
        self.logger.info(f"Processing natural language request [{request_id}]: {request}")
        
        try:
            # Get available agents and their capabilities
            available_agents = self._get_agent_capabilities()
            
            # Use OpenAI to analyze the request and select the appropriate agent
            agent_selection = self._select_agent_for_request(request, available_agents)
            
            if not agent_selection:
                return f"Sorry, I couldn't find an appropriate agent to handle your request: {request}"
            
            # Execute the selected agent method
            result = self._execute_agent_method(agent_selection)
            
            # Return the result as a string
            if isinstance(result, dict):
                return json.dumps(result, ensure_ascii=False, indent=2)
            else:
                return str(result)
                
        except Exception as e:
            self.logger.error(f"Error processing natural language request [{request_id}]: {str(e)}")
            return f"Sorry, I encountered an error while processing your request: {str(e)}"
    
    def _select_agent_for_request(self, request: str, available_agents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Use OpenAI to select the most appropriate agent for the request."""
        system_prompt = """You are an intelligent agent selector for a multi-agent system.
Given a natural language request, analyze it and select the most appropriate agent and method to handle it.

Available agents and their capabilities:
{agents_info}

Respond in JSON format with the following structure:
{{
    "agent_name": "selected_agent_name",
    "method_name": "selected_method_name",
    "parameters": {{}},
    "confidence": 0.95,
    "reasoning": "explanation of why this agent was selected"
}}

If no suitable agent is found, respond with:
{{
    "agent_name": null,
    "method_name": null,
    "parameters": null,
    "confidence": 0.0,
    "reasoning": "no suitable agent found"
}}"""
        
        user_prompt = f"Request: {request}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.effective_model,
                messages=[
                    {"role": "system", "content": system_prompt.format(agents_info=json.dumps(available_agents, indent=2, ensure_ascii=False))},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            response_text = response.choices[0].message.content
            self.logger.debug(f"OpenAI response text: {response_text}")
            
            # Try to parse the JSON response
            try:
                # Clean the response text (remove extra whitespace)
                clean_response = response_text.strip()
                self.logger.debug(f"Clean response text: {clean_response}")
                
                selection_result = json.loads(clean_response)
                self.logger.debug(f"Parsed JSON: {selection_result}")
                
                # Validate the response structure
                if not isinstance(selection_result, dict):
                    self.logger.error(f"Response is not a dict: {type(selection_result)}")
                    return None
                    
                if "agent_name" not in selection_result:
                    self.logger.error(f"Missing 'agent_name' in response: {selection_result}")
                    return None
                    
                return selection_result
                
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error: {e}")
                self.logger.error(f"Raw response: {repr(response_text)}")
                # Try to find the JSON part if there's extra text
                try:
                    # Look for JSON-like structure in the response
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    if start_idx != -1 and end_idx != -1:
                        json_part = response_text[start_idx:end_idx]
                        self.logger.debug(f"Extracted JSON part: {json_part}")
                        selection_result = json.loads(json_part)
                        return selection_result
                except:
                    pass
                return None
                
        except Exception as e:
            self.logger.error(f"Error in agent selection: {e}")
            return None
    
    def _execute_agent_method(self, agent_selection: Dict[str, Any]) -> Any:
        """Execute the selected agent method."""
        agent_name = agent_selection['agent_name']
        method_name = agent_selection['method_name']
        parameters = agent_selection.get('parameters', {})
        
        self.logger.info(f"Executing {agent_name}.{method_name} with parameters: {parameters}")
        
        try:
            # Call the agent method through the router
            result = router.execute_agent_method(agent_name, method_name, parameters)
            
            self.logger.info(f"Agent execution completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing agent method: {str(e)}")
            raise
    
    @agent_method(
        description="Get current status of the master agent",
        parameters={},
        returns="dict"
    )
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the master agent."""
        available_agents = self._get_agent_capabilities()
        
        return {
            "name": "MasterAgent",
            "status": "active",
            "model": self.effective_model,
            "model_provider": self.model_provider,
            "available_agents": len(available_agents),
            "agents": [agent['name'] for agent in available_agents],
            "timestamp": datetime.now().isoformat()
        }
