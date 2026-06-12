import subprocess
import sys

def main():
    print("Building Super Stream Windows application...")
    
    # Construct the PyInstaller command using the current python executable
    cmd = [
        sys.executable, 
        "-m", "PyInstaller", 
        "--noconsole", 
        "--onefile", 
        "windows_app.py"
    ]
    
    print("Running command:", " ".join(cmd))
    
    try:
        subprocess.run(cmd, check=True)
        print("\n==================================================")
        print("BUILD COMPLETED SUCCESSFULLY!")
        print("You can find the standalone executable at:")
        print("dist/windows_app.exe")
        print("==================================================")
    except subprocess.CalledProcessError as e:
        print("\nBuild failed! Error code:", e.returncode)
        sys.exit(1)

if __name__ == "__main__":
    main()
