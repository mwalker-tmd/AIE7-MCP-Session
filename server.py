from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient
import os
import requests
import json
from dice_roller import DiceRoller

load_dotenv()

mcp = FastMCP("mcp-server")
client = TavilyClient(os.getenv("TAVILY_API_KEY"))

@mcp.tool()
def web_search(query: str) -> str:
    """Search the web for information about the given query"""
    search_results = client.get_search_context(query=query)
    return search_results

@mcp.tool()
def roll_dice(notation: str, num_rolls: int = 1) -> str:
    """Roll the dice with the given notation"""
    roller = DiceRoller(notation, num_rolls)
    return str(roller)

"""
Add your own tool here, and then use it through Cursor!
"""
@mcp.tool()
def metal_prices(query: str) -> str:
    """Get the latest metal prices"""
    try:
        # Get API key from environment
        api_key = os.getenv("METALS_DEV_API_KEY")
        if not api_key:
            return "Error: METALS_DEV_API_KEY not found in environment variables"
        
        # Make API call to metals.dev
        url = f"https://api.metals.dev/v1/latest?api_key={api_key}&currency=USD&unit=toz"
        headers = {
            "Accept": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse the query to determine which metals to show
        query_lower = query.lower()
        metals_to_show = []
        
        # Define metal mappings (using the actual API response keys)
        metal_mappings = {
            "gold": "gold",
            "silver": "silver", 
            "platinum": "platinum",
            "palladium": "palladium",
            "copper": "copper",
            "nickel": "nickel",
            "aluminum": "aluminum",
            "zinc": "zinc",
            "lead": "lead"
        }
        
        # Check if specific metals are requested
        if any(metal in query_lower for metal in metal_mappings.keys()):
            for metal_name, metal_key in metal_mappings.items():
                if metal_name in query_lower and metal_key in data.get("metals", {}):
                    metals_to_show.append((metal_name, metal_key))
        else:
            # Default to major metals if no specific request
            default_metals = ["gold", "silver", "platinum", "palladium"]
            for metal_name in default_metals:
                metal_key = metal_mappings[metal_name]
                if metal_key in data.get("metals", {}):
                    metals_to_show.append((metal_name, metal_key))
        
        if not metals_to_show:
            return "No metal prices found for your query"
        
        # Format the response
        result = f"Metal Prices (USD):\n"
        for metal_name, metal_key in metals_to_show:
            price = data["metals"][metal_key]
            result += f"• {metal_name.title()}: ${price:,.2f}\n"
        
        result += f"\nBase currency: {data.get('base', 'USD')}"
        return result
        
    except requests.exceptions.RequestException as e:
        return f"Error fetching metal prices: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")