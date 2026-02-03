import json
import re
import time
from typing import Any, Optional

from loguru import logger
import requests


from vita.config import (
    models,
    DEFAULT_MAX_RETRIES,
)
from vita.data_model.message import (
    AssistantMessage,
    Message,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from vita.environment.tool import Tool


class DictToObject:
    """
    Convert dictionary to object with attribute access
    Usage:
    response_obj = DictToObject(response)
    print(response_obj.choices[0].message.content)  # Instead of response["choices"][0]["message"]["content"]
    """
    def __init__(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                setattr(self, key, DictToObject(value))
            elif isinstance(value, list):
                setattr(self, key, [DictToObject(item) if isinstance(item, dict) else item for item in value])
            else:
                setattr(self, key, value)

    def to_dict(self):
        """Convert object back to dictionary"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, DictToObject):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [item.to_dict() if isinstance(item, DictToObject) else item for item in value]
            else:
                result[key] = value
        return result


def get_response_cost(usage, model) -> float:
    num_prompt_token = usage["prompt_tokens"]
    num_completion_token = usage["completion_tokens"]
    prompt_price = models.get(model, {}).get("cost_1m_token_dollar",{}).get("prompt_price", 0)
    completion_price = models.get(model, {}).get("cost_1m_token_dollar",{}).get("completion_price", 0)
    if prompt_price and completion_price:
        return (prompt_price * num_prompt_token + completion_price * num_completion_token) / 1000000
    else:
        return 0.0


def get_response_usage(response) -> Optional[dict]:
    usage = response.get("usage", {})
    if usage is None:
        return None
    return {
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0)
    }


def _flatten_reasoning_value(value: Any) -> list[str]:
    pieces: list[str] = []

    def _walk(node: Any) -> None:
        if node is None:
            return
        if isinstance(node, str):
            text = node.strip()
            if text:
                pieces.append(text)
            return
        if isinstance(node, (int, float)):
            pieces.append(str(node))
            return
        if isinstance(node, list):
            for item in node:
                _walk(item)
            return
        if isinstance(node, dict):
            handled = False
            for key in (
                "thinking",
                "text",
                "content",
                "reasoning",
                "reasoning_content",
                "output_text",
                "message",
                "analysis",
                "details",
            ):
                if key in node:
                    handled = True
                    _walk(node[key])
            if not handled and "value" in node:
                handled = True
                _walk(node["value"])
            if not handled:
                try:
                    fallback = json.dumps(node, ensure_ascii=False)
                except TypeError:
                    fallback = str(node)
                if fallback:
                    pieces.append(fallback)
            return
        pieces.append(str(node))

    _walk(value)
    return pieces


def _normalize_reasoning(value: Any) -> Optional[str]:
    if value is None:
        return None
    pieces = _flatten_reasoning_value(value)
    text = "\n".join(part for part in pieces if part)
    return text.strip() if text else None


def _extract_reasoning_from_raw(raw: Optional[dict]) -> Optional[str]:
    if not isinstance(raw, dict):
        return None
    candidates: list[Any] = []
    message = raw.get("message")
    if isinstance(message, dict):
        for key in ("reasoning_content", "reasoning", "thinking"):
            if key in message:
                candidates.append(message[key])
        content = message.get("content")
        if isinstance(content, list):
            thinking_items = [
                item
                for item in content
                if isinstance(item, dict)
                and item.get("type") in ("thinking", "reasoning")
            ]
            if thinking_items:
                candidates.append(thinking_items)
    for key in ("reasoning_content", "reasoning", "thinking"):
        if key in raw:
            candidates.append(raw[key])
    content_items = raw.get("content")
    if isinstance(content_items, list):
        thinking_items = [
            item
            for item in content_items
            if isinstance(item, dict)
            and item.get("type") in ("thinking", "reasoning")
        ]
        if thinking_items:
            candidates.append(thinking_items)
    raw_response = raw.get("raw_response")
    if isinstance(raw_response, dict):
        nested_reasoning = _extract_reasoning_from_raw(raw_response)
        if nested_reasoning:
            candidates.append(nested_reasoning)
    for candidate in candidates:
        normalized = _normalize_reasoning(candidate)
        if normalized:
            return normalized
    return None


def extract_reasoning_from_raw(raw: Optional[dict]) -> Optional[str]:
    """Public helper to extract reasoning text from raw LLM payload."""
    return _extract_reasoning_from_raw(raw)




def format_messages(messages: list[Message]) -> list[dict]:
    messages_formatted = []
    for message in messages:
        if isinstance(message, UserMessage):
            messages_formatted.append({"role": "user", "content": message.content})
        elif isinstance(message, AssistantMessage):
            tool_calls = None
            if message.is_tool_call():
                tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.name,
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                        "type": "function",
                    }
                    for tc in message.tool_calls
                ]
            messages_formatted.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": tool_calls,
                }
            )
            reasoning_content = getattr(message, 'reasoning', None) or _extract_reasoning_from_raw(message.raw_data)
            if reasoning_content:
                messages_formatted[-1]["reasoning_content"] = reasoning_content
        elif isinstance(message, ToolMessage):
            messages_formatted.append(
                {
                    "role": "tool",
                    "content": message.content,
                    "tool_call_id": message.id,
                    "name": message.name,
                }
            )
        elif isinstance(message, SystemMessage):
            messages_formatted.append({"role": "system", "content": message.content})
    return messages_formatted



def convert_tools_to_claude_format(tools: list) -> list:
    """
    Convert OpenAI format tools to Claude API format.
    
    OpenAI format:
    {
        "type": "function",
        "function": {
            "name": "...",
            "description": "...",
            "parameters": {...}
        }
    }
    
    Claude format:
    {
        "name": "...",
        "description": "...",
        "input_schema": {...}
    }
    """
    claude_tools = []
    for i, tool in enumerate(tools):
        if not isinstance(tool, dict):
            logger.warning(f"Tool at index {i} is not a dictionary, skipping: {type(tool)}")
            continue
            
        # Check for OpenAI format
        if "function" in tool:
            # OpenAI format: {"type": "function", "function": {...}}
            func = tool.get("function", {})
            if not isinstance(func, dict):
                logger.warning(f"Tool at index {i} has invalid 'function' field, skipping")
                continue
                
            tool_name = func.get("name")
            if not tool_name:
                logger.warning(f"Tool at index {i} missing 'name' in function field, skipping")
                continue
            
            claude_tool = {
                "name": tool_name,
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {})
            }
            claude_tools.append(claude_tool)
            logger.debug(f"Converted OpenAI format tool '{tool_name}' to Claude format")
            
        # Check for Claude format
        elif "name" in tool:
            # Already Claude format or direct format
            # Validate Claude format completeness
            tool_name = tool.get("name")
            if not tool_name:
                logger.warning(f"Tool at index {i} has 'name' key but value is empty, skipping")
                continue
            
            # Ensure required fields exist
            claude_tool = {
                "name": tool_name,
                "description": tool.get("description", ""),
                "input_schema": tool.get("input_schema", {})
            }
            
            # Warn if input_schema is missing (should be present for Claude format)
            if "input_schema" not in tool:
                logger.warning(f"Tool '{tool_name}' appears to be Claude format but missing 'input_schema', using empty dict")
            
            claude_tools.append(claude_tool)
            logger.debug(f"Tool '{tool_name}' already in Claude format, validated and added")
            
        else:
            # Unknown format - try to extract what we can
            logger.warning(f"Tool at index {i} has unknown format, attempting to extract: {list(tool.keys())[:5]}")
            
            # Try to find name in various possible locations
            tool_name = tool.get("name") or tool.get("tool_name") or tool.get("function_name")
            if tool_name:
                claude_tool = {
                    "name": tool_name,
                    "description": tool.get("description", tool.get("tool_description", "")),
                    "input_schema": tool.get("input_schema", tool.get("parameters", tool.get("schema", {})))
                }
                claude_tools.append(claude_tool)
                logger.warning(f"Extracted tool '{tool_name}' from unknown format, may be incomplete")
            else:
                logger.error(f"Tool at index {i} has no recognizable format and cannot extract name, skipping: {tool}")
    
    if len(claude_tools) < len(tools):
        logger.warning(f"Converted {len(claude_tools)} out of {len(tools)} tools to Claude format. Some tools may have been skipped.")
    
    return claude_tools


def _to_claude_text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def convert_messages_to_claude_format(
    messages: list[Message],
    enable_think: bool,
) -> tuple[list[dict], list[str]]:
    claude_messages: list[dict] = []
    system_prompts: list[str] = []
    auto_tool_counter = 0

    for message in messages:
        if isinstance(message, SystemMessage):
            if message.content:
                system_prompts.append(message.content)
            continue

        if isinstance(message, UserMessage):
            content_items: list[dict] = []
            if message.content is not None:
                content_items.append(_to_claude_text_block(message.content))
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    auto_tool_counter += 1
                    tool_use_id = tool_call.id or f"toolu_user_{auto_tool_counter}"
                    tool_input = tool_call.arguments or {}
                    if isinstance(tool_input, str):
                        try:
                            tool_input = json.loads(tool_input)
                        except json.JSONDecodeError:
                            tool_input = {"raw": tool_input}
                    content_items.append(
                        {
                            "type": "tool_use",
                            "id": tool_use_id,
                            "name": tool_call.name,
                            "input": tool_input,
                        }
                    )
            if not content_items:
                content_items.append(_to_claude_text_block(""))
            claude_messages.append({"role": "user", "content": content_items})
            continue

        if isinstance(message, AssistantMessage):
            content_items: list[dict] = []
            reasoning_content = getattr(message, 'reasoning', None) or _extract_reasoning_from_raw(message.raw_data)
            if enable_think and reasoning_content:
                content_items.append({"type": "thinking", "thinking": reasoning_content})
            if message.content is not None:
                content_items.append(_to_claude_text_block(message.content))
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    auto_tool_counter += 1
                    tool_use_id = tool_call.id or f"toolu_assistant_{auto_tool_counter}"
                    tool_input = tool_call.arguments or {}
                    if isinstance(tool_input, str):
                        try:
                            tool_input = json.loads(tool_input)
                        except json.JSONDecodeError:
                            tool_input = {"raw": tool_input}
                    content_items.append(
                        {
                            "type": "tool_use",
                            "id": tool_use_id,
                            "name": tool_call.name,
                            "input": tool_input,
                        }
                    )
            if not content_items:
                content_items.append(_to_claude_text_block(""))
            claude_messages.append({"role": "assistant", "content": content_items})
            continue

        if isinstance(message, ToolMessage):
            auto_tool_counter += 1
            tool_use_id = message.id or f"toolu_result_{auto_tool_counter}"
            tool_output = message.content
            if tool_output is None:
                tool_output = ""
            elif not isinstance(tool_output, str):
                tool_output = json.dumps(tool_output, ensure_ascii=False)
            tool_result: dict[str, Any] = {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": tool_output,
            }
            if message.error:
                tool_result["is_error"] = True
            claude_messages.append({"role": "user", "content": [tool_result]})
            continue

        logger.warning(f"Unexpected message type for Claude formatting: {type(message)}")

    return claude_messages, system_prompts


def _is_native_claude_api(base_url: str) -> bool:
    """Check if the API uses native Claude format (not OpenAI-compatible proxy)."""
    if not base_url:
        return False
    # Native Claude API uses /v1/messages endpoint, not /chat/completions
    return "/v1/messages" in base_url or "api.anthropic.com" in base_url


def kwargs_adapter(data: dict, enable_think: bool, messages: list[Message]) -> dict:
    model_name = data.get("model", "")
    base_url = data.get("base_url", "")
    
    # Only use Claude format for native Claude API, not OpenAI-compatible proxies
    if "claude" in model_name.lower() and _is_native_claude_api(base_url):
        claude_messages, system_prompts = convert_messages_to_claude_format(messages, enable_think)
        data["messages"] = claude_messages
        if system_prompts:
            existing_system = data.get("system")
            if existing_system:
                system_prompts.insert(0, existing_system)
            data["system"] = "\n".join(system_prompts)
        if not enable_think:
            data["thinking"] = {"type": "disabled"}
        else:
            data.pop("thinking", None)
        return data

    if not enable_think:
        if data.get("model", "") == "gpt-5":
            data["reasoning_effort"] = "minimal"
        elif "reasoning_effort" in data:
            data.pop("reasoning_effort")
    return data


def generate(
    model: str,
    messages: list[Message],
    tools: Optional[list[Tool]] = None,
    tool_choice: Optional[str] = None,
    enable_think: bool = False,
    **kwargs: Any,
) -> UserMessage | AssistantMessage:
    """
    Generate a response from the model.

    Args:
        model: The model to use.
        messages: The messages to send to the model.
        tools: The tools to use.
        tool_choice: The tool choice to use.
        enable_think: Whether to enable think mode for the agent.
        **kwargs: Additional arguments to pass to the model.

    Returns: A tuple containing the message and the cost.
    """
    try:
        if kwargs.get("num_retries") is None:
            kwargs["num_retries"] = DEFAULT_MAX_RETRIES
        messages_formatted = format_messages(messages)
        tools = [tool.openai_schema for tool in tools] if tools else None
        
        # Set default tool_choice only if tools are provided
        # Note: tool_choice will be adjusted later for Claude models
        if tools and tool_choice is None:
            tool_choice = "auto"
        
        try:
            data = {
                "model": model,
                "messages": messages_formatted,
                "stream": False,
                "temperature": kwargs.get("temperature"),
                "tools": tools,
                "tool_choice": tool_choice,
            }
            data.update(models[model])
            
            # Extract base_url and headers before removing them from data
            # These are needed for the HTTP request but shouldn't be in the request body
            base_url = data.pop("base_url", models[model].get("base_url"))
            headers = data.pop("headers", models[model].get("headers"))
            
            # Check if this is native Claude API (not OpenAI-compatible proxy)
            is_native_claude = "claude" in model.lower() and _is_native_claude_api(base_url)
            
            # For native Claude API, remove Authorization header if x-api-key is present
            # Native Claude API uses x-api-key, not Authorization: Bearer
            if headers and is_native_claude:
                if "x-api-key" in headers and "Authorization" in headers:
                    headers.pop("Authorization", None)
                    logger.debug(f"Removed Authorization header for native Claude API, using x-api-key instead")
            
            # Remove other config fields that shouldn't be sent to API
            data.pop("cost_1m_token_dollar", None)
            data.pop("name", None)
            data.pop("max_input_tokens", None)  # This is a config field, not an API parameter
            
            # For non-Claude models, ensure tool_choice is removed if tools are None/empty
            if not is_native_claude:
                if not data.get("tools") or (isinstance(data.get("tools"), list) and len(data.get("tools", [])) == 0):
                    if "tool_choice" in data:
                        data.pop("tool_choice", None)
                        logger.debug("Removed tool_choice for non-Claude model since tools are empty")
            
            data = kwargs_adapter(data, enable_think, messages)
            
            # Handle Claude API specific parameter formats (after adapter)
            if is_native_claude:
                # Extract system messages and convert to top-level system parameter
                # Claude API requires system messages as a top-level parameter, not in messages array
                if "messages" in data and isinstance(data["messages"], list):
                    system_messages = []
                    filtered_messages = []
                    
                    for msg in data["messages"]:
                        if isinstance(msg, dict) and msg.get("role") == "system":
                            # Collect system messages
                            content = msg.get("content", "")
                            if content:
                                system_messages.append(content)
                        else:
                            # Keep non-system messages
                            filtered_messages.append(msg)
                    
                    # Set top-level system parameter if there are system messages
                    if system_messages:
                        # Join multiple system messages with newlines
                        data["system"] = "\n".join(system_messages)
                        logger.debug(f"Extracted {len(system_messages)} system message(s) to top-level system parameter")
                    
                    # Update messages to exclude system messages
                    data["messages"] = filtered_messages
                    logger.debug(f"Filtered messages: {len(filtered_messages)} messages (removed {len(system_messages)} system messages)")
                
                # Convert tools from OpenAI format to Claude format (only for native Claude API)
                tools_val = data.get("tools")
                if tools_val is not None:
                    if not isinstance(tools_val, list) or len(tools_val) == 0:
                        data.pop("tools", None)
                        data.pop("tool_choice", None)
                    else:
                        # Check if already in Claude format
                        is_claude_format = (
                            isinstance(tools_val[0], dict) and 
                            "name" in tools_val[0] and 
                            "input_schema" in tools_val[0] and
                            "function" not in tools_val[0]
                        )
                        
                        if not is_claude_format:
                            # Convert from OpenAI format
                            converted_tools = convert_tools_to_claude_format(tools_val)
                            if converted_tools:
                                data["tools"] = converted_tools
                                if len(converted_tools) < len(tools_val):
                                    logger.warning(f"Tool conversion: {len(converted_tools)}/{len(tools_val)} tools converted")
                            else:
                                logger.error("Tool conversion failed, removing tools")
                                data.pop("tools", None)
                                data.pop("tool_choice", None)
                        else:
                            # Validate and ensure required fields
                            validated = []
                            for tool in tools_val:
                                if isinstance(tool, dict) and "name" in tool:
                                    validated.append({
                                        "name": tool.get("name"),
                                        "description": tool.get("description", ""),
                                        "input_schema": tool.get("input_schema", {})
                                    })
                            if validated:
                                data["tools"] = validated
                            else:
                                logger.error("All tools invalid, removing")
                                data.pop("tools", None)
                                data.pop("tool_choice", None)
                
                # Handle tool_choice for native Claude API
                tools_present = bool(data.get("tools"))
                tool_choice_val = data.get("tool_choice")
                
                if tool_choice_val == "none" or not tools_present:
                    data.pop("tool_choice", None)
                elif tool_choice_val in (None, "auto", "required"):
                    data["tool_choice"] = {"type": "any"}
                elif isinstance(tool_choice_val, str) and tools_present:
                    data["tool_choice"] = {"type": "tool", "name": tool_choice_val}
                elif isinstance(tool_choice_val, dict) and "type" not in tool_choice_val:
                    logger.warning(f"Invalid tool_choice dict: {tool_choice_val}")
                    data.pop("tool_choice", None)
                
                # Ensure tool_choice exists if tools are present
                if tools_present and "tool_choice" not in data:
                    data["tool_choice"] = {"type": "any"}

            # Debug: log the final data being sent (without sensitive info)
            if is_native_claude:
                debug_data = {k: v for k, v in data.items() if k != "messages"}
                debug_data["messages_count"] = len(data.get("messages", []))
                if "tools" in data:
                    debug_data["tools_count"] = len(data["tools"]) if isinstance(data["tools"], list) else "not a list"
                logger.debug(f"Native Claude API request data: {debug_data}")
            
            max_retries = 3
            retry_delay = 1
            for attempt in range(max_retries + 1):
                try:
                    response = requests.post(base_url, json=data, headers=headers, timeout=(10, 600))

                    # Check HTTP status code
                    if response.status_code == 500:
                        if attempt < max_retries:
                            logger.warning(f"API returned 500 error, attempt {attempt + 1} retry, retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            response.raise_for_status()
                    
                    # Parse JSON response
                    response_json = response.json()
                    
                    # Check for API errors
                    # Claude API format: {'type': 'error', 'error': {...}}
                    # OpenAI API format: {'error': {...}}
                    error_info = None
                    error_type = None
                    error_message = None
                    
                    if response_json.get('type') == 'error':
                        # Claude API error format
                        error_info = response_json.get('error', {})
                        error_type = error_info.get('type', 'unknown_error')
                        error_message = error_info.get('message', 'Unknown error')
                        logger.error(f"Claude API returned error: {error_type} - {error_message}")
                    elif 'error' in response_json:
                        # OpenAI API error format
                        error_info = response_json.get('error', {})
                        error_type = error_info.get('type', 'unknown_error')
                        error_message = error_info.get('message', 'Unknown error')
                        logger.error(f"API returned error: {error_type} - {error_message}")
                    
                    # Handle error if found
                    if error_info is not None:
                        # Don't retry on invalid_request_error (like format errors)
                        if 'invalid_request' in error_type.lower():
                            raise ValueError(f"API request error: {error_message}")
                        # Retry for other errors
                        if attempt < max_retries:
                            logger.warning(f"Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        else:
                            raise ValueError(f"API error: {error_type} - {error_message}")
                    
                    response = response_json
                    break

                except requests.exceptions.RequestException as e:
                    if attempt < max_retries:
                        logger.warning(f"Request exception, attempt {attempt + 1} retry, retrying in {retry_delay} seconds... Error: {e}")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise e
        except Exception as e:
            logger.error(e)
            raise e
        
        # Validate response structure before processing
        # Determine response format based on actual response structure, not just model name
        # Some Claude-compatible APIs may return OpenAI-format responses
        is_claude_format = 'content' in response and 'choices' not in response
        is_openai_format = 'choices' in response
        
        if "claude" in model.lower():
            # Handle Claude API response format
            if not is_claude_format and not is_openai_format and 'error' not in response:
                raise ValueError(f"Invalid Claude API response: missing 'content' or 'choices' field. Response: {response}")
        else:
            # Handle OpenAI API response format
            if not is_openai_format and 'error' not in response:
                raise ValueError(f"Invalid OpenAI API response: missing 'choices' field. Response: {response}")
        
        usage = get_response_usage(response)
        cost = get_response_cost(usage, model)
        reasoning_text: Optional[str] = None

        # Use actual response format, not just model name
        if is_claude_format:
            try:
                raw_response = response
                content_items = raw_response.get("content", [])
                if not content_items:
                    logger.warning(f"Claude API returned empty content. Full response: {raw_response}")
                content = ""
                tool_calls = []

                for item in content_items:
                    if not isinstance(item, dict):
                        logger.warning(f"Unexpected content item type: {type(item)}, value: {item}")
                        continue

                    item_type = item.get("type")
                    if item_type in ("thinking", "reasoning"):
                        continue
                    if item_type == "text":
                        text_content = item.get("text", "")
                        if text_content:
                            content += text_content
                    elif item_type == "tool_use":
                        tool_calls.append(
                            {
                                "id": item.get("id"),
                                "function": {
                                    "name": item.get("name"),
                                    "arguments": json.dumps(item.get("input", {})),
                                },
                            }
                        )

                if not content and not tool_calls:
                    raise ValueError("Claude API returned empty content and no tool calls")

                reasoning_text = _extract_reasoning_from_raw(raw_response)

                message_payload = {
                    "role": "assistant",
                    "content": content if content else None,
                    "tool_calls": tool_calls if tool_calls else None,
                }
                if reasoning_text:
                    message_payload["reasoning_content"] = reasoning_text

                response = {"message": message_payload, "raw_response": raw_response}
                if raw_response.get("usage"):
                    response["usage"] = raw_response.get("usage")
            except Exception as e:
                logger.error(f"Failed to parse Claude response: {e}")
                logger.error(f"Full response: {json.dumps(response, indent=2)}")
                raise
        elif is_openai_format:
            try:
                if not response.get("choices") or len(response["choices"]) == 0:
                    raise ValueError(f"Invalid response: missing or empty 'choices' field. Response: {response}")
                response = response["choices"][0]
            except (KeyError, IndexError) as e:
                logger.error(f"Failed to extract choice from response: {response}")
                raise ValueError(f"Invalid response structure: {e}") from e
            assert response["message"]["role"] == "assistant", (
                "The response should be an assistant message"
            )
            reasoning_text = _extract_reasoning_from_raw(response)
            if reasoning_text and not response["message"].get("reasoning_content"):
                response["message"]["reasoning_content"] = reasoning_text

        content = response["message"].get("content")
        tool_calls = response["message"].get("tool_calls") or []
        tool_calls = [
            ToolCall(
                id=tool_call.get("id"),
                name=tool_call.get("function", {}).get("name"),
                arguments=json.loads(tool_call.get("function", {}).get("arguments"))
                if tool_call.get("function", {}).get("arguments")
                else {},
            )
            for tool_call in tool_calls
        ]
        tool_calls = tool_calls or None
        message = AssistantMessage(
            role="assistant",
            content=content,
            tool_calls=tool_calls,
            cost=cost,
            usage=usage,
            raw_data=response,
            reasoning=reasoning_text,
        )
        return message
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(e)


def get_cost(messages: list[Message]) -> tuple[float, float] | None:
    """
    Get the cost of the interaction between the agent and the user.
    Returns None if any message has no cost.
    """
    agent_cost = 0
    user_cost = 0
    for message in messages:
        if isinstance(message, ToolMessage):
            continue
        if message.cost is not None:
            if isinstance(message, AssistantMessage):
                agent_cost += message.cost
            elif isinstance(message, UserMessage):
                user_cost += message.cost
        else:
            logger.warning(f"Message {message.role}: {message.content} has no cost")
            return None
    return agent_cost, user_cost
