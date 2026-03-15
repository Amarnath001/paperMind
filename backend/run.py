"""Server entry point (dev, Docker, Render)."""

import os

from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
