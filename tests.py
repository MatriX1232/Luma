import subprocess
from colored import fg, attr
import LOGS
from SYSTEM_CALLS import execute_on_host


def test_main_execution():
    result = subprocess.run(['python', '--version'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Python' in result.stdout or 'Python' in result.stderr
    LOGS.log_success(f"{fg('green')}[PASS]{attr('reset')} Test of main execution")


def test_ollama_presence():
    is_success, output = execute_on_host('which ollama')
    assert is_success == True
    assert output.strip() != ''
    LOGS.log_success(f"{fg('green')}[PASS]{attr('reset')} Test of ollama presence")

def test_ollama_models():
    is_success, output = execute_on_host('ollama list')
    # result = subprocess.run(['ollama', 'list'], cap/ture_output=True, text=True)
    assert is_success == True
    assert 'llama3.2' in output
    LOGS.log_success(f"{fg('green')}[PASS]{attr('reset')} Test of ollama models")


def test_cuda_availability():
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'NVIDIA-SMI' in result.stdout
    LOGS.log_success(f"{fg('green')}[PASS]{attr('reset')} Test of CUDA availability")


def test_cuda_in_ollama():
    try:
        is_success, output = execute_on_host('ollama serve')
        assert is_success == True
        assert 'CUDA' in output or 'GPU' in output
        LOGS.log_success(f"{fg('green')}[PASS]{attr('reset')} Test of CUDA in Ollama")
    except Exception as e:
        LOGS.log_error(f"{fg('red')}[FAIL]{attr('reset')} Test of CUDA in Ollama: {e}")


if __name__ == "__main__":
    test_main_execution()
    test_cuda_availability()
    # test_ollama_presence()
    # test_cuda_in_ollama()