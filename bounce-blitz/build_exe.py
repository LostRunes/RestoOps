# build_exe.py - PyInstaller Single-File Portable Build Script for Bounce Blitz

import subprocess
import os
import sys

def build():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(script_dir, 'templates')
    
    # Format add-data parameter for Windows (source;destination)
    add_data_param = f"{templates_dir};templates"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--noupx",
        "--name=BounceBlitz-Portable",
        f"--add-data={add_data_param}",
        os.path.join(script_dir, "app.py")
    ]

    print("[*] Building Portable Single-File Bounce Blitz Executable...")
    print("Running command:", " ".join(cmd))
    
    res = subprocess.run(cmd, cwd=script_dir)
    if res.returncode == 0:
        print("\n[SUCCESS] Bounce Blitz Single-File Executable compiled successfully!")
        exe_path = os.path.join(script_dir, "dist", "BounceBlitz-Portable.exe")
        print(f"Portable executable location: {exe_path}")
    else:
        print("\n[ERROR] PyInstaller build failed with return code:", res.returncode)

if __name__ == "__main__":
    build()
