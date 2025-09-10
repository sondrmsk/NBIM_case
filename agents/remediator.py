# agents/remediator.py
from smolagents import CodeAgent, LiteLLMModel
from tools.remediation_retriever import RemediationRetrieverTool
from dotenv import load_dotenv
load_dotenv()

class RemediationAgent(CodeAgent):
    def __init__(self, knowledge_base_path: str):
        model = LiteLLMModel(
            model_id="gpt-4o",
            api_base="https://api.openai.com/v1",
            api_key=None,  # from OPENAI_API_KEY in .env
        )
        tool = RemediationRetrieverTool(knowledge_base_path)

        super().__init__(
            model=model,
            tools=[tool],
            instructions=(
                "You are a remediation specialist. Your task is to suggest how to fix discrepancies "
                "found in dividend data between NBIM and its Custodian Bank. "
                "You will be given an ID, severity, and an explanation of mismatches. "
                ""
                "Workflow: "
                "1) Read the discrepancy details carefully. "
                "2) Use the retriever tool to find relevant remediation patterns. "
                "3) Suggest a short remediation strategy (1–3 sentences). The strategy must contain the "
                "actual suggestions for remediation, e.g. if custodian varies between x and y, you say "
                "'change custodian to y' and if holding quantity differs between x and y, you say "
                "'adjust holding quantity to y' and so on. "
                ""
                "Important rules: "
                "- Do not re-diagnose the issue, only provide remediation. "
                "- Be concise and practical. "
                ""
                "Output format: Return a plain string with the remediation suggestion."
            ),
            add_base_tools=False,
            additional_authorized_imports=["json", "pandas", "pathlib"]
        )

    def remediate(self, entry: dict) -> str:
        """Run remediation on one discrepancy entry (from severity_results.json)."""
        query = (
            f"Suggest a remediation for this discrepancy:\n"
            f"ID: {entry['id']}\n"
            f"Severity: {entry['severity']}\n"
            f"Explanation: {entry['explanation']}"
        )
        return self.run(query)
