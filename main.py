import os
import re
import streamlit as st
import yt_dlp
import requests
from PIL import Image
import whisper
from io import BytesIO
import time

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
        return sanitized_title, thumbnail_url

# Function to extract audio using yt-dlp
def extract_audio(video_url):
    sanitized_title = sanitize_filename(video_url.split('=')[-1])  # Use video ID as filename
    audio_file_path = f"downloads/{sanitized_title}.mp3"
    
    ydl_opts = {
        'format': 'bestaudio',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': audio_file_path,
        'noplaylist': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    return audio_file_path

# Function to convert audio to text using Whisper with automatic language detection
def audio_to_text(audio_file_path):
    model = whisper.load_model("base")  # Adjust model for speed/accuracy tradeoff
    result = model.transcribe(audio_file_path)  # Whisper automatically detects language
    
    # Retrieve detected language and transcript
    detected_language = result.get('language', 'unknown')  # Use 'unknown' if no language is detected
    transcript = result['text']
    
    return detected_language, transcript

# Streamlit application interface
def main():
    st.title("Universal Video Downloader and Audio Extractor")

    video_url = st.text_input("Enter the video URL (YouTube, Vimeo, etc.)")

    if st.button("Extract Audio and Get Transcript"):
        if video_url:
            try:
                with st.spinner("Fetching video info..."):
                    # Download the video info and get the thumbnail URL
                    video_title, thumbnail_url = download_video(video_url)
                    st.success("Video info fetched successfully!")

                # Display the video thumbnail
                if thumbnail_url:
                    response = requests.get(thumbnail_url)
                    img = Image.open(BytesIO(response.content))
                    st.image(img, caption="Video Thumbnail", use_column_width=True)
                else:
                    st.warning("Thumbnail not available.")

                with st.spinner("Extracting audio..."):
                    # Extract audio
                    audio_file_path = extract_audio(video_url)
                    st.success("Audio extracted successfully!")
                    st.audio(audio_file_path)  # Display audio player

                with st.spinner("Generating transcript..."):
                    # Convert audio to text and display transcript with detected language
                    detected_language, transcript = audio_to_text(audio_file_path)
                    
                    st.success(f"Transcript extracted successfully in {detected_language}!")
                    st.write(transcript)

            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Please enter a valid URL.")

if __name__ == "__main__":
    main()
