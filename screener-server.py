__author__ = 'vitorio'

from gevent.wsgi import WSGIServer
from screener import app

http_server = WSGIServer(('', 5000), app)
http_server.serve_forever()
