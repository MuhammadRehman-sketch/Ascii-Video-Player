

### About

A high-performance Python multimedia application that converts and renders video files into dynamic ASCII art in real-time. By utilizing Pygame for graphical surface rendering instead of standard terminal outputs, the player bypasses the severe latency limitations of command-line interfaces. It delivers smooth framerates, true RGB color quantization, and precise audio-video synchronization.

### Core Features

* **Optimized Rendering Engine:** Utilizes Pygame surface caching and vectorized NumPy brightness calculations to process and render thousands of text characters per frame without severe CPU bottlenecking.
* **Precise A/V Synchronization:** Implements absolute delta-time tracking and MoviePy audio extraction to maintain perfect sync between the character grid rendering and the audio track, preventing drift over time.
* **True Aspect Ratio Mapping:** Mathematically calculates the character grid based on exact font pixel dimensions (linesize and width) to preserve the original video's aspect ratio without stretching or squashing.
* **Dynamic Auto-Scaling:** Reads host monitor resolution at runtime and automatically scales the output window and character count to ensure the UI remains within screen bounds.
* **Interactive Controls:** Supports live toggling between true RGB color and monochrome modes, pausing, looping, and variable frame-skipping via the GUI or CLI arguments.

### Tech Stack

* **Python 3**
* **OpenCV (`cv2`):** Frame extraction and raw image resizing.
* **NumPy:** Vectorized color quantization and brightness mapping.
* **Pygame:** Hardware-accelerated window generation, font rendering, and audio mixing.
* **MoviePy:** Background audio track extraction.


**How to use this on GitHub:** Copy and paste this directly into the top of your `README.md` file. It tells other developers exactly what the tool is, how it works under the hood, and proves that you understand performance optimization.
