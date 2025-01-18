import os
import re

import aiohttp


class InternetTools:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _process_citations(self, answer: str, citations: list[str]) -> str:
        """Process citations in the answer and return formatted answer with citations."""
        citation_indices = [int(idx) - 1 for idx in re.findall(r"\[(\d+)\]", answer)]
        relevant_citations = [citations[idx] for idx in citation_indices if idx < len(citations)]
        processed_answer = re.sub(r"\[\d+\]", "", answer).strip()

        if relevant_citations:
            citation_text = "\n".join(relevant_citations)
            processed_answer += f"\n\ncitations:\n{citation_text}"

        return processed_answer

    async def ask(self, query: str) -> tuple[str, list[str]]:
        """Ask a question and get response with relevant citations.

        Args:
            query: The question to ask

        Returns:
            Tuple of (answer_text, relevant_citation_urls)
        """
        payload = {
            "model": "llama-3.1-sonar-huge-128k-online",
            "return_images": False,
            "return_related_questions": False,
            "stream": False,
            "temperature": 0,
            "messages": [{"role": "system", "content": "Be concise and direct in your answers."}, {"role": "user", "content": query}],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, json=payload, headers=self.headers) as response:
                json_response = await response.json()

        answer = json_response["choices"][0]["message"]["content"]
        citations = json_response.get("citations", [])

        return self._process_citations(answer, citations)
