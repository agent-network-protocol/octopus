"""
Master Agent - Core orchestrator for the Octopus multi-agent system.
"""

import logging
import json
import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI, AsyncOpenAI

from octopus.agents.base_agent import BaseAgent
from octopus.router.agents_router import router, register_agent, agent_method
from octopus.config.settings import get_settings


logger = logging.getLogger(__name__)


@register_agent(
    name="master_agent",
    description="Master orchestrator agent that coordinates task execution across multiple sub-agents",
    version="1.0.0",
    tags=["orchestrator", "master", "coordinator"]
)
class MasterAgent(BaseAgent):
    """
    Master Agent responsible for:
    1. Task reception and analysis
    2. Sub-agent discovery and capability matching
    3. Task decomposition and delegation
    4. Result aggregation and synthesis
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
        super().__init__(name="MasterAgent", description="Task orchestrator", **kwargs)
        
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
        self.temperature = settings.openai_temperature
        self.max_tokens = settings.openai_max_tokens
        
        # Create client based on provider
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize the appropriate client based on model provider."""
        if self.model_provider == "openai":
            # Create OpenAI client with optional base_url
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
                
            self.client = OpenAI(**client_kwargs)
            self.async_client = AsyncOpenAI(**client_kwargs)
        else:
            raise ValueError(f"Unsupported model provider: {self.model_provider}")
        
        # Executor for parallel tasks
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # Task history
        self.task_history = []
        
        self.logger.info(f"MasterAgent initialized with provider: {self.model_provider}, model: {self.model}")
        if self.base_url:
            self.logger.info(f"Using {self.model_provider.upper()} base URL: {self.base_url}")
        self.logger.info(f"{self.model_provider.upper()} settings - Temperature: {self.temperature}, Max tokens: {self.max_tokens}")
    
    def initialize(self):
        """Custom initialization."""
        # Discover available agents
        self._discover_agents()
    
    def cleanup(self):
        """Cleanup resources."""
        self.executor.shutdown(wait=True)
    
    def _discover_agents(self):
        """Discover and catalog available agents."""
        agents = router.list_agents()
        self.logger.info(f"Discovered {len(agents)} agents:")
        for agent in agents:
            self.logger.info(f"  - {agent['name']}: {agent['description']}")
    
    @agent_method(
        description="Process a task by analyzing requirements and delegating to appropriate sub-agents",
        parameters={
            "task": {"type": "string", "description": "Task description or request"},
            "context": {"type": "dict", "description": "Additional context for task execution", "required": False}
        },
        returns="dict"
    )
    def process_task(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a task by analyzing it and delegating to appropriate sub-agents.
        
        Args:
            task: Task description
            context: Additional context
            
        Returns:
            Task execution results
        """
        self.logger.info(f"Processing task: {task}")
        
        try:
            # Step 1: Analyze task
            task_analysis = self._analyze_task(task, context)
            
            # Step 2: Create execution plan
            execution_plan = self._create_execution_plan(task_analysis)
            
            # Step 3: Execute plan
            results = self._execute_plan(execution_plan)
            
            # Step 4: Synthesize results
            final_result = self._synthesize_results(task, results)
            
            # Record task history
            self._record_task(task, task_analysis, execution_plan, final_result)
            
            return {
                "status": "success",
                "task": task,
                "analysis": task_analysis,
                "execution_plan": execution_plan,
                "results": final_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing task: {str(e)}")
            return {
                "status": "error",
                "task": task,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _analyze_task(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze the task using OpenAI to understand requirements."""
        # Get available agents and their capabilities
        available_agents = self._get_agent_capabilities()
        
        system_prompt = """You are a task analyzer for a multi-agent system. 
Analyze the given task and determine:
1. The main objective
2. Required capabilities
3. Subtasks that need to be performed
4. Which agents from the available list should be used
5. Dependencies between subtasks

Available agents and their capabilities:
{agents_info}

Respond in JSON format with the following structure:
{
    "objective": "main objective",
    "required_capabilities": ["capability1", "capability2"],
    "subtasks": [
        {
            "id": "subtask1",
            "description": "subtask description",
            "agent": "agent_name",
            "method": "method_name",
            "parameters": {},
            "dependencies": []
        }
    ],
    "expected_output": "description of expected output"
}"""
        
        user_prompt = f"Task: {task}"
        if context:
            user_prompt += f"\nContext: {json.dumps(context)}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt.format(agents_info=json.dumps(available_agents, indent=2))},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            analysis = json.loads(response.choices[0].message.content)
            self.logger.info(f"Task analysis completed: {analysis['objective']}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing task: {str(e)}")
            # Fallback analysis
            return {
                "objective": task,
                "required_capabilities": [],
                "subtasks": [],
                "expected_output": "Task completion"
            }
    
    def _get_agent_capabilities(self) -> List[Dict[str, Any]]:
        """Get capabilities of all available agents."""
        capabilities = []
        
        for agent_info in router.list_agents():
            if agent_info["name"] == "master_agent":
                continue  # Skip self
            
            agent_schema = router.get_agent_schema(agent_info["name"])
            if agent_schema:
                capabilities.append({
                    "agent": agent_info["name"],
                    "description": agent_info["description"],
                    "methods": [
                        {
                            "name": func["function"]["name"].split(".")[-1],
                            "description": func["function"]["description"],
                            "parameters": func["function"]["parameters"]
                        }
                        for func in agent_schema["functions"]
                    ]
                })
        
        return capabilities
    
    def _create_execution_plan(self, task_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create an execution plan based on task analysis."""
        plan = []
        
        # Validate and prepare subtasks
        for subtask in task_analysis.get("subtasks", []):
            # Verify agent exists
            if not router.get_agent(subtask["agent"]):
                self.logger.warning(f"Agent '{subtask['agent']}' not found, skipping subtask")
                continue
            
            plan.append({
                "id": subtask["id"],
                "description": subtask["description"],
                "agent": subtask["agent"],
                "method": subtask["method"],
                "parameters": subtask.get("parameters", {}),
                "dependencies": subtask.get("dependencies", []),
                "status": "pending"
            })
        
        # Sort by dependencies
        plan = self._topological_sort(plan)
        
        self.logger.info(f"Created execution plan with {len(plan)} steps")
        return plan
    
    def _topological_sort(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort tasks based on dependencies."""
        # Create task map
        task_map = {task["id"]: task for task in tasks}
        
        # Find tasks with no dependencies
        no_deps = [task for task in tasks if not task["dependencies"]]
        sorted_tasks = []
        
        while no_deps:
            # Take a task with no dependencies
            current = no_deps.pop(0)
            sorted_tasks.append(current)
            
            # Check if any other tasks depend on this one
            for task in tasks:
                if current["id"] in task["dependencies"]:
                    task["dependencies"].remove(current["id"])
                    if not task["dependencies"]:
                        no_deps.append(task)
        
        # Check for circular dependencies
        if len(sorted_tasks) != len(tasks):
            self.logger.warning("Circular dependencies detected, using original order")
            return tasks
        
        return sorted_tasks
    
    def _execute_plan(self, execution_plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute the plan by calling appropriate agents."""
        results = {}
        completed_tasks = set()
        
        for step in execution_plan:
            try:
                # Wait for dependencies
                while not all(dep in completed_tasks for dep in step["dependencies"]):
                    self.logger.debug(f"Waiting for dependencies for task {step['id']}")
                    import time
                    time.sleep(0.1)
                
                self.logger.info(f"Executing step: {step['id']} - {step['description']}")
                
                # Execute agent method
                result = router.execute_agent_method(
                    agent_name=step["agent"],
                    method_name=step["method"],
                    parameters=self._prepare_parameters(step["parameters"], results)
                )
                
                results[step["id"]] = {
                    "status": "completed",
                    "result": result,
                    "agent": step["agent"],
                    "method": step["method"]
                }
                
                completed_tasks.add(step["id"])
                step["status"] = "completed"
                
            except Exception as e:
                self.logger.error(f"Error executing step {step['id']}: {str(e)}")
                results[step["id"]] = {
                    "status": "failed",
                    "error": str(e),
                    "agent": step["agent"],
                    "method": step["method"]
                }
                step["status"] = "failed"
        
        return results
    
    def _prepare_parameters(self, parameters: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare parameters by resolving references to previous results."""
        prepared = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("$"):
                # Reference to previous result
                ref_parts = value[1:].split(".")
                if len(ref_parts) >= 2 and ref_parts[0] in results:
                    # Navigate through result structure
                    ref_value = results[ref_parts[0]]["result"]
                    for part in ref_parts[1:]:
                        if isinstance(ref_value, dict):
                            ref_value = ref_value.get(part)
                    prepared[key] = ref_value
                else:
                    prepared[key] = value
            else:
                prepared[key] = value
        
        return prepared
    
    def _synthesize_results(self, original_task: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize results from multiple agents into a coherent response."""
        # Prepare results summary
        results_summary = []
        for task_id, result in results.items():
            if result["status"] == "completed":
                results_summary.append({
                    "task": task_id,
                    "agent": result["agent"],
                    "output": result["result"]
                })
        
        # Use OpenAI to synthesize
        system_prompt = """You are a result synthesizer for a multi-agent system.
Given the original task and results from multiple agents, create a coherent final response.
Combine the results intelligently and present them in a clear, structured format."""
        
        user_prompt = f"""Original Task: {original_task}

Agent Results:
{json.dumps(results_summary, indent=2)}

Please synthesize these results into a coherent response."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            synthesis = response.choices[0].message.content
            
            return {
                "synthesis": synthesis,
                "raw_results": results,
                "success_rate": sum(1 for r in results.values() if r["status"] == "completed") / len(results) if results else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error synthesizing results: {str(e)}")
            return {
                "synthesis": "Results collected but synthesis failed",
                "raw_results": results,
                "error": str(e)
            }
    
    def _record_task(self, task: str, analysis: Dict, plan: List, result: Dict):
        """Record task execution for history and learning."""
        record = {
            "task": task,
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis,
            "execution_plan": plan,
            "result": result
        }
        
        self.task_history.append(record)
        
        # Keep only last 100 tasks
        if len(self.task_history) > 100:
            self.task_history = self.task_history[-100:]
    
    @agent_method(
        description="Get task execution history",
        parameters={
            "limit": {"type": "integer", "description": "Number of recent tasks to return", "default": 10}
        },
        returns="list"
    )
    def get_task_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent task execution history."""
        return self.task_history[-limit:]
    
    @agent_method(
        description="Get current status of the master agent",
        parameters={},
        returns="dict"
    )
    def get_status(self) -> Dict[str, Any]:
        """Get current status and statistics."""
        return {
            "status": "active",
            "model": self.model,
            "available_agents": len(router.list_agents()) - 1,  # Exclude self
            "task_history_count": len(self.task_history),
            "state": self.get_state()
        }
    
    async def aprocess_task(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Async version of process_task for better performance."""
        # Convert to async execution
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.process_task, task, context)
