import dspy
import argparse
import json
from pypdf import PdfReader
from typing import List, Dict, Any, Union

lm = dspy.LM(
    "ollama_chat/gemma3:12b",
    api_base="http://192.168.178.107:11434",
    api_key="",
    response_format={"type": "json_object"},
)
dspy.configure(lm=lm)


def read_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 300) -> List[str]:
    """Split text into overlapping chunks of specified size."""
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        if end < text_length and end - start == chunk_size:
            last_period = text.rfind(".", start, end)
            last_newline = text.rfind("\n", start, end)
            break_point = max(last_period, last_newline)

            if break_point > start + overlap:
                end = break_point + 1

        chunks.append(text[start:end])
        start = end - overlap if end < text_length else text_length

    return chunks


class DocumentSectionSignature(dspy.Signature):
    """Extract structured section information from document text."""

    document_chunk = dspy.InputField(desc="A chunk of text from a document")
    sections = dspy.OutputField(
        desc="Dictionary of sections found, each with section number, title and text content in a correct json format. [{'section': '', 'title': '', 'text': ''}, {'section': '', 'title': '', 'text': ''} ...]"
    )


# Create the DSPy module for section extraction
class DocumentSectionExtractor(dspy.Module):
    def __init__(self):
        super().__init__()
        self.extract = dspy.ChainOfThought(DocumentSectionSignature)

    def forward(self, document_chunk: str) -> Dict[str, Any]:
        """
        You are an expert at legal document analysis and extraction.
        You are given a chunk of text from a law. Your task is to extract structured sections from this text.
        Illustrations are part of the section they appear under.
        Ignore incomplete sections at the end or beginning of the document (if found)

        """
        result = self.extract(document_chunk=document_chunk)
        breakpoint()
        return {"sections": result.sections}


def process_document(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Process a PDF document and extract structured sections.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of extracted sections with their details
    """
    print(f"Reading PDF: {pdf_path}")
    full_text = read_pdf(pdf_path)

    # 2. Chunk the text
    chunks = chunk_text(full_text, chunk_size=2000, overlap=300)
    print(f"Created {len(chunks)} chunks")

    extractor = DocumentSectionExtractor()

    all_results = []

    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}")

        # Extract structured data from this chunk
        result = extractor(document_chunk=chunk)
        all_results.append({"chunk_id": i + 1, "content": result["sections"]})

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured sections from a PDF document"
    )
    parser.add_argument("pdf_path", type=str, help="Path to the PDF document")
    parser.add_argument("--output", type=str, help="Output text file path (optional)")

    args = parser.parse_args()

    results = process_document(args.pdf_path)

    output_file = args.output or f"{args.pdf_path.rsplit('.', 1)[0]}_sections.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"DOCUMENT SECTION ANALYSIS: {args.pdf_path}\n")
        f.write("=" * 80 + "\n\n")

        for result in results:
            f.write(f"CHUNK {result['chunk_id']}:\n")
            f.write("-" * 80 + "\n")

            # Just write the raw content directly without trying to parse as JSON
            content = result["content"]
            f.write(str(content) + "\n\n")

            f.write("-" * 80 + "\n\n")

    print(f"Results saved to {output_file}")


if __name__ == "__main__":
    main()
