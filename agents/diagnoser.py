# simple_agent.py
# a super simple smolagents agent with one tool.
# run: python simple_agent.py

from smolagents import CodeAgent, LiteLLMModel, tool
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

# --- a tiny tool (example): list the columns of a CSV ---
@tool
def list_columns(csv_path: str) -> list[str]:
    """
    Return the column names from a CSV (auto-detects delimiter).

    Args:
        csv_path: Path to the CSV file to inspect.
    """
    df = pd.read_csv(csv_path, sep=None, engine="python")
    return [str(c).strip() for c in df.columns]
# --- build the simplest possible agent ---
def build_agent() -> CodeAgent:
    # uses Hugging Face Inference as the model backend.
    # set HF_TOKEN in your environment.
    model = LiteLLMModel(
        model_id="gpt-4o-mini",
        api_base="https://api.openai.com/v1",
        api_key=None   # stays None → will pick up OPENAI_API_KEY from environment (via .env)
)
    
    agent = CodeAgent(
        model=model,
        tools=[list_columns],
        instructions=(
            "You are a minimal agent. "
            "When the user asks for something the tool can do, call the tool and return the result plainly."
        ),
        add_base_tools=False,  # keep it super minimal
        max_steps=3
    )
    return agent

if __name__ == "__main__":
    agent = build_agent()
    # example query (adjust the path to your file)
    print(agent.run("Call list_columns on 'data/NBIM_Dividend_Bookings 1.csv' and 'data/CUSTODY_Dividend_Bookings 1.csv' and " \
    "tell me what it is about. Then, tell me what is going wrong in the information flow between NBIM and its custodian. Do NOT " \
    "tell me what might go wrong; either tell med what is actually wrong, or say 'I don't know'."))
