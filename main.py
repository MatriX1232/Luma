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
from threading import Thread, Event
from queue import Queue, Empty
import numpy as np
import signal

from MAIN_MODEL import MAIN_MODEL
from TTS_MODEL import TTS_MODEL
from SYSTEM_CALLS import *

# Global stop event for interrupting response
stop_event = Event()
main_model = None
tts_model = None


def start_ollama_background():
    """Start ollama serve on the HOST machine using nsenter if not already running."""
    curl_path = shutil.which('curl')
    if not curl_path:
        LOGS.log_error("curl not found. Cannot check/manage Ollama.")
        return False

    nsenter_path = shutil.which('nsenter')
    if not nsenter_path:
        LOGS.log_error("nsenter not found. Cannot start Ollama on host.")
        return False

    # Check if ollama is already running
    try:
        result = subprocess.run(
            [curl_path, '-s', 'http://localhost:11434/api/tags'],
            capture_output=True,
            timeout=2
        )
        if result.returncode == 0:
            LOGS.log_info("Ollama is already running")
            return True
    except:
        pass
    
    # Start ollama on HOST using nsenter (run in host's PID/mount namespace)
    LOGS.log_info("Starting Ollama on host via nsenter...")
    try:
        # nsenter with PID 1 enters the host's namespaces
        # -t 1: target PID 1 (init process on host)
        # -m: mount namespace
        # -u: UTS namespace  
        # -n: network namespace
        # -i: IPC namespace
        # Start ollama with nohup and redirect output to suppress GIN logs
        subprocess.Popen(
            [nsenter_path, '-t', '1', '-m', '-u', '-n', '-i', '--', 
             'sh', '-c', 'nohup ollama serve > /dev/null 2>&1 &'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        sleep(3)  # Give ollama time to start
        
        # Verify it started
        result = subprocess.run(
            [curl_path, '-s', 'http://localhost:11434/api/tags'],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            LOGS.log_success("Ollama started successfully on host")
            return True
        else:
            LOGS.log_error("Ollama failed to start on host")
            return False
    except Exception as e:
        LOGS.log_error(f"Failed to start Ollama: {e}")
        return False

def text_fetcher(user_input, text_queue, print_queue):
    """Fetches text from the AI model and queues it for printing and TTS."""
    try:
        if main_model is None:
            LOGS.log_error("MAIN_MODEL not initialized")
            return

        for chunk in main_model.generate_response(user_input):
            if stop_event.is_set():
                break
            print_queue.put(chunk)
            text_queue.put(chunk)
    except Exception as e:
        if not stop_event.is_set():
            LOGS.log_error(f"text_fetcher error: {e}")
    finally:
        print_queue.put(None)
        text_queue.put(None)

def print_worker(print_queue):
    """Prints text chunks as they arrive - runs in main thread context."""
    sys.stdout.write("AI: ")
    sys.stdout.flush()
    while True:
        try:
            chunk = print_queue.get(timeout=0.1)
        except Empty:
            if stop_event.is_set():
                break
            continue
        if chunk is None:
            break
        sys.stdout.write(chunk)
        sys.stdout.flush()

def synthesis_worker(text_queue, audio_queue):
    """Synthesizes audio sentence by sentence."""
    sentence_buffer = ""
    while True:
        try:
            chunk = text_queue.get(timeout=0.1)
        except Empty:
            if stop_event.is_set():
                break
            continue
            
        if chunk is None:
            # Process any remaining text (only if not stopped)
            if sentence_buffer.strip() and not stop_event.is_set():
                try:
                    if tts_model is None:
                        LOGS.log_error("TTS_MODEL not initialized")
                        break

                    for audio in tts_model.synthesize_stream(sentence_buffer):
                        if stop_event.is_set():
                            break
                        audio_queue.put(audio)
                except Exception as e:
                    if not stop_event.is_set():
                        LOGS.log_error(f"synthesis_worker error: {e}")
            break
        
        if stop_event.is_set():
            break
            
        sentence_buffer += chunk
        # Check for sentence boundaries
        while any(p in sentence_buffer for p in ['.', '!', '?', '\n']):
            if stop_event.is_set():
                break
            parts = re.split(r'(?<=[.!?\n])\s*', sentence_buffer, maxsplit=1)
            if len(parts) > 1:
                sentence, sentence_buffer = parts[0], parts[1]
            else:
                sentence, sentence_buffer = parts[0], ""
            
            if sentence.strip():
                try:
                    if tts_model is None:
                        LOGS.log_error("TTS_MODEL not initialized")
                        break

                    for audio in tts_model.synthesize_stream(sentence):
                        if stop_event.is_set():
                            break
                        audio_queue.put(audio)
                except Exception as e:
                    if not stop_event.is_set():
                        LOGS.log_error(f"synthesis_worker error: {e}")
    
    audio_queue.put(None)

def playback_worker(audio_queue):
    """Plays audio chunks from the queue."""
    while True:
        try:
            audio = audio_queue.get(timeout=0.1)
        except Empty:
            if stop_event.is_set():
                break
            continue
        if audio is None:
            break
        if stop_event.is_set():
            break
        try:
            if tts_model is None:
                LOGS.log_error("TTS_MODEL not initialized")
                break

            tts_model.play_audio_chunk(audio)
        except Exception as e:
            if not stop_event.is_set():
                LOGS.log_error(f"playback_worker error: {e}")

if __name__ == "__main__":
    LOGS.log_info("Application started")

    config = configparser.ConfigParser()
    config.read('config.conf')

    if (config.getboolean('DEFAULT', 'PERFORM_TESTS', fallback=False)):
        try:
            tests.test_main_execution()
            tests.test_cuda_availability()
            # tests.test_ollama_presence()
            # tests.test_cuda_in_ollama()

            start_ollama_background()
            tests.test_ollama_models()
        except AssertionError as e:
            LOGS.log_error(f"Test failed: {e}")
            sys.exit(1)
        finally:
            LOGS.log_info("All tests completed\n")

    use_gui = config.getboolean('DEFAULT', 'USE_GUI', fallback=False)

    if not use_gui:
        while True:
            if input("Do u wish to continue? (y/n): ").lower() == 'y':
                break
            else:
                LOGS.log_info("Exiting application as per user request.")
                sys.exit(0)



    # Always try to start Ollama on host if not running
    start_ollama_background()

    main_model = MAIN_MODEL(
        model_name=config.get('DEFAULT', 'MAIN_MODEL', fallback='None'),
        use_tools=config.getboolean('DEFAULT', 'USE_TOOLS', fallback=False)
    )

    tts_model = TTS_MODEL(
        device= "cuda" if config.getboolean('DEFAULT', 'USE_GPU', fallback=False) is True else "cpu"
    )

    LOGS.log_info(f"Main AI Model set to: {config.get('DEFAULT', 'MAIN_MODEL', fallback='None')}")
    LOGS.log_info(f"TTS Model set to: {config.get('DEFAULT', 'TTS_MODEL', fallback='default')}")
    LOGS.log_info(f"Use GPU: {config.getboolean('DEFAULT', 'USE_GPU', fallback=False)}")
    LOGS.log_info(f"Use Tools: {config.getboolean('DEFAULT', 'USE_TOOLS', fallback=False)}")

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit']:
                LOGS.log_info("Exiting application.")
                break

            # Reset stop event for new response
            stop_event.clear()
            
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

            # Wait for threads with interrupt handling
            try:
                while t_fetcher.is_alive() or t_printer.is_alive() or t_synth.is_alive() or t_playback.is_alive():
                    t_fetcher.join(timeout=0.1)
                    t_printer.join(timeout=0.1)
                    t_synth.join(timeout=0.1)
                    t_playback.join(timeout=0.1)
            except KeyboardInterrupt:
                # Ctrl+C during response - stop all workers and continue to next prompt
                print("\n[Interrupted]")
                stop_event.set()
                # Wait for threads to finish cleanly
                t_fetcher.join(timeout=1)
                t_printer.join(timeout=1)
                t_synth.join(timeout=1)
                t_playback.join(timeout=1)
                continue

            print()  # newline after response

        except KeyboardInterrupt:
            # Ctrl+C at prompt - exit application
            print()
            LOGS.log_info("Exiting application due to keyboard interrupt.")
            break
        except Exception as e:
            LOGS.log_error(f"An error occurred: {e}\n{traceback.format_exc()}")

