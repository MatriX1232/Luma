import traceback
import tests
import LOGS
import sys
import subprocess
import os
import shutil
from time import sleep
import configparser
import re
from threading import Thread
from queue import Queue
import numpy as np

from MAIN_MODEL import MAIN_MODEL
from TTS_MODEL import TTS_MODEL


def create_ollama_terminal():
    #try to open a new terminal and run ollama serve there; fall back to detached nohup
    _terminals = ['gnome-terminal', 'mate-terminal', 'konsole', 'xterm', 'xfce4-terminal', 'lxterminal', 'terminator', 'alacritty']
    _term = next((t for t in _terminals if shutil.which(t)), None)
    
    if _term:
        if _term in ('gnome-terminal', 'mate-terminal'):
            _cmd = [_term, '--', 'bash', '-c', 'ollama serve; exec bash']
        else:
            _cmd = [_term, '-e', 'bash', '-c', 'ollama serve; exec bash']
        subprocess.Popen(_cmd, stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'), preexec_fn=os.setsid)
    else:
        # no terminal found — run fully detached
        subprocess.Popen(['nohup', 'ollama', 'serve'], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'), preexec_fn=os.setsid)
    
    sleep(2)  # give some time for ollama to start

def text_fetcher():
    """Fetches text from the AI model, prints it, and queues it for TTS."""
    print("AI: ", end='', flush=True)
    try:
        for chunk in MAIN_MODEL.generate_response(user_input):
            print(chunk, end='', flush=True)
            text_queue.put(chunk)
    finally:
        text_queue.put(None)

def synthesis_worker():
    """Synthesizes audio sentence by sentence."""
    sentence_buffer = ""
    while True:
        chunk = text_queue.get()
        if chunk is None:
            # Process any remaining text
            if sentence_buffer.strip():
                for audio in TTS_MODEL.synthesize_stream(sentence_buffer):
                    audio_queue.put(audio)
            break
        
        sentence_buffer += chunk
        # Check for sentence boundaries
        while any(p in sentence_buffer for p in ['.', '!', '?', '\n']):
            parts = re.split(r'(?<=[.!?\n])\s*', sentence_buffer, maxsplit=1)
            if len(parts) > 1:
                sentence, sentence_buffer = parts[0], parts[1]
            else:
                sentence, sentence_buffer = parts[0], ""
            
            if sentence.strip():
                for audio in TTS_MODEL.synthesize_stream(sentence):
                    audio_queue.put(audio)
    
    audio_queue.put(None)

def playback_worker():
    """Plays audio chunks from the queue."""
    while True:
        audio = audio_queue.get()
        if audio is None:
            break
        TTS_MODEL.play_audio_chunk(audio)



if __name__ == "__main__":
    LOGS.log_info("Application started")

    config = configparser.ConfigParser()
    config.read('config.conf')

    if (config.getboolean('DEFAULT', 'PERFORM_TESTS', fallback=False)):
        try:
            tests.test_main_execution()
            tests.test_cuda_availability()
            tests.test_ollama_presence()
            tests.test_cuda_in_ollama()

            create_ollama_terminal()
            tests.test_ollama_models()
        except AssertionError as e:
            LOGS.log_error(f"Test failed: {e}")
            sys.exit(1)
        finally:
            LOGS.log_info("All tests completed\n")


    MAIN_MODEL = MAIN_MODEL(
        model_name=config.get('DEFAULT', 'MAIN_MODEL', fallback='None')
    )

    TTS_MODEL = TTS_MODEL(
        device= "cuda" if config.getboolean('DEFAULT', 'USE_GPU', fallback=False) is True else "cpu"
    )

    LOGS.log_info(f"Main AI Model set to: {config.get('DEFAULT', 'MAIN_MODEL', fallback='None')}")
    LOGS.log_info(f"TTS Model set to: {config.get('DEFAULT', 'TTS_MODEL', fallback='default')}")
    LOGS.log_info(f"Use GPU: {config.getboolean('DEFAULT', 'USE_GPU', fallback=False)}")

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit']:
                LOGS.log_info("Exiting application.")
                break

            text_queue = Queue()
            audio_queue = Queue()

            # Start threads
            threads = [
                Thread(target=text_fetcher),
                Thread(target=synthesis_worker, daemon=True),
                Thread(target=playback_worker, daemon=True)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            print()  # newline after response

        except KeyboardInterrupt:
            LOGS.log_info("Exiting application due to keyboard interrupt.")
            break
        except Exception as e:
            LOGS.log_error(f"An error occurred: {e}\n{traceback.format_exc()}")

