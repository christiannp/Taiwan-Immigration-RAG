from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
import google.generativeai as genai
from qdrant_client import QdrantClient, models
import google.api_core.exceptions as g_exc

# State definition
class State(TypedDict):
    messages: list       # conversation messages
    user_profile: dict   # e.g. {'nationality': '...', 'visa': '...'}
    retrieved_docs: list # list of (doc_text, source)

# Initialize Gemini model for reasoning
llm = genai.GenerativeModel("gemini-1.5-pro-latest")
client = genai.GenerativeModel("text-embedding-004")
qdrant = QdrantClient(url=os.getenv("QDRANT_URL"))

# Node: Check if profile info is complete
def profile_check(state: State):
    missing = []
    if not state["user_profile"].get("nationality"):
        missing.append("nationality")
    if not state["user_profile"].get("visa"):
        missing.append("visa_type")
    if missing:
        return {"missing": missing}
    return {"ok": True}

# Node: Ask user for missing profile info
def ask_profile(state: State):
    missing = state.get("missing", [])
    prompts = []
    if "nationality" in missing:
        prompts.append("請問您的國籍是什麼？")  # in Chinese for example
    if "visa_type" in missing:
        prompts.append("您目前持有什麼簽證？")
    question = " ".join(prompts)
    # Append to messages as a bot prompt
    state["messages"].append({"role": "assistant", "content": question})
    return {}

# Node: Translate user query to Traditional Chinese
def translate_query(state: State):
    user_msg = state["messages"][-1]["content"]
    prompt = f"將以下問題翻譯為繁體中文：\n{user_msg}"
    response = llm.generate_content(prompt)
    chinese_query = response.text
    state["chinese_query"] = chinese_query
    return {}

# Node: Hybrid Retriever from Qdrant
def hybrid_retriever(state: State):
    query = state.get("chinese_query", "")
    if not query:
        return {"fail": "No query provided"}
    # Embed the query in Chinese
    embedding_resp = client.generate_content(query)
    vector = embedding_resp.prediction
    # For sparse terms, simplistic approach: split query into keywords (could use an actual sparse encoder)
    keywords = query.split()
    # Use Qdrant RRF hybrid search
    try:
        result = qdrant.query_points(
            collection_name="immigration",
            prefetch=[
                models.Prefetch(
                    query=vector,
                    using="dense",
                    limit=5
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=list(range(len(keywords))), 
                        values=[1.0]*len(keywords)
                    ),
                    using="sparse",
                    limit=5
                )
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF)
        )
    except Exception as e:
        return {"fail": str(e)}
    docs = []
    for hit in result:
        docs.append((hit.payload["text"], hit.payload.get("url")))
    state["retrieved_docs"] = docs
    return {}

# Node: Grade retrieved docs (check if sufficient)
def grade_docs(state: State):
    question = state["messages"][-1]["content"]
    docs_text = "\n\n".join([d for d,_ in state.get("retrieved_docs", [])])
    prompt = f"問題：{question}\n根據以上文件，請判斷這些文件是否足夠回答問題。"
    resp = llm.generate_content(prompt)
    if "不相關" in resp.text or "無法回答" in resp.text:
        return {"insufficient": True}
    return {}

# Node: Generate final answer with citations
def generate_answer(state: State):
    user_lang = "English"  # assume original user language known
    question = state["messages"][-1]["content"]
    # Combine docs for context
    combined_docs = ""
    for idx, (text, url) in enumerate(state.get("retrieved_docs", []), 1):
        combined_docs += f"[{idx}] {text}\n\n"
    prompt = (f"以下資料擷取自台灣移民署公佈資料：\n{combined_docs}\n"
              f"請用{user_lang}回答問題「{question}」，並引用來源編號。")
    response = llm.generate_content(prompt)
    answer = response.text
    state["messages"].append({"role": "assistant", "content": answer})
    return {"done": True}

# Build the StateGraph workflow
workflow = StateGraph(State)
workflow.add_node("profile_check", profile_check)
workflow.add_node("ask_profile", ask_profile)
workflow.add_node("translate_query", translate_query)
workflow.add_node("hybrid_retriever", hybrid_retriever)
workflow.add_node("grade_docs", grade_docs)
workflow.add_node("generate_answer", generate_answer)

# Define edges
workflow.add_edge(START, "profile_check")
# If missing, go to ask_profile; otherwise to translation
workflow.add_conditional_edges("profile_check", lambda s: "ask" if "missing" in s else "go", 
                              {"ask": "ask_profile", "go": "translate_query"})
workflow.add_edge("ask_profile", END)  # after asking, wait for user
workflow.add_edge("translate_query", "hybrid_retriever")
workflow.add_edge("hybrid_retriever", "grade_docs")
workflow.add_conditional_edges("grade_docs", lambda s: "gen" if "retrieved_docs" in s else "translate", 
                              {"gen": "generate_answer", "translate": "hybrid_retriever"})
workflow.add_edge("generate_answer", END)

agent = workflow.compile()