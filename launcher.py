import sys
import os
import subprocess

def main():
    app_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path, "--server.headless=true"], check=True)

if __name__ == "__main__":
    main()
