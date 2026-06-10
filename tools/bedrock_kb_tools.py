import boto3
from langchain_core.tools import tool


class BedrockKbTools:
    def __init__(self, knowledge_base_id: str, region_name: str = "us-east-2", aws_access_key_id: str = None, 
                 aws_secret_access_key: str = None):
        
        self.knowledge_base_id = knowledge_base_id
        self.client = boto3.client(
            "bedrock-agent-runtime",
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

    def search_knowledge_base_tool(self):
        @tool
        def search_knowledge_base(query: str) -> str:
            """
            Search the AWS Bedrock Knowledge Base for relevant FinIntel document knowledge.
            """
            response = self.client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={
                    "text": query
                },
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": 3
                    }
                },
            )

            results = response.get("retrievalResults", [])

            if not results:
                return "No relevant knowledge base results found."

            chunks = []

            for item in results:
                text = item["content"]["text"]
                score = item.get("score", None)

                chunks.append(
                    f"Score: {score}\n{text}"
                )

            return "\n\n".join(chunks)

        return search_knowledge_base