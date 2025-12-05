"""
System control functions that work both natively and inside Docker containers.
When running in Docker, commands are executed on the host via nsenter.
When running natively, commands are executed directly.
"""

import subprocess
import os
import LOGS

# Detect if running inside Docker
def is_docker():
    """Check if we're running inside a Docker container."""
    # Check for .dockerenv file
    if os.path.exists('/.dockerenv'):
        return True
    # Check cgroup for docker
    try:
        with open('/proc/1/cgroup', 'r') as f:
            return 'docker' in f.read()
    except:
        return False

IN_DOCKER = is_docker()

def execute_on_host(command: str) -> tuple[bool, str]:
    """
    Executes a shell command. If in Docker, uses nsenter to run on host.
    Returns (success: bool, output: str)
    """
    try:
        if IN_DOCKER:
            # Use nsenter to execute on host
            result = subprocess.run(
                ['nsenter', '-t', '1', '-m', '-u', '-n', '-i', '--', 'sh', '-c', command],
                capture_output=True,
                text=True,
                timeout=10
            )
        else:
            # Execute directly on host
            result = subprocess.run(
                ['sh', '-c', command],
                capture_output=True,
                text=True,
                timeout=10
            )
        
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except FileNotFoundError:
        return False, "nsenter not found (required for Docker mode)"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def read_file_on_host(filepath: str) -> tuple[bool, str]:
    """Read a file from the host filesystem."""
    success, output = execute_on_host(f'cat "{filepath}"')
    return success, output

def write_file_on_host(filepath: str, content: str) -> bool:
    """Write content to a file on the host filesystem."""
    # Escape content for shell
    escaped = content.replace("'", "'\\''")
    success, _ = execute_on_host(f"echo '{escaped}' > \"{filepath}\"")
    return success


# ============================================================================
# SCREEN BRIGHTNESS CONTROLS
# ============================================================================

def get_backlight_path() -> str | None:
    """Find the backlight device path on the host."""
    backlight_dirs = [
        '/sys/class/backlight/intel_backlight',
        '/sys/class/backlight/amdgpu_bl0',
        '/sys/class/backlight/nvidia_0',
        '/sys/class/backlight/acpi_video0',
    ]
    
    # Try to find available backlight
    success, output = execute_on_host('ls /sys/class/backlight/ 2>/dev/null | head -1')
    if success and output:
        return f'/sys/class/backlight/{output}'
    
    # Fallback to known paths
    for path in backlight_dirs:
        success, _ = execute_on_host(f'test -d "{path}" && echo ok')
        if success:
            return path
    
    return None

def get_max_brightness() -> int:
    """Get the maximum brightness value."""
    path = get_backlight_path()
    if not path:
        return 100
    
    success, output = read_file_on_host(f'{path}/max_brightness')
    if success:
        try:
            return int(output)
        except ValueError:
            pass
    return 100

def get_screen_brightness() -> int | None:
    """Gets the current screen brightness (0-100)."""
    path = get_backlight_path()
    if not path:
        LOGS.log_error("No backlight device found")
        return None
    
    success, output = read_file_on_host(f'{path}/brightness')
    if success:
        try:
            current = int(output)
            max_brightness = get_max_brightness()
            return int((current / max_brightness) * 100)
        except ValueError:
            LOGS.log_error(f"Invalid brightness value: {output}")
            return None
    else:
        LOGS.log_error(f"Failed to read brightness: {output}")
        return None

def set_screen_brightness(level: int) -> bool:
    """Sets the screen brightness to the specified level (0-100)."""
    path = get_backlight_path()
    if not path:
        LOGS.log_error("No backlight device found")
        return False
    
    level = max(0, min(100, level))  # Clamp between 0-100
    max_brightness = get_max_brightness()
    actual_value = int((level / 100) * max_brightness)
    
    # Need root/sudo for writing to sysfs
    success, error = execute_on_host(f'echo {actual_value} | sudo tee "{path}/brightness" > /dev/null')
    if not success:
        # Try without sudo (might work if permissions are set)
        success, error = execute_on_host(f'echo {actual_value} > "{path}/brightness"')
    
    if success:
        LOGS.log_success(f"Screen brightness set to {level}%")
        return True
    else:
        LOGS.log_error(f"Failed to set screen brightness: {error}")
        return False


