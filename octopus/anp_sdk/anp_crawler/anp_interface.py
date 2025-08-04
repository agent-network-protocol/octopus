"""
ANP Interface Converter Module

This module provides functionality to convert JSON-RPC and OpenRPC interface formats
to OpenAI Tools JSON format for seamless LLM integration.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ANPInterface:
    """
    Interface converter for transforming JSON-RPC and OpenRPC interfaces to OpenAI Tools format.
    
    Supported conversions:
    - JSON-RPC 2.0 → OpenAI Tools
    - OpenRPC → OpenAI Tools
    """
    
    def __init__(self):
        """Initialize the interface converter."""
        pass
    
    def convert_to_openai_tools(self, interface_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert JSON-RPC or OpenRPC interface definition to OpenAI Tools format.
        
        Args:
            interface_data: Interface definition from parser
            
        Returns:
            OpenAI Tools format dictionary or None if conversion fails
            {
                "type": "function",
                "function": {
                    "name": str,
                    "description": str,
                    "parameters": {
                        "type": "object",
                        "properties": {...},
                        "required": [...]
                    }
                }
            }
        """
        interface_type = interface_data.get("type", "unknown")
        
        # Handle different interface types
        if interface_type == "jsonrpc_method":
            try:
                result = self._convert_jsonrpc_method(interface_data)
                if result:
                    logger.debug(f"Successfully converted {interface_type} to OpenAI Tools format")
                return result
            except Exception as e:
                logger.error(f"Failed to convert {interface_type}: {str(e)}")
                return None
        elif interface_type == "openrpc_method":
            try:
                result = self._convert_openrpc_method(interface_data)
                if result:
                    logger.debug(f"Successfully converted {interface_type} to OpenAI Tools format")
                return result
            except Exception as e:
                logger.error(f"Failed to convert {interface_type}: {str(e)}")
                return None
        else:
            logger.warning(f"Unsupported interface type: {interface_type}. Only JSON-RPC and OpenRPC methods are supported.")
            return None
    
    def _convert_jsonrpc_method(self, interface_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JSON-RPC method to OpenAI Tools format."""
        method_name = interface_data.get("method_name", "unknown_method")
        description = interface_data.get("description", f"JSON-RPC method: {method_name}")
        params = interface_data.get("params", {})
        
        # Convert JSON-RPC parameters to JSON Schema
        parameters = self._convert_jsonrpc_params_to_schema(params)
        
        return {
            "type": "function",
            "function": {
                "name": self._sanitize_function_name(method_name),
                "description": description,
                "parameters": parameters
            }
        }
    
    def _convert_openrpc_method(self, interface_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OpenRPC method to OpenAI Tools format."""
        method_name = interface_data.get("method_name", "unknown_method")
        
        # Use description, fall back to summary if description is empty
        description = interface_data.get("description", "")
        if not description:
            description = interface_data.get("summary", f"OpenRPC method: {method_name}")
        
        params = interface_data.get("params", [])
        components = interface_data.get("components", {})
        
        # Convert OpenRPC parameters to JSON Schema
        parameters = self._convert_openrpc_params_to_schema(params, components)
        
        return {
            "type": "function",
            "function": {
                "name": self._sanitize_function_name(method_name),
                "description": description,
                "parameters": parameters
            }
        }
    
    def _convert_jsonrpc_params_to_schema(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JSON-RPC parameters to JSON Schema format."""
        if not params:
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
        
        # If params is already a schema-like structure
        if "type" in params:
            return params
        
        # Convert named parameters to schema
        properties = {}
        required = []
        
        for param_name, param_def in params.items():
            if isinstance(param_def, dict):
                properties[param_name] = param_def
                if param_def.get("required", False):
                    required.append(param_name)
            else:
                # Simple parameter
                properties[param_name] = {
                    "type": "string",
                    "description": f"Parameter: {param_name}"
                }
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def _convert_openrpc_params_to_schema(self, params: List[Dict[str, Any]], components: Dict[str, Any] = None) -> Dict[str, Any]:
        """Convert OpenRPC parameters array to JSON Schema format."""
        if not params:
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
        
        if components is None:
            components = {}
        
        properties = {}
        required = []
        
        for param in params:
            if not isinstance(param, dict):
                continue
                
            param_name = param.get("name", "")
            param_description = param.get("description", "")
            param_required = param.get("required", False)
            param_schema = param.get("schema", {})
            
            if param_name:
                # Use the schema from the parameter, or create a basic string schema
                if param_schema:
                    # Resolve any $ref references in the schema
                    property_def = self._resolve_schema_refs(param_schema, components)
                else:
                    property_def = {"type": "string"}
                
                # Add description to the property if not already present
                if param_description and "description" not in property_def:
                    property_def["description"] = param_description
                
                properties[param_name] = property_def
                
                # Add to required list if marked as required
                if param_required:
                    required.append(param_name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def _sanitize_function_name(self, name: str) -> str:
        """Sanitize function name to comply with OpenAI Tools requirements."""
        if not name:
            return "unknown_function"
        
        # Replace invalid characters with underscores
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        
        # Ensure it starts with a letter or underscore
        if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
            sanitized = f"fn_{sanitized}"
        
        # Ensure it's not empty
        if not sanitized:
            sanitized = "unknown_function"
        
        # Limit length (OpenAI has limits)
        if len(sanitized) > 64:
            sanitized = sanitized[:64]
        
        return sanitized
    
    def _resolve_schema_refs(self, schema: Dict[str, Any], components: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve $ref references in a JSON Schema.
        
        Args:
            schema: The schema that may contain $ref references
            components: The components section from OpenRPC document
            
        Returns:
            Schema with all $ref references resolved
        """
        if not isinstance(schema, dict):
            return schema
        
        # If this is a $ref, resolve it
        if "$ref" in schema:
            ref_path = schema["$ref"]
            resolved_schema = self._resolve_ref(ref_path, components)
            if resolved_schema:
                # Recursively resolve any refs in the resolved schema
                return self._resolve_schema_refs(resolved_schema, components)
            else:
                logger.warning(f"Could not resolve $ref: {ref_path}")
                return {"type": "object", "description": f"Unresolved reference: {ref_path}"}
        
        # If this is a regular schema, check for nested refs
        resolved_schema = {}
        for key, value in schema.items():
            if key == "properties" and isinstance(value, dict):
                # Resolve refs in properties
                resolved_properties = {}
                for prop_name, prop_schema in value.items():
                    resolved_properties[prop_name] = self._resolve_schema_refs(prop_schema, components)
                resolved_schema[key] = resolved_properties
            elif key == "items" and isinstance(value, dict):
                # Resolve refs in array items
                resolved_schema[key] = self._resolve_schema_refs(value, components)
            elif isinstance(value, dict):
                # Resolve refs in nested objects
                resolved_schema[key] = self._resolve_schema_refs(value, components)
            elif isinstance(value, list):
                # Resolve refs in lists
                resolved_list = []
                for item in value:
                    if isinstance(item, dict):
                        resolved_list.append(self._resolve_schema_refs(item, components))
                    else:
                        resolved_list.append(item)
                resolved_schema[key] = resolved_list
            else:
                # Keep primitive values as-is
                resolved_schema[key] = value
        
        return resolved_schema
    
    def _resolve_ref(self, ref_path: str, components: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve a single $ref reference.
        
        Args:
            ref_path: The reference path (e.g., "#/components/schemas/Room")
            components: The components section from OpenRPC document
            
        Returns:
            The referenced schema or None if not found
        """
        if not ref_path.startswith("#/"):
            logger.warning(f"Unsupported reference format: {ref_path}")
            return None
        
        # Parse the reference path
        # Format: #/components/schemas/SchemaName
        path_parts = ref_path[2:].split("/")  # Remove "#/" and split
        
        if len(path_parts) < 3 or path_parts[0] != "components":
            logger.warning(f"Invalid reference path: {ref_path}")
            return None
        
        try:
            # Navigate to the referenced schema
            current = components
            for part in path_parts[1:]:  # Skip "components"
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    logger.warning(f"Reference not found: {ref_path}")
                    return None
            
            return current if isinstance(current, dict) else None
            
        except Exception as e:
            logger.error(f"Error resolving reference {ref_path}: {str(e)}")
            return None