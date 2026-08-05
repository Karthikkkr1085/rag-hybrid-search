import re


class CitationGenerator:
    """
    Generate and validate citations from the model output.
    """

    def __init__(self):
        self._citation_pattern = re.compile(r"\[(\d+)\]")
        self._citation_group_pattern = re.compile(r"((?:\[\d+\])+)")

    def extract_ids(self, answer: str) -> list[int]:
        return [int(match) for match in self._citation_pattern.findall(answer)]

    def remove_sources_section(self, answer: str) -> str:
        if "Sources:" in answer:
            return answer.split("Sources:", 1)[0].strip()
        return answer

    def remove_invalid_citations(self, answer: str, valid_ids: set[int]) -> str:
        def replace(match: re.Match) -> str:
            ids = [
                int(value) for value in self._citation_pattern.findall(match.group(0))
            ]
            kept = [cid for cid in ids if cid in valid_ids]
            return "".join(f"[{cid}]" for cid in kept)

        sanitized = self._citation_group_pattern.sub(replace, answer)
        sanitized = sanitized.replace("[]", "")
        return re.sub(r"\s{2,}", " ", sanitized).strip()

    def generate(
        self,
        answer: str,
        citation_map: dict[int, dict],
        only_ids: set[int] | None = None,
    ) -> list[dict]:
        citation_ids: list[int] = []
        source_ids = self.extract_ids(answer)
        for citation_id in source_ids:
            if citation_id in citation_map and citation_id not in citation_ids:
                citation_ids.append(citation_id)

        if only_ids is not None:
            citation_ids = [
                citation_id for citation_id in citation_ids if citation_id in only_ids
            ]

        citations = []
        for citation_id in citation_ids:
            metadata = citation_map[citation_id]
            citations.append(
                {
                    "id": citation_id,
                    "source": metadata["source"],
                    "page": metadata["page"],
                    "chunk_id": metadata["chunk_id"],
                    "content": metadata["content"],
                    "confidence": 1.0,
                }
            )

        return citations

    def calculate_confidence(self, answer: str, citation_map: dict[int, dict]) -> float:
        cited_ids = self.extract_ids(answer)
        if not cited_ids:
            return 0.0

        valid = [
            citation_id for citation_id in cited_ids if citation_id in citation_map
        ]
        return len(valid) / len(cited_ids)
