This project implements a minimal LangGraph agent that:

- Classifies a support ticket into an issue type
- Fetches a fake order from mock data
- Drafts a reply using a template

Stack: **FastAPI + LangGraph + Groq (Llama 3.1 8B Instant)**

Prerequisites:

Python 3.10+
A Groq API key

Setup

From the project root:
# 1. Install dependencies
pip install -r requirements.txt

# 2. Environment Variables
Create a .env file in the project root: (Add the below to .env file)
GROQ_API_KEY=your_groq_api_key_here

# 3. Run the API
From the project root:
uvicorn app.main:app --reload --port 8000

You should see:
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.

Health check:
curl http://127.0.0.1:8000/health

Expected response:
{"status": "ok"}

You can also open the interactive docs at:
http://127.0.0.1:8000/docs

# curl Example
Assume mock_data/orders.json contains an order:
{
  "order_id": "ORD1002",
  "customer_name": "David Lee",
  "email": "david.lee@example.com",
  "items": [ ... ]
}


On Windows PowerShell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/triage/invoke" `
-Method POST `
-Headers @{ "Content-Type" = "application/json" } `
-Body '{"ticket_text": "Hi, my order ORD1002 is late and I want a refund.", "order_id": null}'


# Example response
StatusCode        : 200
StatusDescription : OK
Content           : {"order_id":"ORD1002","issue_type":"refund_request","evidence":"The customer is requesting a
                    refund due to a late order, which is a common reason for refund requests. The customer has
                    also provided a ...}
RawContent        : HTTP/1.1 200 OK
                    Content-Length: 957
                    Content-Type: application/json
                    Date: Tue, 18 Nov 2025 17:57:14 GMT
                    Server: uvicorn

                    {"order_id":"ORD1002","issue_type":"refund_request","evidence":"The custom...}
Forms             : {}
Headers           : {[Content-Length, 957], [Content-Type, application/json], [Date, Tue, 18 Nov 2025 17:57:14
                    GMT], [Server, uvicorn]}
Images            : {}
InputFields       : {}
Links             : {}
ParsedHtml        : mshtml.HTMLDocumentClass

RawContentLength  : 957

Updated the code with a dummy LLM for the GitHub CI part, because the actual pipeline uses a groq api key to communicate with the model.

# Running tests locally
From the root folder
pytest -q
