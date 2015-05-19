#!/bin/bash
echo bootstrap theme
curl https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap-theme.min.css > assets/styles/bootstrap-theme.min.css
echo bootstrap
curl https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css > assets/styles/bootstrap.min.css
echo bootstrap.js
curl https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/js/bootstrap.min.js > assets/script/bootstrap.min.js
echo jquery
curl https://ajax.googleapis.com/ajax/libs/jquery/1.11.2/jquery.min.js > assets/script/jquery.min.js
echo coffeescript
curl http://coffeescript.org/extras/coffee-script.js > assets/script/coffee-script.js
echo jumly
curl http://jumly.tmtk.net/public/jumly.min.js > assets/script/jumly.min.js