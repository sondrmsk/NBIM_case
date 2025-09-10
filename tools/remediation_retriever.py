import json
from smolagents import Tool
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever


class RemediationRetrieverTool(Tool):
    name = "remediation_retriever"
    description = "Retrieve the most relevant remediation strategy for a given discrepancy explanation"
    inputs = {
        "explanation": {
            "type": "string",
            "description": "The discrepancy explanation (e.g. 'custodian mismatch: JPMORGAN_CHASE vs CUST/JPMORGANUS')."
        }
    }
    output_type = "string"

    def __init__(self, kb_path="knowledge_base.json", **kwargs):
        super().__init__(**kwargs)

        # Load the knowledge base JSON
        with open(kb_path, "r") as f:
            kb_data = json.load(f)

        # Convert KB entries to Documents
        source_docs = [
            Document(
                page_content=entry["remediation"],
                metadata={"pattern": entry["pattern"], "type": entry["type"]}
            )
            for entry in kb_data
        ]

        # Optional: split into chunks (keeps retrieval accurate if texts are longer)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=300, chunk_overlap=50, strip_whitespace=True
        )
        docs_processed = splitter.split_documents(source_docs)

        # Initialize retriever
        self.retriever = BM25Retriever.from_documents(docs_processed, k=3)

    def forward(self, explanation: str) -> str:
        """Retrieve the most relevant remediation strategy for the discrepancy explanation"""
        assert isinstance(explanation, str), "Explanation must be a string"

        # Query retriever
        docs = self.retriever.invoke(explanation)

        if not docs:
            return "No remediation found for this discrepancy."

        # Return the remediation text
        return docs[0].page_content