# ============================================================================
# VOLUME CONTROLS
# ============================================================================

def get_volume() -> int | None:
    """Gets the current system volume (0-100)."""
    # Try PulseAudio/PipeWire first
    success, output = execute_on_host("pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null | grep -oP '\\d+%' | head -1 | tr -d '%'")
    if success and output:
        try:
            return int(output)
        except ValueError:
            pass
    
    # Try ALSA
    success, output = execute_on_host("amixer get Master 2>/dev/null | grep -oP '\\d+%' | head -1 | tr -d '%'")
    if success and output:
        try:
            return int(output)
        except ValueError:
            pass
    
    LOGS.log_error("Could not get volume (no audio system found)")
    return None

def set_volume(level: int) -> bool:
    """Sets the system volume to the specified level (0-100)."""
    level = max(0, min(100, level))  # Clamp between 0-100
    
    # Try PulseAudio/PipeWire first
    success, _ = execute_on_host(f"pactl set-sink-volume @DEFAULT_SINK@ {level}%")
    if success:
        LOGS.log_success(f"Volume set to {level}%")
        return True
    
    # Try ALSA
    success, error = execute_on_host(f"amixer set Master {level}%")
    if success:
        LOGS.log_success(f"Volume set to {level}%")
        return True
    
    LOGS.log_error(f"Failed to set volume: {error}")
    return False

def mute_volume() -> bool:
    """Mutes the system volume."""
    success, _ = execute_on_host("pactl set-sink-mute @DEFAULT_SINK@ 1")
    if not success:
        success, _ = execute_on_host("amixer set Master mute")
    
    if success:
        LOGS.log_success("Volume muted")
    else:
        LOGS.log_error("Failed to mute volume")
    return success

def unmute_volume() -> bool:
    """Unmutes the system volume."""
    success, _ = execute_on_host("pactl set-sink-mute @DEFAULT_SINK@ 0")
    if not success:
        success, _ = execute_on_host("amixer set Master unmute")
    
    if success:
        LOGS.log_success("Volume unmuted")
    else:
        LOGS.log_error("Failed to unmute volume")
    return success

def toggle_mute() -> bool:
    """Toggles mute state."""
    success, _ = execute_on_host("pactl set-sink-mute @DEFAULT_SINK@ toggle")
    if not success:
        success, _ = execute_on_host("amixer set Master toggle")
    return success


# ============================================================================
# MEDIA CONTROLS
# ============================================================================

def media_play_pause() -> bool:
    """Toggle play/pause for media."""
    success, _ = execute_on_host("playerctl play-pause 2>/dev/null || dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.PlayPause 2>/dev/null")
    return success

def media_next() -> bool:
    """Skip to next track."""
    success, _ = execute_on_host("playerctl next 2>/dev/null")
    return success

def media_previous() -> bool:
    """Go to previous track."""
    success, _ = execute_on_host("playerctl previous 2>/dev/null")
    return success


# ============================================================================
# POWER CONTROLS
# ============================================================================

def shutdown() -> bool:
    """Shutdown the system."""
    LOGS.log_info("Initiating system shutdown...")
    success, _ = execute_on_host("systemctl poweroff")
    return success

def reboot() -> bool:
    """Reboot the system."""
    LOGS.log_info("Initiating system reboot...")
    success, _ = execute_on_host("systemctl reboot")
    return success

def suspend() -> bool:
    """Suspend/sleep the system."""
    LOGS.log_info("Suspending system...")
    success, _ = execute_on_host("systemctl suspend")
    return success

def lock_screen() -> bool:
    """Lock the screen."""
    # Try various lock commands
    commands = [
        "loginctl lock-session",
        "gnome-screensaver-command -l",
        "xdg-screensaver lock",
        "dm-tool lock",
    ]
    for cmd in commands:
        success, _ = execute_on_host(cmd)
        if success:
            LOGS.log_success("Screen locked")
            return True
    LOGS.log_error("Failed to lock screen")
    return False


if __name__ == "__main__":
    # Simple test of brightness functions
    current_brightness = get_screen_brightness()
    print(f"Current Brightness: {current_brightness}%")
    print("Setting brightness to 50%...")
    set_screen_brightness(50)
    new_brightness = get_screen_brightness()
    print(f"New Brightness: {new_brightness}%")