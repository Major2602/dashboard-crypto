import os
from layout import app
import callbacks

server = app.server

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run_server(debug=False, host="0.0.0.0", port=port)
