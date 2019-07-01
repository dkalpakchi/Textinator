var express = require('express')
var bodyParser = require('body-parser')
var fs = require('fs')
var wtf = require('wtf_wikipedia');
var app = express()

app.use(bodyParser.json())

app.post('/', function(request, response) {
  console.log('POST /')
  var data = request.body;
  response.writeHead(200, {'Content-Type': 'text/plain; charset=utf-8'})
  console.log(wtf(data['wikitext']).text())
  response.end(wtf(data['wikitext']).text())
})

port = 3000
app.listen(port)
console.log(`Listening at http://localhost:${port}`)
