import os
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq


# Local embedding model (safe to load globally)
embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2",
)


# ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(
    name="lecture_chunks"
)


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY is missing")

    return Groq(api_key=api_key)


def chunk_transcript(segments):
    chunks = []
    current_text = []
    current_start = None
    current_end = None
    word_count = 0

    for segment in segments:

        if current_start is None:
            current_start = segment["start"]

        current_text.append(segment["text"])
        current_end = segment["end"]

        word_count += len(segment["text"].split())

        if word_count >= 500:

            chunks.append({
                "text": " ".join(current_text),
                "start": current_start,
                "end": current_end
            })

            overlap = " ".join(current_text).split()[-50:]

            current_text = [" ".join(overlap)]
            word_count = len(overlap)
            current_start = current_end

    if current_text:
        chunks.append({
            "text": " ".join(current_text),
            "start": current_start,
            "end": current_end
        })

    return chunks


# -----------------------------
# EMBED + STORE
# -----------------------------
async def embed_and_store(lecture_id: str, transcript: dict) -> None:

    chunks = chunk_transcript(transcript["segments"])

    for i, chunk in enumerate(chunks):

        embedding = embedding_model.encode(chunk["text"]).tolist()

        collection.add(
            ids=[f"{lecture_id}_{i}"],
            embeddings=[embedding],
            documents=[chunk["text"]],
            metadatas=[{
                "lecture_id": lecture_id,
                "start": chunk["start"],
                "end": chunk["end"]
            }]
        )


# -----------------------------
# SEMANTIC SEARCH
# -----------------------------
async def semantic_search(lecture_id: str, query: str) -> dict:

    query_embedding = embedding_model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where={"lecture_id": lecture_id}
    )

    chunks = results["documents"][0]
    metadata = results["metadatas"][0]

    context = "\n\n".join(chunks)

    prompt = f"""
Answer using only the lecture content.

Lecture:
{context}

Question:
{query}
"""

    groq_client = get_groq_client()

    response = groq_client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    sources = [
        {
            "text": text,
            "start": meta["start"],
            "end": meta["end"]
        }
        for text, meta in zip(chunks, metadata)
    ]

    return {
        "answer": response.choices[0].message.content,
        "sources": sources
    }