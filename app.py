from layout import app
import callbacks

server = app.server

if __name__ == '__main__':
  app.run_server(debug=False, host="0.0.0.0", port=8080)
