import requests
 
url = 'http://127.0.0.1:5000/'
payload = {'q':'python'}
r = requests.get(url, params=payload)
print(r.content)