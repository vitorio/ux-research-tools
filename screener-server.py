## ux-research-tools - Tools to reduce UX research administrivia
## 
## Written in 2014-2015 by Vitorio Miliano <http://vitor.io/>
## 
## To the extent possible under law, the author has dedicated all copyright and related and neighboring rights to this software to the public domain worldwide.  This software is distributed without any warranty.
## 
## You should have received a copy of the CC0 Public Domain Dedication along with this software.  If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

__author__ = 'vitorio'

from gevent.wsgi import WSGIServer
from screener import app

http_server = WSGIServer(('', 5000), app)
http_server.serve_forever()
