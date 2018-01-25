# coding=utf-8
from flask import Flask, stream_with_context, url_for, Response, request, send_file
from StringIO import StringIO
from functools import wraps

import re
import mimetypes
import os
import cgi
import urllib2


app = Flask(__name__)
PATTERN = re.compile('(\d{4}-\d{2}-\d{2})')
# 工作目录
WORKDIR = os.getcwd()


def check_auth(username, password):
    return username == 'username' and password == 'password'


def authenticate():
    return Response(
        u'认证失败', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


def sort_filename(x):
    data = PATTERN.findall(x)
    if not data:
        return ''
    return data[0]


def show_dir_list(dir_path):
    f = StringIO()
    # list directory
    # 展示相对路径
    abs_path = os.path.relpath(dir_path, WORKDIR)
    if abs_path == '.':
        abs_path = ''
    f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
    f.write("<html>\n<title>Directory listing for /%s</title>\n" % abs_path)
    f.write("<body>\n<h2>Directory listing for /%s</h2>\n" % abs_path)
    f.write("<hr>\n<ul>\n")

    dir_list = os.listdir(dir_path)
    # 根据文件日期倒叙排序显示
    dir_list.sort(key=lambda x: sort_filename(x), reverse=True)
    # 只列出最近30个
    for name in dir_list[:30]:
        fn = os.path.join(abs_path, name)
        uri = url_for('link', file_name=urllib2.quote(fn))
        f.write('<li><a href="%s">%s</a>\n'
                % (uri, cgi.escape(name)))
    f.write("</ul>\n<hr>\n</body>\n</html>\n")
    f.seek(0)
    return f


@app.route('/', methods=['GET'])
@requires_auth
def get_file():
    f = show_dir_list(WORKDIR)
    return f.read()


@app.route('/<file_name>', methods=['GET'])
@requires_auth
def link(file_name):
    file_name = urllib2.unquote(file_name)
    file_path = os.path.join(WORKDIR, file_name)
    if os.path.isdir(file_path) is True:
        resp = show_dir_list(file_path)
        return resp.read()

    if not os.path.exists(file_path):
        return 'File not exists!'

    # 生成文件流
    def generate():
        with open(file_path, "rb") as f:
            while True:
                b = f.read(1024)
                if len(b) == 0:
                    f.close()
                    break
                yield b

    # 检测mimetype
    mt, _ = mimetypes.guess_type(file_name)
    resp = Response(generate(), mimetype=mt)
    resp.headers.add('content-length', str(os.path.getsize(file_name)))
    return resp


if __name__ == '__main__':
    app.run(port=1087, host='0.0.0.0', threaded=True)
