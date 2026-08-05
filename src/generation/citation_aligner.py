import re

from sentence_transformers import SentenceTransformer, util


class CitationAligner:
    """
    Automatically attaches citations to generated answers.

    The LLM generates plain text without citations.
    This aligner matches each sentence against the retrieved
    document chunks and appends the most relevant citation(s).
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        threshold: float = 0.55,
    ):
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold

    def align(
        self,
        answer: str,
        citation_map: dict[int, dict],
    ) -> str:

        if not answer.strip():
            return answer

        if not citation_map:
            return answer

        # Split answer into sentences while preserving blank lines
        parts = answer.splitlines(keepends=True)

        chunk_ids = list(citation_map.keys())
        chunk_texts = [citation_map[idx]["content"] for idx in chunk_ids]

        chunk_embeddings = self.model.encode(
            chunk_texts,
            convert_to_tensor=True,
            normalize_embeddings=True,
        )

        output = []

        for part in parts:

            stripped = part.strip()
            print("\n----------------")
            print("LINE:", repr(stripped))
            print("HAS CITATION:", bool(re.search(r"\[\d+\]", stripped)))

            # Preserve blank lines
            if not stripped:
                output.append(part)
                continue

            # Skip markdown headings
            if stripped.startswith("#"):
                output.append(part)
                continue

            # Skip bullets containing only titles
            if len(stripped.split()) <= 2:
                output.append(part)
                continue

            # Skip if citation already exists
            if re.search(r"\[\d+\]", stripped):
                output.append(part)
                continue

            sentence_embedding = self.model.encode(
                stripped,
                convert_to_tensor=True,
                normalize_embeddings=True,
            )

            similarities = util.cos_sim(
                sentence_embedding,
                chunk_embeddings,
            )[0]

            scored = [
                (chunk_ids[i], float(similarities[i])) for i in range(len(chunk_ids))
            ]

            scored.sort(
                key=lambda x: x[1],
                reverse=True,
            )

            matched = [cid for cid, score in scored if score >= self.threshold]

            # Fallback to best chunk
            if not matched:
                matched = [scored[0][0]]

            citation_text = "".join(f"[{cid}]" for cid in sorted(set(matched)))

            output.append(stripped + " " + citation_text)

        return "".join(output)
