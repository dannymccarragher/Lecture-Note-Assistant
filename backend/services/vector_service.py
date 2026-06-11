import os
import chromadb
from openai import OpenAI
from groq import Groq


# API clients
openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


# ChromaDB storage
chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = chroma_client.get_or_create_collection(
    name="lecture_chunks"
)



def chunk_transcript(segments):
    """
    Split Whisper transcript into ~500 word chunks
    with 50 word overlap.
    """

    chunks = []

    current_text = []
    current_start = None
    current_end = None

    word_count = 0


    for segment in segments:

        if current_start is None:
            current_start = segment["start"]


        current_text.append(
            segment["text"]
        )

        current_end = segment["end"]


        word_count += len(
            segment["text"].split()
        )


        if word_count >= 500:

            chunks.append({
                "text": " ".join(current_text),
                "start": current_start,
                "end": current_end
            })


            # overlap
            overlap = " ".join(
                current_text
            ).split()[-50:]


            current_text = [
                " ".join(overlap)
            ]

            word_count = len(overlap)
            current_start = current_end


    if current_text:

        chunks.append({
            "text": " ".join(current_text),
            "start": current_start,
            "end": current_end
        })


    return chunks



# TODO: Implement with OpenAI text-embedding-3-small + ChromaDB
async def embed_and_store(lecture_id: str, transcript: dict) -> None:
    """
    Chunks transcript (~500 tokens, 50-token overlap), embeds each chunk,
    and stores in ChromaDB under the given lecture_id.
    """

    chunks = chunk_transcript(
        transcript["segments"]
    )


    for i, chunk in enumerate(chunks):

        # Create embedding
        embedding_response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=chunk["text"]
        )


        embedding = (
            embedding_response
            .data[0]
            .embedding
        )


        collection.add(
            ids=[
                f"{lecture_id}_{i}"
            ],

            embeddings=[
                embedding
            ],

            documents=[
                chunk["text"]
            ],

            metadatas=[
                {
                    "lecture_id": lecture_id,
                    "start": chunk["start"],
                    "end": chunk["end"]
                }
            ]
        )



# TODO: Implement semantic search + Groq Q&A
async def semantic_search(lecture_id: str, query: str) -> dict:
    """
    Embeds the query, retrieves top-k chunks from ChromaDB,
    sends context to Groq.
    """


    # Embed question
    query_embedding = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )


    results = collection.query(

        query_embeddings=[
            query_embedding.data[0].embedding
        ],

        n_results=5,

        where={
            "lecture_id": lecture_id
        }
    )


    chunks = results["documents"][0]
    metadata = results["metadatas"][0]


    context = "\n\n".join(chunks)


    prompt = f"""
Answer the question using only the lecture content.

Lecture:
{context}

Question:
{query}
"""


    response = groq_client.chat.completions.create(

        model="llama-3.1-70b-versatile",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.2
    )


    sources = []

    for text, meta in zip(chunks, metadata):

        sources.append({
            "text": text,
            "start": meta["start"],
            "end": meta["end"]
        })


    return {
        "answer": response.choices[0].message.content,
        "sources": sources
    }