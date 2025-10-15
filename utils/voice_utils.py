# utils/voice_utils.py
import speech_recognition as sr
from pydub import AudioSegment
import io

def transcribe_audio_file(file_like) -> str:
    """
    Convert uploaded audio file (wav/mp3) to text using SpeechRecognition.
    Accepts a file-like object (Streamlit UploadFile or BytesIO).
    """
    # Normalize file-like to BytesIO for pydub / sr
    try:
        # If it's a Streamlit UploadedFile, .read() returns bytes
        audio_bytes = file_like.read()
    except Exception:
        # assume raw bytes were passed directly
        audio_bytes = file_like

    # Detect and convert mp3 to wav in-memory if needed
    try:
        # pydub can read bytes via BytesIO
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)
    except Exception:
        # fallback: assume already WAV
        wav_io = io.BytesIO(audio_bytes)
        wav_io.seek(0)

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_io) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            text = "[Could not transcribe audio]"
        except sr.RequestError as e:
            text = f"[Speech recognition service error: {e}]"
    return text
