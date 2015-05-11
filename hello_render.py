from flask import Flask
from flask import render_template
import flask
from flask import request

app = Flask(__name__)

@app.route("/")
@app.route("/<name>")
def hello(name=None):
	resp = "I got the following request: "
	for key in request.args:
		resp = resp + key + ":" + request.args[key]+"<br>"
	return resp
		#render_template('hello.html', name=name)

	#return render_template('hello.html', name=name)

if __name__ == "__main__":
    app.run()
