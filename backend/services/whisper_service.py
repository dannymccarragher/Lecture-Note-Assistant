from faster_whisper import WhisperModel


model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)


async def transcribe_audio(
    file_bytes: bytes,
    filename: str
) -> dict:


    with open(filename, "wb") as f:
        f.write(file_bytes)


    segments, info = model.transcribe(
        filename
    )


    transcript_segments = []

    full_text = []


    for segment in segments:

        transcript_segments.append(
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip()
            }
        )

        full_text.append(
            segment.text.strip()
        )


    return {
        "text": " ".join(full_text),
        "segments": transcript_segments
    }