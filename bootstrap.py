"""MAKEVID Bootstrap - configura ambiente na 1a execucao e lanca o app."""

import sys
import os
import subprocess
import threading
from pathlib import Path

# Diretorio base: onde o executavel esta
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

PYTHON_DIR = BASE_DIR / "python"          # Python embutido
PYTHON_EXE = PYTHON_DIR / "python.exe"
PIP_SCRIPT  = PYTHON_DIR / "get-pip.py"
SITE_PKG    = PYTHON_DIR / "Lib" / "site-packages"
READY_FLAG  = BASE_DIR / "data" / ".setup_done"

PACKAGES = [
    "PySide6>=6.7.0",
    "pillow>=10.4.0",
    "opencv-python-headless>=4.10.0",
    "requests>=2.32.0",
    "numpy>=1.26.0",
    "huggingface-hub>=0.25.0",
    "edge-tts>=7.0.0",
    "sounddevice>=0.4.6",
    "soundfile>=0.12.0",
    "scipy>=1.11.0",
    "psutil>=6.0.0",
]

# torch >= 2.6 requerido para Python 3.13
# index-url escolhido automaticamente em _detect_torch_index()
PACKAGES_TORCH = [
    "torch>=2.6.0",
    "torchvision>=0.21.0",
    "diffusers>=0.31.0",
    "transformers>=4.44.0",
    "accelerate>=0.34.0",
    "safetensors>=0.4.5",
    "peft>=0.13.0",
]

# Mapa CUDA driver version -> whl index
_CUDA_INDEX = {
    "12.4": "https://download.pytorch.org/whl/cu124",
    "12.1": "https://download.pytorch.org/whl/cu121",
    "11.8": "https://download.pytorch.org/whl/cu118",
}
_CPU_INDEX = "https://download.pytorch.org/whl/cpu"


