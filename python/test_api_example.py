from fastapi.testclient import TestClient

from .main import app

client = TestClient(app)
age = 8
sex = 'M'

def test_read_main():
	response = client.get(f"/predict?age={age}&sex={sex}')")
	assert response.status_code == 200
	assert response.json() == {'survived':1}