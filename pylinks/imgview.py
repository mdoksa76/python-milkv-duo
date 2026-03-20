#!/usr/bin/python3

import plotext as plt
import sys
import os
from PIL import Image

def display_image(path, thumbnail=False):
    try:
        with Image.open(path) as img:
            orig_width, orig_height = img.size

            term_cols, term_rows = plt.terminal_size()

            if thumbnail:
                max_height = max(10, int(term_rows / 4))
            else:
                max_height = term_rows - 6

            new_width = int(max_height * orig_width / orig_height * 1.82)
            new_width = min(new_width, term_cols - 4)

            info = (f"{os.path.basename(path)} "
                    f"| {orig_width}x{orig_height} px "
                    f"| {new_width}x{max_height} chars")

            plt.clear_figure()
            plt.plotsize(new_width, max_height)
            plt.frame(True)
            plt.title(info)
            plt.image_plot(path)
            plt.show()

            return True

    except Exception as e:
        print(f"❌ Cannot display: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: ./imgview.py <image-path>")
        return

    thumbnail = "--thumb" in sys.argv
    path = [a for a in sys.argv[1:] if not a.startswith("--")][0]

    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    display_image(path, thumbnail)

    if os.name == 'nt':
        import msvcrt
        print("\nPress any key to exit...")
        msvcrt.getch()
    else:
        os.system("""bash -c 'read -s -n 1 -p "Press any key to exit..."'""")

if __name__ == "__main__":
    main()
