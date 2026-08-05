import re
from collections import OrderedDict


class PostProcessor:
    def process(self, text: str) -> str:
        if not text:
            return text

        text = self._normalize(text)

        text = self._fix_markdown(text)

        text = self._remove_duplicate_bullets(text)
        text = self._remove_duplicate_paragraphs(text)

        text = self._fix_citations(text)

        return text.strip()

    def _fix_markdown(self, text: str) -> str:
        """
        Fix malformed markdown.
        """

        # ####Title -> #### Title
        text = re.sub(
            r"^(#{1,6})([^\s#])",
            r"\1 \2",
            text,
            flags=re.MULTILINE,
        )

        # Ensure blank line before headings
        text = re.sub(
            r"([^\n])\n(#{1,6}\s)",
            r"\1\n\n\2",
            text,
        )

        return text

    def _normalize(self, text: str) -> str:
        """Standardize line endings, excessive line breaks, and whitespace."""
        text = text.replace("\r\n", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text

    def _extract_citations(self, text: str) -> list[str]:
        """
        Extract citation IDs only from citation brackets.

        Supports:
        [1]
        [2][3]
        [1,2]
        [1, 2]
        """

        citations = []

        # Find everything inside [...]
        matches = re.findall(r"\[([^\]]+)\]", text)

        for match in matches:
            # Extract numbers only from inside the brackets
            citations.extend(re.findall(r"\d+", match))

        return sorted(set(citations), key=int)

    def _strip_citations(self, text: str) -> str:
        """Remove all citation brackets."""
        return re.sub(r"\s*\[[^\]]+\]", "", text)

    def _remove_duplicate_bullets(self, text: str) -> str:
        """
        Remove duplicate bullet points while preserving and merging citations.
        """
        lines = text.splitlines()
        seen = OrderedDict()
        output = []

        for line in lines:
            stripped = line.strip()

            # Ignore non-bullet lines
            if not re.match(r"^[-*•]\s*", stripped):
                output.append(line)
                continue

            # Generate normalization key for comparison
            key_text = self._strip_citations(stripped)
            key_text = re.sub(r"^[-*•]\s*", "", key_text)  # strip leading bullet marker
            key = " ".join(key_text.split()).lower()

            citations = self._extract_citations(stripped)

            if key not in seen:
                seen[key] = {
                    "output_index": len(output),
                    "citations": citations,
                    "base_text": key_text.strip(),
                }

                bullet_match = re.match(r"^([-*•]\s*)", stripped)
                bullet_prefix = bullet_match.group(1) if bullet_match else "- "

                merged_citations = (
                    " " + "".join(f"[{c}]" for c in sorted(set(citations), key=int))
                    if citations
                    else ""
                )

                output.append(f"{bullet_prefix}{key_text.strip()}{merged_citations}")
            else:
                entry = seen[key]
                existing_citations = entry["citations"]

                # Append any new unique citations found in the duplicate line
                for c in citations:
                    if c not in existing_citations:
                        existing_citations.append(c)

                # Reconstruct the line preserving original bullet style and merged citations
                bullet_match = re.match(r"^([-*•]\s*)", stripped)
                bullet_prefix = bullet_match.group(1) if bullet_match else "- "

                merged_citations_str = (
                    " "
                    + "".join(
                        f"[{c}]" for c in sorted(set(existing_citations), key=int)
                    )
                    if existing_citations
                    else ""
                )
                merged_line = (
                    f"{bullet_prefix}{entry['base_text']}{merged_citations_str}"
                )

                # Update output list at original index position
                output[entry["output_index"]] = merged_line

        return "\n".join(output)

    def _fix_citations(self, text: str) -> str:
        # word.2 -> word [2]
        text = re.sub(
            r"([A-Za-z)])\.(\d+)\b",
            r"\1 [\2]",
            text,
        )

        return text

    def _remove_duplicate_paragraphs(self, text: str) -> str:
        """Remove duplicate paragraphs ignoring citations and whitespace differences."""
        paragraphs = text.split("\n\n")

        seen = set()
        cleaned = []

        for para in paragraphs:
            key = self._strip_citations(para)
            key = " ".join(key.split()).lower()

            if key in seen:
                continue

            seen.add(key)
            cleaned.append(para)

        return "\n\n".join(cleaned)
