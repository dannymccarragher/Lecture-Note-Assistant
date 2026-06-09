import io
import os
import openai


async def transcribe_audio(file_bytes: bytes, filename: str) -> dict:
    """
    Sends audio to OpenAI Whisper and returns transcript text + timestamped segments.
    Returns: {"text": str, "segments": [{"start": float, "end": float, "text": str}]}
    """
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    audio_file = io.BytesIO(file_bytes)
    audio_file.name = filename

    response = await client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="verbose_json",
        timestamp_granularities=["segment"],
    )

    segments = [
        {"start": seg.start, "end": seg.end, "text": seg.text.strip()}
        for seg in response.segments
    ]

    return {"text": response.text, "segments": segments}
