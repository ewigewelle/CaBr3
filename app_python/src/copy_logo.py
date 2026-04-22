import shutil
import os

src = r"C:\Users\koehl\Downloads\Logo CaBr3.png"
dst = r"C:\Users\koehl\Downloads\cabr2\app_python\assets\logo.png"

try:
    shutil.copy(src, dst)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
