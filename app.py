from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from bling.api import mod as bling_module

app = Flask(__name__)
CORS(app)

app.register_blueprint(bling_module, url_prefix="/bling")


@app.errorhandler(Exception)
def global_error_handler(e):
    if isinstance(e, HTTPException):
        return e  # pass the exception on unchanged
    response = jsonify(message="Server error")
    response.status_code = 500
    return response


@app.route("/")
def index():
    return "Hello from EW!", 200


if __name__ == "__main__":
    app.run()
