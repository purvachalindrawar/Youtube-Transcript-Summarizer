import os
import re
import subprocess
import streamlit as st
import yt_dlp
import requests
from PIL import Image
import whisper
import torch  # Import torch for CUDA support
from io import BytesIO
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled

# Function to sanitize filenames by removing invalid characters
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*#:]', '_', filename).strip()

# Function to download video using yt-dlp and get thumbnail URL
def download_video(video_url):
    ydl_opts = {
        'format': 'best',  # or try 'bestaudio/best'
        'noplaylist': True,
        'quiet': True,  # Set to True to suppress output
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)

            video_title = info.get('title', None)
            sanitized_title = sanitize_filename(video_title)
            thumbnail_url = info.get('thumbnail', None)
            return sanitized_title, thumbnail_url

        except Exception as e:
            st.error(f"Error fetching video info: {e}")
            return None, None

# Function to extract audio using yt-dlp
def extract_audio(video_url):
    sanitized_title = sanitize_filename(video_url.split('=')[-1])  # Use video ID as filename
    audio_file_path = f"downloads/{sanitized_title}.mp3"

    ydl_opts = {
        'format': 'bestaudio/best',  # Dynamically choose the best available audio format
        'outtmpl': audio_file_path,  # Save the audio file in the 'downloads' folder
        'noplaylist': True,
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Download the best audio available
            ydl.download([video_url])
        except Exception as e:
            st.error(f"Error downloading audio: {e}")

    return audio_file_path

# Function to convert audio to text using Whisper (translate to English)
def audio_to_text(audio_file_path):
    # Check if CUDA (GPU) is available, otherwise use CPU
    if torch.cuda.is_available():
        model = whisper.load_model("base", device="cuda")  # Load model on GPU
        model = model.half()  # Convert model to half precision (fp16) if GPU is available
    else:
        model = whisper.load_model("base", device="cpu")  # Load model on CPU
    
    # Transcribe and enforce English language
    result = model.transcribe(audio_file_path, language="en")  # Specify language as English
    return result['text']

# Function to check if a transcript is available for the YouTube video
def get_video_id(video_url):
    regex = (r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
             r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    match = re.search(regex, video_url)
    
    if match:
        return match.group(6)
    else:
        return None

def fetch_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry['text'] for entry in transcript])
        return transcript_text
    except NoTranscriptFound:
        return None
    except TranscriptsDisabled:
        return None
    except Exception as e:
        raise e

# Streamlit application interface
def main():
    st.title("YouTube Transcript Summarizer")

    video_url = st.text_input("Enter the video URL: ")

    if st.button("Extract Audio and Get Transcript"):
        if video_url:
            try:
                video_id = get_video_id(video_url)
                if not video_id:
                    st.error("Invalid YouTube URL")
                    return
                
                with st.spinner("Checking for available transcript..."):
                    transcript = fetch_transcript(video_id)
                    
                if transcript:
                    st.success("Transcript found!")
                    st.write("**Original Transcript:**")
                    st.write(transcript)
                else:
                    st.warning("No transcript available. Downloading video and extracting audio for transcription...")
                    
                    with st.spinner("Fetching video info..."):
                        video_title, thumbnail_url = download_video(video_url)
                        st.success("Video info fetched successfully!")

                    if thumbnail_url:
                        response = requests.get(thumbnail_url)
                        img = Image.open(BytesIO(response.content))
                        st.image(img, caption="Video Thumbnail", use_column_width=True)
                    else:
                        st.warning("Thumbnail not available.")

                    with st.spinner("Extracting audio..."):
                        audio_file_path = extract_audio(video_url)
                        st.success("Audio extracted successfully!")
                        st.audio(audio_file_path)

                    with st.spinner("Generating transcript..."):
                        transcript = audio_to_text(audio_file_path)
                        st.success("Transcript extracted and translated to English!")
                        st.write("**English Transcript:**")
                        st.write(transcript)

            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Please enter a valid URL.")

if __name__ == "__main__":
    main()

