import requests
import time

url = "http://127.0.0.1:8000/api/reference/upload"
files = {'file': ('datest-1.pdf', open('test_pdfs/teachers.pdf', 'rb'))}
res = requests.post(url, files=files)
data = res.json()
print("Upload response:", data)

exam_id = data.get("exam_id")
if exam_id:
    for i in range(15):
        time.sleep(1)
        status_res = requests.get(f"http://127.0.0.1:8000/api/exam/{exam_id}/status")
        status_data = status_res.json()
        print(f"Status check {i}:", status_data)
        if status_data.get("status") in ("reference_ready", "error"):
            break
