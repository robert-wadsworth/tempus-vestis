"""
TempusVestis - AI-Powered Wardrobe Consultant

This is the main CLI application that orchestrates the weather agent and RAG
system via a LangGraph StateGraph pipeline.
"""

import os
import sys
from dotenv import load_dotenv

from core.graph import build_wardrobe_graph

# Load environment variables
load_dotenv()

# On Windows, the default console codepage (cp1252) can't encode the emoji/
# box-drawing characters this CLI prints, raising UnicodeEncodeError before
# any real output appears. Force UTF-8 so `python main.py` works without
# requiring PYTHONUTF8=1 to be set externally.
if sys.stdout.encoding is not None and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def print_banner():
    """Print the application banner."""
    banner = f"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║                     TEMPUS VESTIS                        ║
║            AI-Powered Wardrobe Consultant                ║
║                                                          ║
║    Your intelligent packing assistant for weather-       ║
║         based wardrobe recommendations                   ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_help():
    """Print usage instructions."""
    help_text = """
USAGE:
  Simply describe your travel plans, and I'll help you pack!

EXAMPLES:
  • "What should I pack for Chicago in 7 days?"
  • "I'm going to Miami next weekend, what should I wear?"
  • "Help me pack for San Francisco 10 days from now"
  
NOTE: Currently supports US locations only (National Weather Service API)

COMMANDS:
  help  - Show this help message
  quit  - Exit the application
  exit  - Exit the application
"""
    print(help_text)


def run_pipeline(query: str) -> str:
    """
    Run the LangGraph pipeline: weather_agent_node → rag_node (or error_node).

    Args:
        query: User's query

    Returns:
        Final wardrobe recommendations or a user-facing error message
    """
    print("\n🔍 Analyzing your request...")

    graph = build_wardrobe_graph()
    result = graph.invoke({
        "query": query,
        "weather_data": None,
        "recommendations": None,
        "error": None,
    })

    if not result.get("error"):
        print("🌤️  Weather data retrieved successfully")
        print("📚 Consulting wardrobe knowledge base...")

    return result.get("recommendations", "I couldn't process that request.")


def interactive_mode():
    """Run the application in interactive mode."""
    print_banner()
    print_help()
    
    while True:
        try:
            # Get user input
            print("\n" + "="*60)
            user_input = input("\n💬 You: ").strip()
            
            # Handle commands
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit']:
                print("\n👋 Thanks for using TempusVestis! Safe travels!")
                break
            
            if user_input.lower() == 'help':
                print_help()
                continue
            
            # Process the query
            print("\n🤖 TempusVestis:")
            response = run_pipeline(user_input)
            print("\n" + response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Thanks for using TempusVestis! Safe travels!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try again.")


def single_query_mode(query: str):
    """Run a single query and exit."""
    print_banner()
    print(f"\n💬 Query: {query}")
    print("\n🤖 TempusVestis:")

    response = run_pipeline(query)
    print("\n" + response)


def main():
    """Main entry point for the application."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY not found in environment variables.")
        print("Please create a .env file with your OpenAI API key.")
        sys.exit(1)
    
    # Check if a query was provided as command-line argument
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        single_query_mode(query)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()