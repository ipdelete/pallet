import requests
from requests.exceptions import RequestException

class Registry:
    def __init__(self):
        self.url = "http://localhost:5000"

    def is_alive(self) -> bool:
        try:
            response = requests.get(f'{self.url}/v2/')
            return response.status_code in (200, 401)
        except RequestException as e:
            return False
    
    def list_repositories(self):
        try:
            response = requests.get(f"{self.url}/v2/_catalog/")
            if response.status_code == 200:
                return response.json()
            return None
        except RequestException as e:
            return None
    
    def list_tags(self, repo):
        try:
            print(f"{self.url}/v2/{repo}/tags/list")
            response = requests.get(f"{self.url}/v2/{repo}/tags/list")
            if response.status_code == 200:
                return response.json()
            return None
        except RequestException as e:
            print("tag requested, error returned")
            return None
        
    def get_manifest(self, repo, tag):
        try:
            headers = {
                'Accept': 'application/vnd.oci.image.manifest.v1+json'
            }
            response = requests.get(f"{self.url}/v2/{repo}/manifests/{tag}", headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed: {response.status_code} - {response.text[:500]}")
            return None
        except RequestException as e:
            return None
        
    def get_blob(self, repo, digest):
        try:
            response = requests.get(f"{self.url}/v2/{repo}/blobs/{digest}")
            if response.status_code == 200:
                return response.content
            return None
        except RequestException as e:
            return None
