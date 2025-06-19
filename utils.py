import io
import openai
import os

# Set OpenAI API key from environment vars
openai.api_key = os.getenv("OPENAI_API_KEY")

def transcribe_audio(file_stream):
    """
    Transcribe the audio using OpenAI's Whisper model.
    Expects a file-like object.
    """
    file_stream.seek(0)
    transcript = openai.Audio.transcribe("whisper-1", file_stream)
    return transcript["text"]

def extract_moods(raw_text):
    """
    Use OpenAI's text completion API to extract moods.
    Returns a list of adjectives.
    """
    prompt = (
        f"Extract the underlying mood of the following text as a comma-separated list of vivid adjectives. \n"
        f"Text: {raw_text}"
    )
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=50,
        temperature=0.7
    )
    moods = response.choices[0].text.strip().split(',')
    return [m.strip() for m in moods if m.strip()]

def extract_topics(raw_text):
    """
    Use OpenAI's text completion API to extract topics.
    Returns a list of clear and descriptive topics.
    """
    prompt = (
        f"Identify the key topics or tags from the following text as a comma-separated list. "
        f"Text: {raw_text}"
    )
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=50,
        temperature=0.7
    )
    topics = response.choices[0].text.strip().split(',')
    return [t.strip() for t in topics if t.strip()]

def polish_text(raw_text):
    """
    Use OpenAI's text completion API to produce
    a polished version of the journal text.
    """
    prompt = (
        f"Improve the following text by correcting grammar and making it more engaging and coherent. "
        f"Provide a polished version that reads naturally. \n"
        f"Text: {raw_text}"
    )
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150,
        temperature=0.7
    )
    return response.choices[0].text.strip()