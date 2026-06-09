"""MAKEVID - Entry point."""

import traceback

try:
    from makevid.core.logger import setup_logging
    setup_logging()

    from makevid.ui.app import MakeVidApp
    app = MakeVidApp()
    app.mainloop()
except Exception as e:
    traceback.print_exc()
    input("\nAperte ENTER para fechar...")
