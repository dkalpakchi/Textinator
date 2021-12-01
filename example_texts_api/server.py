import random
from flask import Flask, jsonify, request


app = Flask(__name__)


texts = [
    'Hello world!',
    'Bye world',
    'fgjsogifjisgfjgoisdjgf',
    'We can do what we can.'
]


@app.route("/get_datapoint", methods=['GET'])
def get_datapoint():
    key = request.args['key']
    return jsonify({
        'text': texts[int(key)]
    })


@app.route("/get_random_datapoint", methods=['GET'])
def get_random_datapoint():
    idx = random.randint(0, len(texts)-1)
    return jsonify({
        'id': idx,
        'text': texts[idx]
    })


@app.route("/size", methods=['GET'])
def size():
    return jsonify({
        'size': len(texts)
    })


if __name__ == '__main__':
    app.run(debug=True)
