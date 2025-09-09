# simple_agent.py
# a super simple smolagents agent with one tool.
# run: python simple_agent.py

from smolagents import CodeAgent, LiteLLMModel, tool
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
from tools.file_merge import MergeAndTransposeTool


class Diagnoser(CodeAgent):
    def __init__(self):
        model = LiteLLMModel(
            model_id="gpt-4o-mini",
            api_base="https://api.openai.com/v1",
            api_key=None,  # picked up from OPENAI_API_KEY in .env
        )
        tool_instance = MergeAndTransposeTool()
        super().__init__(
            model=model,
            tools=[tool_instance],
            instructions=(
                "You are a minimal agent. "
                "When the user asks for something the tool can do, "
                "call the tool and return the result plainly."
            ),
            add_base_tools=False,
            max_steps=3,
        )

if __name__ == "__main__":
    agent = Diagnoser()
    # example query (adjust the path to your file)
    print(agent.run("Call MergeAndTransposeTool on 'data/NBIM_Dividend_Bookings 1.csv' and 'data/CUSTODY_Dividend_Bookings 1.csv' and " \
    "tell me what it is about. Then, tell me what is going wrong in the information flow between NBIM and its custodian. Do NOT " \
    "tell me what might go wrong; either tell med what is actually wrong, or say 'I don't know'."))
