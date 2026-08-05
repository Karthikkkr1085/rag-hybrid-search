from src.generation.citation import CitationGenerator
from src.generation.prompt import PromptBuilder


def test_prompt_builder_numbers_contexts():
    builder = PromptBuilder()
    contexts = [
        {
            "document": "This is page one.",
            "metadata": {"source": "Doc.pdf", "page": 1, "chunk_id": 11},
        },
        {
            "document": "This is page two.",
            "metadata": {"source": "Doc.pdf", "page": 2, "chunk_id": 22},
        },
    ]

    prompt, citation_map = builder.build_prompt("What is the policy?", contexts)

    assert "[1]" in prompt
    assert "Chunk ID: 11" in prompt
    assert citation_map[1]["source"] == "Doc.pdf"
    assert citation_map[2]["page"] == 2


def test_citation_generator_extracts_and_validates_ids():
    citation_map = {
        1: {"source": "Doc.pdf", "page": 1, "chunk_id": 11, "content": "page one"},
        2: {"source": "Doc.pdf", "page": 2, "chunk_id": 22, "content": "page two"},
    }
    generator = CitationGenerator()
    answer = "The policy is defined on page one. [1] It refers to the next section. [2]"

    citations = generator.generate(answer, citation_map)
    assert len(citations) == 2
    assert citations[0]["id"] == 1
    assert citations[1]["source"] == "Doc.pdf"
    assert generator.calculate_confidence(answer, citation_map) == 1.0

    invalid_answer = "This is unsupported. [3]"
    sanitized = generator.remove_invalid_citations(invalid_answer, citation_map)
    assert "[3]" not in sanitized
    assert sanitized == "This is unsupported."
