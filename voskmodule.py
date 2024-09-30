import os
import re
import subprocess
import streamlit as st
import yt_dlp
from vosk import Model, KaldiRecognizer
import wave
import json
import requests
from PIL import Image
from io import BytesIO

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

# Convert MP3 to WAV format for Vosk to process
def convert_audio_to_wav(mp3_file_path):
    wav_file_path = mp3_file_path.replace(".mp3", ".wav")
    subprocess.run(['ffmpeg', '-i', mp3_file_path, wav_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return wav_file_path

# Function to generate transcript using Vosk
def audio_to_text(wav_file_path):
    # Load Vosk model (Make sure you have downloaded the Vosk model and placed it in your project directory)
    model_path = "vosk-model-small-en-us-0.15"  # Adjust this path to your model folder
    if not os.path.exists(model_path):
        raise Exception("Vosk model not found. Please download and extract the model.")

    model = Model(model_path)

    wf = wave.open(wav_file_path, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())

    transcript = ""
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = rec.Result()
            result_json = json.loads(result)
            transcript += result_json.get('text', '') + " "

    wf.close()
    return transcript.strip()

# Streamlit application interface
def main():
    st.title("Universal Video Downloader and Audio Extractor")

    video_url = st.text_input("Enter the video URL (YouTube, Vimeo, etc.)")

    if st.button("Extract Audio and Get Transcript"):
        if video_url:
            try:
                with st.spinner("Fetching video info..."):
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
                    audio_file_path = extract_audio(video_url)
                    st.success("Audio extracted successfully!")
                    st.audio(audio_file_path)

                with st.spinner("Converting audio to WAV..."):
                    wav_file_path = convert_audio_to_wav(audio_file_path)
                    st.success("Audio converted to WAV format.")

                with st.spinner("Generating transcript using Vosk..."):
                    transcript = audio_to_text(wav_file_path)
                    st.success("Transcript generated successfully!")
                    st.write(transcript)

            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.error("Please enter a valid URL.")

if __name__ == "__main__":
    main()
