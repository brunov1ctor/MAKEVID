"""Build script - gera MAKEVID.exe. Uso: python build.py"""

import PyInstaller.__main__
import sys

PyInstaller.__main__.run([
    "main.py",
    "--name=MAKEVID",
    "--onedir",
    "--windowed",
    "--noconfirm",
    "--clean",
    # Incluir pacotes que PyInstaller pode perder
    "--hidden-import=customtkinter",
    "--hidden-import=torch",
    "--hidden-import=diffusers",
    "--hidden-import=transformers",
    "--hidden-import=accelerate",
    "--hidden-import=safetensors",
    "--hidden-import=huggingface_hub",
    # Dados extras
    "--add-data=makevid;makevid",
    # Icone (se tiver)
    # "--icon=assets/icon.ico",
])

print("\n\nBuild completo! Executavel em: dist/MAKEVID/MAKEVID.exe")
