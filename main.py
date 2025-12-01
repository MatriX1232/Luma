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

def text_fetcher(user_input, text_queue, print_queue):
    """Fetches text from the AI model and queues it for printing and TTS."""
    try:
        for chunk in MAIN_MODEL.generate_response(user_input):
            print_queue.put(chunk)
            text_queue.put(chunk)
    except Exception as e:
        LOGS.log_error(f"text_fetcher error: {e}")
    finally:
        print_queue.put(None)
        text_queue.put(None)

def print_worker(print_queue):
    """Prints text chunks as they arrive - runs in main thread context."""
    sys.stdout.write("AI: ")
    sys.stdout.flush()
    while True:
        chunk = print_queue.get()
        if chunk is None:
            break
        sys.stdout.write(chunk)
        sys.stdout.flush()

def synthesis_worker(text_queue, audio_queue):
    """Synthesizes audio sentence by sentence."""
    sentence_buffer = ""
    while True:
        chunk = text_queue.get()  # blocking get is fine here
            
        if chunk is None:
            # Process any remaining text
            if sentence_buffer.strip():
                try:
                    for audio in TTS_MODEL.synthesize_stream(sentence_buffer):
                        audio_queue.put(audio)
                except Exception as e:
                    LOGS.log_error(f"synthesis_worker error: {e}")
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
                try:
                    for audio in TTS_MODEL.synthesize_stream(sentence):
                        audio_queue.put(audio)
                except Exception as e:
                    LOGS.log_error(f"synthesis_worker error: {e}")
    
    audio_queue.put(None)

def playback_worker(audio_queue):
    """Plays audio chunks from the queue."""
    while True:
        audio = audio_queue.get()  # blocking get is fine here
        if audio is None:
            break
        try:
            TTS_MODEL.play_audio_chunk(audio)
        except Exception as e:
            LOGS.log_error(f"playback_worker error: {e}")



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
            print_queue = Queue()

            # Start threads - separate printing from synthesis
            t_fetcher = Thread(target=text_fetcher, args=(user_input, text_queue, print_queue))
            t_printer = Thread(target=print_worker, args=(print_queue,))
            t_synth = Thread(target=synthesis_worker, args=(text_queue, audio_queue))
            t_playback = Thread(target=playback_worker, args=(audio_queue,))

            t_fetcher.start()
            t_printer.start()
            t_synth.start()
            t_playback.start()

            # Wait for text streaming and printing to finish first
            t_fetcher.join()
            t_printer.join()
            
            # Then wait for audio pipeline to complete
            t_synth.join()
            t_playback.join()

            print()  # newline after response

        except KeyboardInterrupt:
            LOGS.log_info("Exiting application due to keyboard interrupt.")
            break
        except Exception as e:
            LOGS.log_error(f"An error occurred: {e}\n{traceback.format_exc()}")

