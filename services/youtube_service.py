import os
import re
import logging
import requests
from pytube import YouTube
import whisper
import google.generativeai as genai
from config import (
    CONVERSATION_HISTORY_LIMIT,
    SUMMARY_WORD_LIMIT,
    MAX_TRANSCRIPT_LENGTH
)
from services.pdf_service import process_file
from bs4 import BeautifulSoup
import wikipedia
import wikipedia.exceptions

# In-memory caches
transcript_cache = {}
file_contents_cache = {}
website_contents_cache = {}
wikipedia_contents_cache = {}
summary_cache = {}
answer_cache = {}

# Conversation history: user_history[username] = [ { "question": "...", "answer": "..." }, ... ]
user_history = {}

# Load Whisper model once
whisper_model = whisper.load_model("base")

# Re-configure generative AI in case it's needed again (optional—already configured in config.py)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))



def download_audio(video_id):
    try:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        yt = YouTube(youtube_url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        if not audio_stream:
            raise RuntimeError("No audio stream found for the video.")
        audio_file = audio_stream.download(filename=f"{video_id}.mp4")
        logging.info(f"Downloaded audio for video ID {video_id}")
        return audio_file
    except Exception as e:
        raise RuntimeError(f"Error downloading audio for video {video_id}: {e}")

def transcribe_audio(audio_file_path, delete_after=True):
    try:
        result = whisper_model.transcribe(audio_file_path)
        transcript = result['text']
        return transcript
    except Exception as e:
        raise RuntimeError(f"Transcription error: {e}")
    finally:
        if delete_after and os.path.exists(audio_file_path):
            os.remove(audio_file_path)

def fetch_transcript_from_external_service(video_id):
    """
    An example of external transcript fetch. 
    If you have a separate service that returns transcripts, you can implement it here.
    """
    transcript_url = "http://localhost:5000/get_transcript"  # Example only
    try:
        r = requests.post(transcript_url, json={"video_url": f"https://www.youtube.com/watch?v={video_id}"})
        r.raise_for_status()
        return r.json().get("transcript")
    except Exception as e:
        logging.warning(f"External transcript fetch failed: {e}")
        return None

def get_transcript_text(video_id):
    if video_id in transcript_cache:
        return transcript_cache[video_id]
    txt = fetch_transcript_from_external_service(video_id)
    if not txt:
        audio_file = download_audio(video_id)
        txt = transcribe_audio(audio_file)
    transcript_cache[video_id] = txt
    return txt

def fetch_video_metadata(video_id):
    try:
        url = f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json"
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch video metadata: {e}")

def get_file_content(file_name, file_extension, file_path):
    if file_name in file_contents_cache:
        return file_contents_cache[file_name]
    if file_extension.lower() in ['mp3', 'mp4', 'wav', 'avi', 'mkv', 'flv', 'mov']:
        txt = transcribe_audio(file_path, delete_after=False)
    else:
        txt = process_file(file_path, file_extension)
    file_contents_cache[file_name] = txt
    return txt

def get_website_content(url):
    if url in website_contents_cache:
        return website_contents_cache[url]
    try:
        r = requests.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text(separator=' ', strip=True)
        website_contents_cache[url] = text
        return text
    except Exception as e:
        raise RuntimeError(f"Failed to fetch website content: {e}")

def get_wikipedia_content(title):
    if title in wikipedia_contents_cache:
        return wikipedia_contents_cache[title]
    try:
        page = wikipedia.page(title)
        c = page.content
        wikipedia_contents_cache[title] = c
        return c
    except wikipedia.exceptions.DisambiguationError as e:
        raise RuntimeError(f"Disambiguation for '{title}': {e.options}")
    except wikipedia.exceptions.PageError:
        raise RuntimeError(f"Page '{title}' does not exist.")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch Wikipedia content: {e}")

def generate_summary(content_text, metadata):
    try:
        model = genai.GenerativeModel("gemini-pro")
        if len(content_text) > MAX_TRANSCRIPT_LENGTH:
            content_text = content_text[:MAX_TRANSCRIPT_LENGTH]
        prompt = (
            f"You are Dev, a professional and creative summarizer. "
            f"Carefully review the following content and produce a detailed, thorough summary:\n\n"
            f"Title: {metadata.get('title', '')}\n"
            f"Author: {metadata.get('author_name', '')}\n\n"
            f"{content_text}\n\n"
            f"Highlight key points in a concise, well-structured manner."
        )
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        raise RuntimeError(f"Summarization error: {e}")

def merge_summaries(*summaries):
    try:
        model = genai.GenerativeModel("gemini-pro")
        joined = "\n\n".join([f"Summary {i+1}:\n{s}" for i, s in enumerate(summaries)])
        prompt = (
            f"You are Dev, a skilled summarizer. Combine the partial summaries below into one cohesive, "
            f"thorough, and refined summary:\n\n"
            f"{joined}\n\n"
            f"Final summary:"
        )
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        raise RuntimeError(f"merge_summaries error: {e}")

def merge_answers(*answers, question):
    try:
        model = genai.GenerativeModel("gemini-pro")
        valid = [a for a in answers if a.strip()]
        if not valid:
            return "No valid information available to answer the question."
        joined = "\n\n".join([f"Answer {i+1}:\n{ans}" for i, ans in enumerate(valid)])
        prompt = (
            f"You are Dev, a dedicated assistant. The user asked:\n"
            f"{question}\n\n"
            f"Below are partial answers from various sources:\n"
            f"{joined}\n\n"
            f"Combine them into a single, coherent, and thorough answer:"
        )
        final = model.generate_content(prompt).text.strip()
        return final or "No valid information to merge."
    except Exception as e:
        raise RuntimeError(f"merge_answers error: {e}")

def answer_question(content_text, metadata, user_question, conversation_history=None):
    conversation_history = conversation_history or []

    try:
        model = genai.GenerativeModel("gemini-pro")
        if len(content_text) > MAX_TRANSCRIPT_LENGTH:
            content_text = content_text[:MAX_TRANSCRIPT_LENGTH]

        # Build conversation context from the last N entries
        convo_str = ""
        for entry in conversation_history[-CONVERSATION_HISTORY_LIMIT:]:
            q = entry['question']
            a = entry['answer']
            convo_str += f"User: {q}\nDev: {a}\n"

        prompt = (
            f"You are Dev, a dedicated and professional assistant. Here is the recent conversation:\n\n"
            f"{convo_str}\n\n"
            f"Below is reference content that may be useful:\n{content_text}\n\n"
            f"Now, the user asks:\n{user_question}\n\n"
            f"Provide a comprehensive, thoughtful response, addressing all relevant details."
        )

        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        raise RuntimeError(f"answer_question error: {e}")

def answer_general_question(user_question, conversation_history=None):
    conversation_history = conversation_history or []

    try:
        model = genai.GenerativeModel("gemini-pro")

        convo_str = ""
        for entry in conversation_history[-CONVERSATION_HISTORY_LIMIT:]:
            q = entry['question']
            a = entry['answer']
            convo_str += f"User: {q}\nDev: {a}\n"

        prompt = (
            f"You are Dev, a professional and creative assistant. Here is the recent conversation:\n"
            f"{convo_str}\n\n"
            f"The user says: \"{user_question}\"\n\n"
            f"Please provide a thorough, considerate response."
        )

        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"answer_general_question error: {e}")
        return "An error occurred while attempting to answer."

def end_conversation():
    """
    Clears all in-memory caches and conversation histories.
    Useful if you want to start fresh or upon user logout.
    """
    global transcript_cache, file_contents_cache, website_contents_cache
    global wikipedia_contents_cache, summary_cache, answer_cache, user_history

    transcript_cache.clear()
    file_contents_cache.clear()
    website_contents_cache.clear()
    wikipedia_contents_cache.clear()
    summary_cache.clear()
    answer_cache.clear()
    user_history.clear()
    logging.info("All caches and conversation history cleared.")