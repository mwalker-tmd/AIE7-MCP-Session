import requests
from requests.structures import CaseInsensitiveDict
    
url = "https://api.metals.dev/v1/latest?api_key=G2Y3XHWZ9EICDHAE7CRT733AE7CRT&currency=USD&unit=toz"
headers = CaseInsensitiveDict()
headers["Accept"] = "application/json"

resp = requests.get(url, headers=headers)
print(resp)
data = resp.json()
print(data)
