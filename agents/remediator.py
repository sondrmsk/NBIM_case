import json
from smolagents import CodeAgent, InferenceClientModel
from tools.remediation_retriever import RemediationRetrieverTool


class RemediationAgent:
    def __init__(self, knowledge_base_path="knowledge_base.json", model_id=None):
        """
        RemediationAgent suggests fixes for discrepancies based on a knowledge base.

        Args:
            knowledge_base_path: Path to knowledge base JSON.
            model_id: Optional Hugging Face model ID (default: smolagents default).
        """
        self.tool = RemediationRetrieverTool(knowledge_base_path)
        self.model = InferenceClientModel(model_id=model_id)
        self.agent = CodeAgent(
            tools=[self.tool],
            model=self.model,
            max_steps=3,
            verbosity_level=1,  # keep it readable
            additional_authorized_imports=["json", "pandas", "pathlib"],
        )

    def remediate(self, discrepancy: dict) -> str:
        """
        Suggest a remediation for one discrepancy entry.

        Args:
            discrepancy: Dict with keys {id, severity, explanation}.
        Returns:
            str: Suggested remediation.
        """
        query = (
            f"Suggest a remediation for this discrepancy:\n"
            f"ID: {discrepancy['id']}\n"
            f"Severity: {discrepancy['severity']}\n"
            f"Explanation: {discrepancy['explanation']}"
        )
        return self.agent.run(query)
