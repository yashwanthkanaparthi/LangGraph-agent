import os,json, re
from typing import Optional, List, Dict, Any, Annotated
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq

load_dotenv()

ORDERS = json.load(open(r'mock_data/orders.json'))
ISSUES = json.load(open(r'mock_data/issues.json'))
REPLIES = json.load(open(r'mock_data/replies.json'))


llm = ChatGroq(
    model= "llama-3.1-8b-instant",
    temperature=0.1,
    api_key=os.getenv("GROQ_API_KEY"),
)


class TriageState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    ticket_text: str
    order_id: Optional[str]
    issue_type: Optional[str]
    evidence: Optional[str]
    recommendation: Optional[str]
    order: Optional[Dict[str, Any]]
    reply_text: Optional[str]


ORDER_ID_RE = re.compile(r"(ORD\d{4})", re.IGNORECASE)


def extract_order_id(text: str, order_id: Optional[str]) -> Optional[str]:
    if order_id:
        return order_id
    m = ORDER_ID_RE.search(text or "")
    if m:
        return m.group(1).upper()
    return None


def ingest(state: TriageState) -> Dict[str, Any]:
    msgs = state.get("messages", [])
    msgs.append(HumanMessage(content=state["ticket_text"]))
    return {"messages": msgs}


def classify_issue(state: TriageState) -> Dict[str, Any]:
    text = state["ticket_text"]
    lower = text.lower()

    issue_type = "unknown"
    for rule in ISSUES:
        kw = rule.get("keyword", "").lower()
        if kw and kw in lower:
            issue_type = rule.get("issue_type", "unknown")
            break

    sys = (
        "You are a customer support triage assistant. "
        "Given a ticket and a precomputed issue_type, briefly explain why this "
        "issue_type is reasonable and what the support agent should do next. "
        "Respond in strict JSON with keys: evidence, recommendation."
    )

    msgs = [
        SystemMessage(content=sys),
        HumanMessage(content=f"TICKET:\n{text}\n\nISSUE_TYPE: {issue_type}"),
    ]
    raw = llm.invoke(msgs)
    data = json.loads(raw.content)

    return {
        "issue_type": issue_type,
        "evidence": data.get("evidence"),
        "recommendation": data.get("recommendation"),
        "messages": [AIMessage(content=f"Issue classified as: {issue_type}")],
    }


def fetch_order(state: TriageState) -> Dict[str, Any]:
    text = state["ticket_text"]
    order_id = extract_order_id(text, state.get("order_id"))
    order = None
    if order_id:
        for o in ORDERS:
            if o.get("order_id", "").upper() == order_id.upper():
                order = o
                break

    if not order_id:
        msg = AIMessage(content="No order_id found in payload or ticket text.")
    elif not order:
        msg = AIMessage(content=f"Order {order_id} not found in mock data.")
    else:
        msg = AIMessage(content=f"Fetched order {order_id} from mock data.")

    return {"order_id": order_id, "order": order, "messages": [msg]}


def render_reply(issue_type: str, order: Dict[str, Any]) -> str:
    template = next(
        (r["template"] for r in REPLIES if r.get("issue_type") == issue_type),
        "Hi {{customer_name}}, we are reviewing order {{order_id}}.",
    )
    return template.replace(
        "{{customer_name}}", order.get("customer_name", "Customer")
    ).replace(
        "{{order_id}}", order.get("order_id", "N/A")
    )


def draft_reply(state: TriageState) -> Dict[str, Any]:
    issue_type = state.get("issue_type") or "unknown"
    order = state.get("order") or {}
    reply_text = render_reply(issue_type, order)
    return {"reply_text": reply_text, "messages": [AIMessage(content="Drafted reply.")]}
    

def build_graph():
    g = StateGraph(TriageState)
    g.add_node("ingest", ingest)
    g.add_node("classify_issue", classify_issue)
    g.add_node("fetch_order", fetch_order)
    g.add_node("draft_reply", draft_reply)
    g.add_edge(START, "ingest")
    g.add_edge("ingest", "classify_issue")
    g.add_edge("classify_issue", "fetch_order")
    g.add_edge("fetch_order", "draft_reply")
    g.add_edge("draft_reply", END)
    g.set_entry_point("ingest")
    return g.compile()


graph_app = build_graph()

app = FastAPI(title="Groq LangGraph Triage API")


class TriageInput(BaseModel):
    ticket_text: str
    order_id: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/triage/invoke")
def triage_invoke(body: TriageInput):
    state: TriageState = {
        "messages": [],
        "ticket_text": body.ticket_text,
        "order_id": body.order_id,
        "issue_type": None,
        "evidence": None,
        "recommendation": None,
        "order": None,
        "reply_text": None,
    }

    result = graph_app.invoke(state)

    if not result.get("order_id"):
        raise HTTPException(status_code=400, detail="order_id missing and not found in text")
    if result.get("order") is None:
        raise HTTPException(status_code=404, detail="order not found")

    return {
        "order_id": result["order_id"],
        "issue_type": result["issue_type"],
        "evidence": result["evidence"],
        "recommendation": result["recommendation"],
        "order": result["order"],
        "reply_text": result["reply_text"],
    }
