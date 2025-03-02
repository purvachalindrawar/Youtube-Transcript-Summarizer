import os
import re
import subprocess
import streamlit as st
import yt_dlp
import requests
from PIL import Image
import whisper
from io import BytesIO
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled
from translate import Translator  # Replaced googletrans with translate
import streamlit.components.v1 as components  # Import components for HTML/JS
import openai
from dotenv import load_dotenv

# Initialize the translator outside of functions to avoid scope issues
translator = Translator(to_lang="en")

# Add these constants after the imports
load_dotenv()  # Load environment variables from .env file

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")

# Function to sanitize filenames by removing invalid characters
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*#:]', '_', filename).strip()

# Function to download video using yt-dlp and get thumbnail URL
def download_video(video_url):
    ydl_opts = {
        'format': 'best',
        'noplaylist': True,
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        video_title = info.get('title', None)
        sanitized_title = sanitize_filename(video_title)
        thumbnail_url = info.get('thumbnail', None)

        st.write(f"Video Title: {video_title}")  # Debug statement
        st.write(f"Thumbnail URL: {thumbnail_url}")  # Debug statement

        return sanitized_title, thumbnail_url

# Function to extract audio using yt-dlp with fallback formats
def extract_audio(video_url):
    sanitized_title = sanitize_filename(video_url.split('=')[-1])  # Use video ID as filename
    audio_dir = "extracted_audio"
    os.makedirs(audio_dir, exist_ok=True)
    audio_file_path = os.path.join(audio_dir, f"{sanitized_title}.mp3")

    formats_to_try = ['bestaudio/best', 'worst', 'best']

    for format_id in formats_to_try:
        ydl_opts = {
            'format': format_id,
            'extractaudio': True,
            'audioformat': 'mp3',
            'outtmpl': audio_file_path.rstrip('.mp3'),
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([video_url])
                return audio_file_path
            except yt_dlp.utils.ExtractorError as e:
                st.warning(f"Extractor Error with format {format_id}: {e}")
            except Exception as e:
                st.warning(f"An error occurred with format {format_id}: {e}")
    
    st.error("All format attempts failed for audio extraction.")
    return None

# Function to convert audio to text using Whisper
def audio_to_text_in_chunks(audio_file_path, language=None):
    model = whisper.load_model("tiny")
    
    if not os.path.exists(audio_file_path):
        st.error(f"Error: Audio file not found at {audio_file_path}")
        return

    result = model.transcribe(audio_file_path, language=language, fp16=True, verbose=False)
    
    partial_transcript = ""
    for segment in result['segments']:
        partial_transcript += segment['text'] + " "
        yield partial_transcript

# Function to get all available transcripts and choose the first one available
def fetch_first_available_transcript(video_id):
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        for transcript in transcripts:
            try:
                transcript_data = transcript.fetch()
                transcript_text = " ".join([entry['text'] for entry in transcript_data])
                return transcript_text
            except Exception as e:
                st.warning(f"Error fetching transcript: {e}")
        
        return None
    except NoTranscriptFound:
        return None
    except TranscriptsDisabled:
        return None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return None

# Function to translate text to English
# def translate_to_english(text):
#     if text:  # Make sure text is not None or empty
#         try:
#             translated = translator.translate(text, src='auto', dest='en')  # Automatic source language detection
#             return translated.text
#         except Exception as e:
#             st.error(f"Error during translation: {e}")
#     else:
#         st.warning("Text is empty; cannot translate.")
#     return None

def translate_to_english(text):
    if text:  # Ensure text is not None or empty
        try:
            translated_text = translator.translate(text)  # Translate to English
            return translated_text
        except Exception as e:
            st.error(f"Error during translation: {e}")
    else:
        st.warning("Text is empty; cannot translate.")
    return None

# JavaScript alert for notifying the user
def show_js_alert():
    js_code = """
    <script>
    alert("No transcript is available. Click OK to proceed with audio extraction.");
    </script>
    """
    components.html(js_code)

# Function to summarize the transcript using Azure OpenAI API
def summarize_transcript(text):
    """
    Summarize the transcript using Azure OpenAI API
    """
    if not text:
        return None
        
    try:
        # Configure Azure OpenAI client
        client = openai.AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version="2023-05-15",
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )

        # Prepare the prompt for summarization
        prompt = f"""Please provide a concise summary of the following transcript:
        
        {text}
        
        Summary:"""

        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,  # This should match your deployment name
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes video transcripts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        summary = response.choices[0].message.content.strip()
        return summary

    except Exception as e:
        st.error(f"Error during summarization: {str(e)}")
        return None

# Streamlit application interface
def main():
    st.title("Universal Video Downloader and Transcript Fetcher with English Translation")

    video_url = st.text_input("Enter the video URL: ")

    if st.button("Get Transcript and Extract Audio"):
        if video_url:
            try:
                video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", video_url)
                if video_id_match:
                    video_id = video_id_match.group(1)
                else:
                    st.error("Invalid YouTube URL")
                    return

                with st.spinner("Checking for available transcript..."):
                    transcript = fetch_first_available_transcript(video_id)

                if transcript:
                    st.success("Transcript found! Here it is:")
                    st.write(transcript)

                    # Translate to English
                    st.info("Translating to English...")
                    english_translation = translate_to_english(transcript)
                    if english_translation:
                        st.write("**English Translation:**")
                        st.write(english_translation)
                        
                        # Add summarization
                        st.info("Generating summary...")
                        summary = summarize_transcript(english_translation)
                        if summary:
                            st.write("**Summary:**")
                            st.write(summary)
                else:
                    show_js_alert()

                    with st.spinner("Fetching video info..."):
                        video_title, thumbnail_url = download_video(video_url)
                        st.success("Video info fetched successfully!")

                    if thumbnail_url:
                        try:
                            response = requests.get(thumbnail_url)
                            response.raise_for_status()  # Raise an error for bad responses
                            img = Image.open(BytesIO(response.content))
                            st.image(img, caption="Video Thumbnail", use_column_width=True)
                        except Exception as e:
                            st.error(f"Error fetching thumbnail: {e}")
                    else:
                        st.warning("Thumbnail not available.")

                    with st.spinner("Extracting audio..."):
                        audio_file_path = extract_audio(video_url)
                        if audio_file_path:
                            st.success("Audio extracted successfully!")
                            st.audio(audio_file_path)
                        else:
                            st.error("Audio extraction failed.")
                            return

                    st.info("Generating transcript in real-time...")
                    transcript_placeholder = st.empty()

                    final_transcript = ""
                    for partial_transcript in audio_to_text_in_chunks(audio_file_path):
                        final_transcript = partial_transcript
                        transcript_placeholder.text_area("Transcript in progress:", partial_transcript)

                    if final_transcript:
                        st.info("Translating final transcript to English...")
                        english_translation = translate_to_english(final_transcript)
                        if english_translation:
                            st.write("**English Translation of Generated Transcript:**")
                            st.write(english_translation)
                            
                            # Add summarization for Whisper-generated transcript
                            st.info("Generating summary...")
                            summary = summarize_transcript(english_translation)
                            if summary:
                                st.write("**Summary:**")
                                st.write(summary)

            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Please enter a valid URL.")

if __name__ == "__main__":
    main()