def _detect_torch_index() -> str:
    """Detecta CUDA disponivel e retorna o index-url correto do PyTorch."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return _CPU_INDEX
        # Pega versao do driver e mapeia para CUDA toolkit
        driver = result.stdout.strip().split("\n")[0].strip()
        major = int(driver.split(".")[0]) if driver else 0
        # Driver >= 525 suporta CUDA 12.1+, >= 550 suporta CUDA 12.4
        if major >= 550:
            return _CUDA_INDEX["12.4"]
        if major >= 525:
            return _CUDA_INDEX["12.1"]
        if major >= 450:
            return _CUDA_INDEX["11.8"]
        return _CPU_INDEX
    except Exception:
        return _CPU_INDEX


def _already_setup() -> bool:
    return READY_FLAG.exists()


def _mark_done():
    READY_FLAG.parent.mkdir(parents=True, exist_ok=True)
    READY_FLAG.write_text("ok")


def _pip_install(packages: list, log_fn=None, index_url: str = None):
    pip_cmd = [str(PYTHON_EXE), "-m", "pip", "install", "--quiet", "--no-warn-script-location"]
    if index_url:
        pip_cmd += ["--index-url", index_url]
    pip_cmd += packages
    proc = subprocess.Popen(
        pip_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(BASE_DIR),
    )
    for line in proc.stdout:
        line = line.strip()
        if line and log_fn:
            log_fn(line)
    proc.wait()
    return proc.returncode == 0


def _bootstrap_pip():
    """Instala pip no Python embutido se necessario."""
    result = subprocess.run(
        [str(PYTHON_EXE), "-m", "pip", "--version"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return True
    if PIP_SCRIPT.exists():
        r = subprocess.run([str(PYTHON_EXE), str(PIP_SCRIPT), "--quiet"], capture_output=True)
        return r.returncode == 0
    # Baixar get-pip.py
    import urllib.request
    try:
        urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", str(PIP_SCRIPT))
        r = subprocess.run([str(PYTHON_EXE), str(PIP_SCRIPT), "--quiet"], capture_output=True)
        return r.returncode == 0
    except Exception:
        return False


def _fix_pth(python_dir: Path):
    """Habilita site-packages no Python embutido (._pth precisa ter 'import site')."""
    for pth in python_dir.glob("python*._pth"):
        content = pth.read_text()
        if "import site" not in content:
            pth.write_text(content.rstrip() + "\nimport site\n")
        break


def launch_app():
    """Lanca o app principal usando o Python embutido."""
    main_py = BASE_DIR / "main.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE_DIR)
    subprocess.Popen([str(PYTHON_EXE), str(main_py)], cwd=str(BASE_DIR), env=env)


# ─────────────────────────────────────────────────────────────────────────────
#  GUI de setup (PySide6 se disponivel, senao tkinter, senao console)
# ─────────────────────────────────────────────────────────────────────────────

def run_setup_gui(on_done, on_error):
    """Tenta abrir janela de progresso. Retorna True se abriu GUI."""
    try:
        from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar
        from PySide6.QtCore import Qt, QThread, Signal
        from PySide6.QtGui import QFont

        app = QApplication.instance() or QApplication(sys.argv)

        win = QWidget()
        win.setWindowTitle("MAKEVID — Configurando")
        win.setFixedSize(480, 200)
        win.setStyleSheet("background: #0d0f1a; color: #e0e0e0;")

        lay = QVBoxLayout(win)
        lay.setContentsMargins(30, 30, 30, 30)
        lay.setSpacing(14)

        title = QLabel("MAKEVID")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #c8a84b;")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        status = QLabel("Preparando instalação...")
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet("color: #aaaaaa; font-size: 10pt;")
        lay.addWidget(status)

        bar = QProgressBar()
        bar.setRange(0, 0)  # indeterminate
        bar.setFixedHeight(6)
        bar.setTextVisible(False)
        bar.setStyleSheet(
            "QProgressBar { background: #1a1d2e; border: none; border-radius: 3px; }"
            "QProgressBar::chunk { background: #c8a84b; border-radius: 3px; }"
        )
        lay.addWidget(bar)

        sub = QLabel("Isso acontece apenas na primeira execução.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #555; font-size: 8pt;")
        lay.addWidget(sub)

        win.show()

        class Worker(QThread):
            progress = Signal(str)
            finished = Signal(bool, str)

            def run(self):
                try:
                    self.progress.emit("Verificando pip...")
                    _fix_pth(PYTHON_DIR)
                    if not _bootstrap_pip():
                        self.finished.emit(False, "Falha ao instalar pip.")
                        return
                    self.progress.emit("Instalando dependências principais...")
                    if not _pip_install(PACKAGES, self.progress.emit):
                        self.finished.emit(False, "Falha ao instalar pacotes.")
                        return
                    self.progress.emit("Detectando GPU...")
                    torch_index = _detect_torch_index()
                    backend = "CPU" if torch_index == _CPU_INDEX else f"CUDA ({torch_index.split('/')[-1]})"
                    self.progress.emit(f"Instalando PyTorch [{backend}] (pode demorar)...")
                    _pip_install(PACKAGES_TORCH, self.progress.emit, index_url=torch_index)
                    _mark_done()
                    self.finished.emit(True, "")
                except Exception as e:
                    self.finished.emit(False, str(e))

        worker = Worker()
        worker.progress.connect(lambda msg: status.setText(msg[:70]))
        worker.finished.connect(lambda ok, err: (
            (win.close(), on_done()) if ok else (win.close(), on_error(err))
        ))
        worker.start()
        app.exec()
        return True

    except ImportError:
        return False


def run_setup_console(on_done, on_error):
    """Fallback: instala em console sem GUI."""
    print("MAKEVID — Configurando ambiente (primeira execucao)...")
    _fix_pth(PYTHON_DIR)
    if not _bootstrap_pip():
        on_error("Falha ao instalar pip.")
        return
    print("Instalando dependencias...")
    if not _pip_install(PACKAGES, print):
        on_error("Falha ao instalar pacotes.")
        return
    print("Detectando GPU...")
    torch_index = _detect_torch_index()
    backend = "CPU" if torch_index == _CPU_INDEX else f"CUDA ({torch_index.split('/')[-1]})"
    print(f"Instalando PyTorch [{backend}] (pode demorar)...")
    _pip_install(PACKAGES_TORCH, print, index_url=torch_index)
    _mark_done()
    on_done()


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Adicionar site-packages do Python embutido ao path
    if SITE_PKG.exists():
        sys.path.insert(0, str(SITE_PKG))
        sys.path.insert(0, str(BASE_DIR))

    if _already_setup():
        launch_app()
        return

    def on_done():
        launch_app()

    def on_error(msg):
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "MAKEVID — Erro", f"Falha na configuração:\n{msg}\n\nVerifique sua conexão com a internet.")
        except Exception:
            print(f"ERRO: {msg}")
        sys.exit(1)

    if not run_setup_gui(on_done, on_error):
        run_setup_console(on_done, on_error)


if __name__ == "__main__":
    main()
