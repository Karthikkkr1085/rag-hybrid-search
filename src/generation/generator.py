import time

from src.evaluation.evaluate import Evaluator
from src.generation.citation import CitationGenerator
from src.generation.citation_aligner import CitationAligner
from src.generation.citation_verifier import CitationVerifier
from src.generation.llm import LLM
from src.generation.postprocessor import PostProcessor
from src.generation.prompt import PromptBuilder
from src.generation.verifier import Verifier
from src.utils.cost import estimate_cost

FALLBACK_ANSWER = "I couldn't find the answer in the provided documents."


class Generator:
    """
    End-to-end answer generation pipeline.
    """

    def __init__(self):
        self.prompt_builder = PromptBuilder()
        self.llm = LLM()
        self.verifier = Verifier()
        self.citation = CitationGenerator()
        self.citation_verifier = CitationVerifier()
        self.postprocessor = PostProcessor()
        self.evaluator = Evaluator()
        self.citation_aligner = CitationAligner()
        self.aligner = CitationAligner()

    def _calculate_retrieval_confidence(
        self,
        contexts: list,
        settings: dict | None = None,
    ) -> float:
        if not contexts:
            return 0.0

        scores = [
            c.get("rerank_score") for c in contexts if c.get("rerank_score") is not None
        ]

        if not scores:
            return 0.0

        confidence = sum(scores) / len(scores)

        return max(0.0, min(1.0, confidence))

    def _process_answer(
        self,
        raw_response: str,
        contexts: list,
        citation_map: dict[int, dict],
        settings: dict | None = None,
    ) -> dict:
        answer = raw_response.strip()
        answer = self.citation.remove_sources_section(answer)

        # Add/fix citations first
        answer = self.aligner.align(
            answer,
            citation_map,
        )

        # Then clean up formatting
        answer = self.postprocessor.process(answer)

        verification_confidence = self.verifier.verify(
            answer=answer,
            contexts=contexts,
        )

        verification = self.citation_verifier.verify(
            answer=answer,
            citation_map=citation_map,
        )
        if verification["unsupported_claims"]:
            print("Citation verification issues:", verification["unsupported_claims"])

        valid_ids = {
            citation["id"]
            for citation in verification["citations"]
            if citation.get("valid")
        }
        answer = self.citation.remove_invalid_citations(answer, valid_ids)

        citations = [
            citation for citation in verification["citations"] if citation.get("valid")
        ]
        citation_summary = verification["citation_summary"]
        citation_confidence = verification["citation_confidence"]
        retrieval_confidence = self._calculate_retrieval_confidence(contexts, settings)
        print("\n========== AFTER POSTPROCESS ==========")
        print(answer)

        answer = self.citation.remove_invalid_citations(
            answer,
            valid_ids,
        )

        print("\n========== AFTER REMOVE INVALID ==========")
        print(answer)

        print("\n========== CONFIDENCE DEBUG ==========")
        print("Retrieval Confidence   :", retrieval_confidence)
        print("Citation Confidence    :", citation_confidence)
        print("Verification Confidence:", verification_confidence)
        print("======================================")

        print("\n========== CONFIDENCE DEBUG ==========")
        print(f"Retrieval   : {retrieval_confidence}")
        print(f"Citation    : {citation_confidence}")
        print(f"Verification: {verification_confidence}")

        overall_confidence = (
            retrieval_confidence + citation_confidence + verification_confidence
        ) / 3.0

        overall_confidence = max(0.0, min(1.0, overall_confidence))

        print(f"Overall     : {overall_confidence}")
        print("======================================")

        verified = citation_summary["invalid"] == 0 and citation_summary["valid"] > 0

        return {
            "answer": answer,
            "verified": verified,
            "citations": citations,
            "citation_summary": citation_summary,
            "retrieval_confidence": retrieval_confidence,
            "citation_confidence": citation_confidence,
            "confidence": overall_confidence,
        }

    def generate(
        self,
        query: str,
        contexts: list,
        settings: dict | None = None,
        history: list[dict] | None = None,
        conversation_summary: str | None = None,
    ) -> dict:
        """
        Generate an answer from retrieved contexts.
        """
        total_start = time.perf_counter()
        settings = settings or {}

        if not contexts:
            return {
                "answer": FALLBACK_ANSWER,
                "verified": False,
                "citation_summary": {
                    "valid": 0,
                    "invalid": 0,
                    "coverage": 0,
                    "confidence_level": "Low",
                },
                "citations": [],
                "retrieval_confidence": 0.0,
                "citation_confidence": 0.0,
                "confidence": 0.0,
            }

        prompt, citation_map = self.prompt_builder.build_prompt(
            query=query,
            contexts=contexts,
            history=history,
            conversation_summary=conversation_summary,
        )

        print("\n================ PROMPT ================")
        print(prompt)
        print("========================================")
        print("Citation map:", citation_map)

        llm_start = time.perf_counter()
        llm_response = self.llm.generate(
            prompt,
            model=settings.get("model"),
            temperature=settings.get("temperature", 0.2),
            max_tokens=settings.get("max_tokens", 2048),
            provider=settings.get("provider"),
        )
        llm_time = round((time.perf_counter() - llm_start) * 1000, 2)

        raw_response = llm_response["content"]

        process_start = time.perf_counter()
        response = self._process_answer(
            raw_response,
            contexts,
            citation_map,
            settings,
        )
        postprocess_time = round((time.perf_counter() - process_start) * 1000, 2)

        response["usage"] = llm_response.get("usage", {})
        response["provider"] = llm_response.get("provider")
        response["model"] = llm_response.get("model")

        if response.get("usage"):
            response["cost"] = estimate_cost(
                model=response["model"],
                prompt_tokens=response["usage"].get("prompt_tokens", 0),
                completion_tokens=response["usage"].get("completion_tokens", 0),
            )
            print("================ COST ================")
            print(response["cost"])
            print("======================================")

        total_time = round((time.perf_counter() - total_start) * 1000, 2)
        response["metrics"] = {
            "llm_ms": llm_time,
            "postprocess_ms": postprocess_time,
            "total_ms": total_time,
        }
        response["evaluation"] = self.evaluator.evaluate(
            retrieved_docs=contexts,
            reranked_docs=contexts,
            answer=response["answer"],
            retrieval_time_ms=0,
            generation_time_ms=llm_time,
        )

        print("\n================ RAW LLM RESPONSE ================")
        print(raw_response)
        print("==================================================")
        print("Verification confidence:", response["confidence"])
        print("Citation summary:", response.get("citation_summary"))
        print("Generated citations:", [c["id"] for c in response["citations"]])
        print("Token Usage:", response.get("usage"))
        print("Performance Metrics:", response["metrics"])
        print("\n================ POST PROCESSED ================")
        print(response["answer"])
        print("===============================================")
        print("\n========== SENDING TO FRONTEND ==========")
        print(response["answer"])
        print("=========================================")
        return response

    def stream(
        self,
        query: str,
        contexts: list,
        settings: dict | None = None,
        history: list[dict] | None = None,
        conversation_summary: str | None = None,
    ):
        """Yield token deltas, then return final verification/citation metadata."""
        settings = settings or {}

        if not contexts:
            yield {
                "type": "done",
                "answer": FALLBACK_ANSWER,
                "verified": False,
                "citation_summary": {
                    "valid": 0,
                    "invalid": 0,
                    "coverage": 0,
                    "confidence_level": "Low",
                },
                "citations": [],
                "retrieval_confidence": 0.0,
                "citation_confidence": 0.0,
                "confidence": 0.0,
            }
            return

        prompt, citation_map = self.prompt_builder.build_prompt(
            query=query,
            contexts=contexts,
            history=history,
            conversation_summary=conversation_summary,
        )
        raw_response = ""

        print("\n================ PROMPT ================")
        print(prompt)
        print("========================================")
        print("Citation map:", citation_map)

        for token in self.llm.stream(
            prompt,
            model=settings.get("model"),
            temperature=settings.get("temperature", 0.2),
            max_tokens=settings.get("max_tokens", 2048),
            provider=settings.get("provider"),
        ):
            raw_response += token

            # Stream each token to the frontend
            yield {
                "type": "token",
                "token": token,
            }

        # Process the complete answer after generation finishes
        response = self._process_answer(
            raw_response,
            contexts,
            citation_map,
            settings,
        )

        print("Citation summary:", response.get("citation_summary"))

        # Send the final verified answer
        yield {
            "type": "done",
            **response,
        }
