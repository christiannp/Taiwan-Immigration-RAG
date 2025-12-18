from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import json
from backend.graph import agent, State

app = FastAPI()

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_msg = data.get("message")
    user_profile = data.get("user_profile", {})
    state: State = {"messages": [], "user_profile": user_profile, "retrieved_docs": []}

    # Append user message to state
    state["messages"].append({"role": "user", "content": user_msg})
    
    # Run the workflow
    result_stream = agent.invoke(state, return_intermediates=True)

    async def event_stream():
        for node_output in result_stream:
            # Emit intermediate status updates
            if isinstance(node_output, dict) and "status" in node_output:
                yield json.dumps({"type": "status", "content": node_output["status"]}) + "\n"
            # Final answer at END
            if isinstance(node_output, dict) and "done" in node_output:
                answer = state["messages"][-1]["content"]
                yield json.dumps({"type": "answer", "content": answer}) + "\n"
    return StreamingResponse(event_stream(), media_type="application/json")