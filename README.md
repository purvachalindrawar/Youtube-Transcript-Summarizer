# YouTube Transcript Summarizer

This project is a universal video downloader and audio extractor that fetches video transcripts from various platforms. It allows users to enter a video URL, extract audio, and convert the audio to text.

## Features

- Download videos from platforms like YouTube and Vimeo.
- Extract audio from videos.
- Convert audio to text using speech recognition.
- Display the video thumbnail and transcript on the interface.
- User-friendly Streamlit interface.

## Requirements

- Python 3.x
- Streamlit
- yt-dlp
- SpeechRecognition
- pydub
- Whisper (for audio-to-text conversion)
- Pillow
- Requests

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/purvachalindrawar/Youtube-Transcript-Summarizer.git
   cd Youtube-Transcript-Summarizer
   
2. Virtual Environment:
   ```bash
   python -m venv venv
   `venv\Scripts\activate`   # For Windows

3. Instllation of packages:
   ```bash
    pip install -r requirements.txt
   
4. Run the Application:
   ```bash
     1. streamlit run app.py

5. Enter the video URL in the provided input box and click "Extract Audio and Get Transcript".
6. The video thumbnail will be displayed, and the audio will be extracted. The transcript of the audio will also be displayed on the screen.



# What's Next
- Summarization of the transcript into multiple language
- the pop up message displayed if particular video has no transcript provided
- customizable summary - user can enter the number of words he wants
- 
