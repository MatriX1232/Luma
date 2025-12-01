from contextlib import contextmanager, redirect_stderr, redirect_stdout
import io
import logging
from kokoro import KPipeline
import soundfile as sf
import torch
import numpy as np
from threading import Thread
from queue import Queue

from pydub import AudioSegment
from pydub.playback import _play_with_ffplay
import subprocess
import tempfile

import LOGS
import traceback
import os
import warnings


@contextmanager
def suppress_all_output():
    devnull = os.open(os.devnull, os.O_RDWR)
    saved_stdout_fd = os.dup(1)
    saved_stderr_fd = os.dup(2)
    prev_log_levels = {}
    try:
        # silence python warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            # silence python-level stdout/stderr
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                # silence C-level outputs by redirecting fds to /dev/null
                os.dup2(devnull, 1)
                os.dup2(devnull, 2)

                # reduce noisy loggers to CRITICAL
                for name in ("transformers", "torch", "kokoro"):
                    logger = logging.getLogger(name)
                    prev_log_levels[name] = logger.level
                    logger.setLevel(logging.CRITICAL)

                yield
    finally:
        # restore fds
        os.dup2(saved_stdout_fd, 1)
        os.dup2(saved_stderr_fd, 2)
        os.close(devnull)
        os.close(saved_stdout_fd)
        os.close(saved_stderr_fd)
        # restore logger levels
        for name, lvl in prev_log_levels.items():
            logging.getLogger(name).setLevel(lvl)


class TTS_MODEL:
    def __init__(self, lang_code='a', voice='af_heart', device=None):
        self.pipeline = None
        self.voice = voice
        try:
            with suppress_all_output():
                if device is None:
                    self.pipeline = KPipeline(lang_code=lang_code)
                else:
                    self.pipeline = KPipeline(lang_code=lang_code, device=device)
            LOGS.log_success(f"Initialized TTS_MODEL with lang_code={lang_code}, voice={voice}, device={device}")
        except Exception as e:
            LOGS.log_error(f"Failed to initialize TTS_MODEL: {e}\n{traceback.format_exc()}")


    def synthesize(self, text):
        if self.pipeline is None:
            LOGS.log_error("Cannot synthesize: pipeline not initialized")
            return
        try:
            generator = self.pipeline(text, voice=self.voice)
            for i, (gs, ps, audio) in enumerate(generator):
                LOGS.log_info(f"Synthesizing chunk {i}: gs={gs}, ps={ps}")
                sf.write(f'{i}.wav', audio, 24000)
        except Exception as e:
            LOGS.log_error(f"Synthesis failed: {e}\n{traceback.format_exc()}")
            raise


    def play(self):
        if self.pipeline is None:
            LOGS.log_error("Cannot play: pipeline not initialized")
            return
        try:
            LOGS.log_info(f"Playing response form TTS Model")
            song = AudioSegment.from_wav("RESPONSE.wav")
            self._play_silent(song)
        except Exception as e:
            LOGS.log_error(f"Playback failed: {e}\n{traceback.format_exc()}")
            raise

    def _play_silent(self, audio_segment):
        """Play audio using ffplay with suppressed output."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_segment.export(f.name, format="wav")
            try:
                subprocess.run(
                    ["ffplay", "-nodisp", "-autoexit", "-hide_banner", "-loglevel", "quiet", f.name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            finally:
                os.unlink(f.name)

    def synthesize_stream(self, text):
        """Generator that yields audio chunks as they're synthesized"""
        if self.pipeline is None:
            LOGS.log_error("Cannot synthesize: pipeline not initialized")
            return
        try:
            generator = self.pipeline(text, voice=self.voice)
            for i, (gs, ps, audio) in enumerate(generator):
                # LOGS.log_info(f"Synthesizing chunk {i}: gs={gs}, ps={ps}")
                yield audio
        except Exception as e:
            LOGS.log_error(f"Synthesis failed: {e}\n{traceback.format_exc()}")
            raise

    def play_audio_chunk(self, audio_data, sample_rate=24000):
        """Play a single audio chunk"""
        try:
            # Convert tensor to numpy if needed
            if torch.is_tensor(audio_data):
                audio_data = audio_data.cpu().numpy()
            
            # Ensure it's float32 and in the range [-1, 1], then convert to int16
            audio_data = np.clip(audio_data, -1.0, 1.0)
            audio_data = (audio_data * 32767).astype(np.int16)
            
            audio_segment = AudioSegment(
                audio_data.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,
                channels=1
            )
            # Use silent playback to avoid polluting stdout
            self._play_silent(audio_segment)
        except Exception as e:
            LOGS.log_error(f"Playback failed: {e}\n{traceback.format_exc()}")


# Example usage:
# TTS = TTS_MODEL(lang_code='a', voice='af_heart', device='cuda' if torch.cuda.is_available() else 'cpu')
# text = 'Hi there! This is a test of the text-to-speech synthesis system.'
# TTS.synthesize(text)