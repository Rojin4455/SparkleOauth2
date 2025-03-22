
from flask import Flask, request, Response
import requests

app = Flask(__name__)

# This is your Django server address
DJANGO_SERVER = "http://localhost:8000"

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(path):
    # Build the target URL to your Django app
    target_url = f"{DJANGO_SERVER}/{path}"
    
    # Copy original headers and add the ngrok skip header
    headers = {key: value for key, value in request.headers.items() 
               if key.lower() not in ('host', 'content-length')}
    headers['ngrok-skip-browser-warning'] = 'true'
    
    # Forward the request with appropriate method
    try:
        if request.method == 'GET':
            resp = requests.get(
                target_url, 
                params=request.args,
                headers=headers,
                timeout=10
            )
        elif request.method == 'POST':
            resp = requests.post(
                target_url,
                data=request.get_data(),
                headers=headers,
                timeout=10
            )
        elif request.method == 'PUT':
            resp = requests.put(
                target_url,
                data=request.get_data(),
                headers=headers,
                timeout=10
            )
        elif request.method == 'DELETE':
            resp = requests.delete(
                target_url,
                headers=headers,
                timeout=10
            )
        
        # Log the response for debugging
        print(f"Proxied {request.method} request to {path}")
        print(f"Response status: {resp.status_code}")
        print(f"Response body: {resp.text[:200]}...")
        
        # Return the response from Django to the original requester
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.raw.headers.items()
                  if name.lower() not in excluded_headers]
        
        return Response(resp.content, resp.status_code, headers)
    
    except Exception as e:
        print(f"Proxy error: {str(e)}")
        return Response(f"Proxy error: {str(e)}", 500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
