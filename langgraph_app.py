import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import json
import re

load_dotenv()

# Define the state structure
class AgentState(TypedDict):
    user_input: str
    tool_choice: str
    tool_result: str
    final_response: str

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Initialize MCP client to connect to your server
client = MultiServerMCPClient(
    {
        "mcp-server": {
            "command": "uv",
            "args": ["run", "server.py"],
            "transport": "stdio",
        }
    }
)

# Get the tools from your MCP server
mcp_tools = None  # Will be initialized in async function

async def initialize_tools():
    """Initialize MCP tools"""
    global mcp_tools
    mcp_tools = await client.get_tools()

async def decide_tool(state: AgentState) -> AgentState:
    """LLM decides which tool to use based on user input"""
    user_input = state["user_input"]
    
    # Reset state for new runs (clear previous run data)
    if state.get("tool_result") or state.get("final_response"):
        state = {
            "user_input": user_input,
            "tool_choice": "",
            "tool_result": "",
            "final_response": ""
        }
    
    # Create a prompt for the LLM to decide which tool to use
    prompt = f"""
    Based on the user's input, determine which tool to use. Available tools:
    1. web_search - for searching the web
    2. roll_dice - for rolling dice (e.g., "2d6", "1d20")
    3. metal_prices - for getting metal prices (gold, silver, platinum, etc.)
    
    User input: {user_input}
    
    Respond with ONLY the tool name (web_search, roll_dice, or metal_prices).
    """
    
    response = await llm.ainvoke(prompt)
    tool_choice = response.content.strip().lower()
    
    return {
        **state,
        "tool_choice": tool_choice
    }

async def call_tool(state: AgentState) -> AgentState:
    """Call the selected MCP tool"""
    user_input = state["user_input"]
    tool_choice = state["tool_choice"]
    
    try:
        # Initialize tools if not already done
        global mcp_tools
        if mcp_tools is None:
            await initialize_tools()
        
        # Find the appropriate tool
        tool_to_use = None
        for tool in mcp_tools:
            if tool.name == tool_choice:
                tool_to_use = tool
                break
        
        if tool_to_use:
            # Prepare parameters based on tool type
            if tool_choice == "roll_dice":
                # Extract dice notation from user input (e.g., "Roll 2d6" -> "2d6")
                dice_match = re.search(r'(\d+d\d+)', user_input.lower())
                if dice_match:
                    notation = dice_match.group(1)
                    # Check if num_rolls is specified (e.g., "Roll 3d6 5 times")
                    rolls_match = re.search(r'(\d+)\s+times?', user_input.lower())
                    num_rolls = int(rolls_match.group(1)) if rolls_match else 1
                    result = await tool_to_use.ainvoke({"notation": notation, "num_rolls": num_rolls})
                else:
                    tool_result = "Could not parse dice notation. Please use format like '2d6' or '1d20'"
                    return {**state, "tool_result": tool_result}
            else:
                # For web_search and metal_prices, use the query parameter
                result = await tool_to_use.ainvoke({"query": user_input})
            
            tool_result = str(result)
        else:
            tool_result = f"Tool '{tool_choice}' not found"
            
    except Exception as e:
        tool_result = f"Error calling tool: {str(e)}"
    
    return {
        **state,
        "tool_result": tool_result
    }

async def format_response(state: AgentState) -> AgentState:
    """Format the final response"""
    tool_result = state["tool_result"]
    
    # Create a simple formatted response
    final_response = f"Tool Result:\n{tool_result}"
    
    return {
        **state,
        "final_response": final_response
    }

# Create the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("decide_tool", decide_tool)
workflow.add_node("call_tool", call_tool)
workflow.add_node("format_response", format_response)

# Set entry point
workflow.set_entry_point("decide_tool")

# Add edges
workflow.add_edge("decide_tool", "call_tool")
workflow.add_edge("call_tool", "format_response")
workflow.add_edge("format_response", END)

# Compile the graph
app = workflow.compile()

async def run_app(user_input: str):
    """Run the LangGraph application with user input"""
    # Initialize tools first
    await initialize_tools()
    
    result = await app.ainvoke({
        "user_input": user_input,
        "tool_choice": "",
        "tool_result": "",
        "final_response": ""
    })
    
    return result["final_response"]

# Test code removed for LangGraph Studio compatibility
# The application will now run continuously when loaded by the dev server
