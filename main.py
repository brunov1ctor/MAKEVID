"""MAKEVID - Entry point."""

import traceback
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Suprime bug do Python 3.13 no GC de threads daemon
import threading
_orig_del = getattr(threading._DeleteDummyThreadOnDel, "__del__", None)
if _orig_del:
    def _safe_del(self):
        try:
            _orig_del(self)
        except TypeError:
            pass
    threading._DeleteDummyThreadOnDel.__del__ = _safe_del

try:
    from makevid.core.logger import setup_logging
    setup_logging()

    from makevid.qt.app import run
    run()
except Exception as e:
    traceback.print_exc()
    input("\nAperte ENTER para fechar...")
