"""
ASCII Art Video Player - Version 9 (Audio + Auto-Scaling)
=============================================================
Features:
  - Audio extraction and synchronized playback (moviepy + pygame.mixer)
  - Surface Caching & Color Quantization
  - Perfect Aspect Ratio mapping 
  - Dynamic Monitor Bounds Checking
  - Delta-time based Audio/Video synchronization
"""

import argparse
import cv2
import os
import sys
import time
import threading
import pygame
import numpy as np
from queue import Queue, Empty
from moviepy import VideoFileClip

# ── 92-character set ─────────────────────────────────────────────────────────
ASCII_CHARS = (
    " `.-':_,^=;><+!rc*/z?sLTv)J7(|Fi{C}fI31tlu"
    "[neoZ5Yxjya]2ESwqkP6h9d4VpOGbUAKXHm8RD#$Bg0MNWQ%&@"
)
_CHARS_ARRAY = np.array(list(ASCII_CHARS))


# ── Advanced Renderer with Caching ────────────────────────────────────────────

class RenderCache:
    def __init__(self, font: pygame.font.Font):
        self.font = font
        self.cache = {}
        
    def get_surface(self, char: str, color_map: np.ndarray, row: int, col: int, use_color: bool):
        if not use_color:
            color_key = (200, 200, 200) 
        else:
            r = int((color_map[row, col, 0] // 16) * 16)
            g = int((color_map[row, col, 1] // 16) * 16)
            b = int((color_map[row, col, 2] // 16) * 16)
            color_key = (r, g, b)

        cache_key = (char, color_key)
        
        if cache_key not in self.cache:
            self.cache[cache_key] = self.font.render(char, False, color_key)
            
        return self.cache[cache_key]


# ── Frame Converters ──────────────────────────────────────────────────────────

def process_frame(frame, width: int, height: int):
    resized = cv2.resize(frame, (width, height), interpolation=cv2.INTER_NEAREST)
    resized_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

    r = resized_rgb[:, :, 0].astype(np.float32)
    g = resized_rgb[:, :, 1].astype(np.float32)
    b = resized_rgb[:, :, 2].astype(np.float32)
    brightness = 0.299 * r + 0.587 * g + 0.114 * b
    
    char_indices = np.clip(
        (brightness / 255.0 * (len(ASCII_CHARS) - 1)).astype(np.int32),
        0, len(ASCII_CHARS) - 1
    )
    char_grid = _CHARS_ARRAY[char_indices]
    
    return char_grid, resized_rgb


# ── Background Decoder ────────────────────────────────────────────────────────

def _frame_decoder(cap, frame_queue, stop_event, skip):
    frame_idx = 0
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            break

        if skip > 1 and frame_idx % skip != 0:
            frame_idx += 1
            continue

        frame_idx += 1
        
        while not stop_event.is_set():
            try:
                frame_queue.put(frame, timeout=0.1)
                break
            except Empty:
                pass
            except Exception:
                pass

    frame_queue.put(None) 


# ── Audio Extraction ──────────────────────────────────────────────────────────

def extract_audio(video_path: str) -> str:
    """Extracts audio to a temporary MP3 file using moviepy."""
    temp_audio_path = "temp_ascii_audio.mp3"
    print("[INFO] Extracting audio track. Please wait a moment...")
    try:
        clip = VideoFileClip(video_path)
        if clip.audio is not None:
            # Write audio without spamming the terminal console
            clip.audio.write_audiofile(temp_audio_path, logger=None)
            clip.close()
            return temp_audio_path
        clip.close()
    except Exception as e:
        print(f"[WARNING] Could not extract audio: {e}")
    return None


# ── Playback Engine ───────────────────────────────────────────────────────────

def play_video_gui(video_path: str, width: int, use_color: bool, skip: int, loop: bool):
    if not os.path.exists(video_path):
        print(f"[ERROR] File not found: '{video_path}'")
        sys.exit(1)

    # 1. Extract Audio Before Starting GUI
    audio_path = extract_audio(video_path)

    pygame.init()
    pygame.mixer.init() # Initialize the audio engine
    pygame.display.set_caption("ASCII Art Player v9 - Audio Enabled")

    if audio_path:
        pygame.mixer.music.load(audio_path)

    # Get monitor resolution to prevent off-screen UI
    monitor_info = pygame.display.Info()
    max_win_height = int(monitor_info.current_h * 0.85) 
    max_win_width = int(monitor_info.current_w * 0.90)

    font_size = 12
    font = pygame.font.SysFont("consolas, courier new, monospace", font_size, bold=True)
    char_w = font.size("A")[0]
    char_h = font.get_linesize() 
    renderer = RenderCache(font)

    play_count = 0
    running = True

    while running:
        play_count += 1
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("[ERROR] Could not open video file.")
            sys.exit(1)

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        orig_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # --- True Aspect Ratio & Auto-Scaling ---
        video_aspect = orig_height / orig_width
        font_aspect = char_w / char_h
        grid_height = max(1, int(width * video_aspect * font_aspect))
        win_width = width * char_w
        win_height = (grid_height * char_h) + 40 

        if win_height > max_win_height:
            allowed_grid_height = (max_win_height - 40) // char_h
            width = int(allowed_grid_height / (video_aspect * font_aspect))
            grid_height = max(1, int(width * video_aspect * font_aspect))
            win_width = width * char_w
            win_height = (grid_height * char_h) + 40

        if win_width > max_win_width:
            width = max_win_width // char_w
            grid_height = max(1, int(width * video_aspect * font_aspect))
            win_width = width * char_w
            win_height = (grid_height * char_h) + 40

        screen = pygame.display.set_mode((win_width, win_height), pygame.DOUBLEBUF)
        
        # Threading setup
        frame_queue = Queue(maxsize=16)
        stop_event = threading.Event()
        decoder = threading.Thread(target=_frame_decoder, args=(cap, frame_queue, stop_event, skip), daemon=True)
        decoder.start()

        # Playback state
        is_paused = False
        played_frames = 0
        expected_frames = max(1, total_frames // skip)
        
        clock = pygame.time.Clock()
        
        # START AUDIO HERE (Synchronized with frame 1)
        if audio_path:
            pygame.mixer.music.rewind()
            pygame.mixer.music.play()

        start_time = time.perf_counter()
        pause_start = 0

        while running:
            # 1. Handle Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        is_paused = not is_paused
                        if is_paused:
                            pause_start = time.perf_counter()
                            if audio_path: pygame.mixer.music.pause()
                        else:
                            start_time += (time.perf_counter() - pause_start)
                            if audio_path: pygame.mixer.music.unpause()
                    elif event.key == pygame.K_m:
                        use_color = not use_color

            if not running:
                break

            if is_paused:
                clock.tick(15)
                continue

            # 2. Get next frame
            try:
                frame = frame_queue.get(timeout=1.0)
            except Empty:
                continue

            if frame is None:
                break

            played_frames += 1
            
            char_grid, color_map = process_frame(frame, width, grid_height)

            # 3. Render
            screen.fill((10, 10, 10))

            for row in range(char_grid.shape[0]):
                for col in range(char_grid.shape[1]):
                    char = char_grid[row, col]
                    if char == ' ': continue
                    
                    surf = renderer.get_surface(char, color_map, row, col, use_color)
                    screen.blit(surf, (col * char_w, row * char_h))

            # 4. Draw UI Status Bar
            progress = played_frames / expected_frames
            bar_y = grid_height * char_h + 10
            
            pygame.draw.rect(screen, (50, 50, 50), (10, bar_y, win_width - 20, 8), border_radius=4)
            pygame.draw.rect(screen, (0, 200, 100), (10, bar_y, int((win_width - 20) * progress), 8), border_radius=4)

            actual_fps = clock.get_fps()
            mode_text = "COLOR" if use_color else "NO COLOR"
            audio_text = "AUDIO ON" if audio_path else "NO AUDIO"
            hud_text = f"Frames: {played_frames}/{expected_frames} | {actual_fps:.1f} FPS | {audio_text} | {mode_text} (M) | Space: Pause | ESC: Quit"
            hud_surface = font.render(hud_text, True, (180, 180, 180))
            screen.blit(hud_surface, (10, bar_y + 12))

            pygame.display.flip()

            # 5. Delta-time Synchronization
            current_time = time.perf_counter()
            target_time = start_time + (played_frames * (1.0 / (fps / skip)))
            sleep_time = target_time - current_time
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            clock.tick(120)

        stop_event.set()
        decoder.join(timeout=1.0)
        cap.release()

        if not loop or not running:
            break

    # Cleanup operations
    pygame.mixer.quit()
    pygame.quit()
    
    # Delete the temporary audio file so it doesn't clutter your hard drive
    if audio_path and os.path.exists(audio_path):
        try:
            os.remove(audio_path)
            print("[INFO] Temporary audio file cleaned up.")
        except:
            pass
            
    print("[INFO] Player exited gracefully.")


# ── CLI Argument Parser & Menus ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ASCII Video Player v9")
    parser.add_argument("video", nargs="?", default=None, help="Video path")
    parser.add_argument("-w", "--width", type=int, default=120, help="Output width in characters")
    parser.add_argument("-c", "--color", action="store_true", help="Start in full RGB color mode")
    parser.add_argument("-s", "--skip", type=int, default=1, help="Skip every N frames")
    parser.add_argument("-l", "--loop", action="store_true", help="Loop playback")

    args = parser.parse_args()

    if args.video is None:
        print("\n--- ASCII GUI Video Player ---")
        args.video = input("Enter video path: ").strip().strip('"')
        if not args.video:
            print("[ERROR] Path required.")
            sys.exit(1)
            
        color_input = input("Enable full video colors? (y/N): ").strip().lower()
        args.color = (color_input == 'y')
        
        try:
            w = input("Output width in characters (default 120): ").strip()
            args.width = int(w) if w else 120
        except ValueError:
            args.width = 120

        try:
            s = input("Skip every N frames (default 1): ").strip()
            args.skip = int(s) if s else 1
        except ValueError:
            args.skip = 1
            
        loop_input = input("Loop video continuously? (y/N): ").strip().lower()
        args.loop = (loop_input == 'y')

    play_video_gui(
        video_path=args.video,
        width=args.width,
        use_color=args.color,
        skip=args.skip,
        loop=args.loop
    )

if __name__ == "__main__":
    main()