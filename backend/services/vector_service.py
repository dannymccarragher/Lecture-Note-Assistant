# TODO: Implement with OpenAI text-embedding-3-small + ChromaDB


async def embed_and_store(lecture_id: str, transcript: dict) -> None:
    """
    Chunks transcript (~500 tokens, 50-token overlap), embeds each chunk,
    and stores in ChromaDB under the given lecture_id.

    Input:  lecture_id str, transcript dict {"text": str, "segments": [...]}
    """
    raise NotImplementedError("Person 2: implement chunking + ChromaDB storage")


async def semantic_search(lecture_id: str, query: str) -> dict:
    """
    Embeds the query, retrieves top-k chunks from ChromaDB, passes them to
    Groq as context, and returns a grounded answer with source segments.

    Output: {"answer": str, "sources": [{"text": str, "start": float, "end": float}]}
    """
    raise NotImplementedError("Person 2: implement semantic search + Groq Q&A")
