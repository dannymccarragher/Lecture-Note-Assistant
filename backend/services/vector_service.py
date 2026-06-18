import os
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(
    name="lecture_chunks"
)

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from environment variables")

    return Groq(api_key=api_key)


# -----------------------------
# Chunking transcript
# -----------------------------
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

        # Create chunk every ~500 words
        if word_count >= 500:
            full_text = " ".join(current_text)

            chunks.append({
                "text": full_text,
                "start": current_start,
                "end": current_end
            })

            # overlap last 50 words
            overlap_words = full_text.split()[-50:]
            current_text = [" ".join(overlap_words)]

            word_count = len(overlap_words)
            current_start = current_end

    # final chunk
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

    try:
        # 1. Embed query
        query_embedding = embedding_model.encode(query).tolist()

        # 2. Search vector DB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            where={"lecture_id": lecture_id}
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        # Handle empty results safely
        if not documents:
            return {
                "answer": "No relevant lecture content found.",
                "sources": []
            }

        context = "\n\n".join(documents)

        # 3. Build prompt
        prompt = f"""
You are a helpful assistant that answers using ONLY the lecture content below.

Lecture Context:
{context}

Question:
{query}
"""

        # 4. Call Groq
        groq_client = get_groq_client()

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You answer only using provided lecture context."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2
        )

        answer = response.choices[0].message.content

        # 5. Build sources safely
        sources = []
        for doc, meta in zip(documents, metadatas):
            sources.append({
                "text": doc,
                "start": meta.get("start"),
                "end": meta.get("end")
            })

        return {
            "answer": answer,
            "sources": sources
        }

    except Exception as e:
        return {
            "answer": f"Error during semantic search: {str(e)}",
            "sources": []
        }