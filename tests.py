import subprocess
from colored import fg, attr
import LOGS


def test_main_execution():
    result = subprocess.run(['python', '--version'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Python' in result.stdout or 'Python' in result.stderr
    LOGS.log_success(f"{fg('green')}[PASS]{attr('reset')} Test of main execution")


def test_ollama_presence():
    result = subprocess.run(['which', 'ollama'], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() != ''
    LOGS.log_success(f"{fg('green')}[PASS]{attr('reset')} Test of ollama presence")

def test_ollama_models():
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'llama3.2' in result.stdout
    LOGS.log_success(f"{fg('green')}[PASS]{attr('reset')} Test of ollama models")


def test_cuda_availability():
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'NVIDIA-SMI' in result.stdout
    LOGS.log_success(f"{fg('green')}[PASS]{attr('reset')} Test of CUDA availability")


def test_cuda_in_ollama():
    try:
        result = subprocess.run(['ollama', 'serve'], capture_output=True, text=True, timeout=5)
        output = (result.stdout or '') + (result.stderr or '')
    except subprocess.TimeoutExpired as e:
        # process was killed after timeout; collect any partial output
        output = (e.stdout or '') + (e.stderr or '') if hasattr(e, 'stdout') or hasattr(e, 'stderr') else ''
    assert 'NVIDIA GeForce' in output.decode('utf-8')
    LOGS.log_success(f"{fg('green')}[PASS]{attr('reset')} Test of CUDA in ollama")