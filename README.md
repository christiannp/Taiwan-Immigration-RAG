# 🇹🇼 Taiwan Immigration RAG

The official Taiwan immigration website provides very detailed explanations, including many specific cases. However, this level of detail is quite difficult to understand in practice. Rather than overwhelming users with all available information, we designed a system that personalizes responses based on the user’s situation. The LLM first asks targeted follow-up questions to gather the necessary context before generating an answer. As a result, the system delivers personalized and citation-backed responses in multiple languages.

This system combines:
- **LangGraph** for intelligent, personalized agent workflows  
- **FastAPI** for a streaming backend  
- **Qdrant Hybrid Search** (Dense + Sparse)  
- **Google Gemini Pro** for reasoning and embeddings  
- **Next.js 14 + Vercel AI SDK** for a modern chat UI  

---

## ✨ Key Features

- 🔍 **Official Knowledge Only**  
  Uses only content (HTML & PDFs) from  
  👉 https://www.immigration.gov.tw/

- 🧠 **Personalized Immigration Agent**
  - Detects missing critical info (nationality, visa type)
  - Asks clarifying questions when required
  - Adapts answers based on user profile

- 🌏 **Multilingual Support**
  - User can ask in **English, Indonesian, Vietnamese**, etc.
  - Retrieval is done in **Traditional Chinese** for accuracy
  - Answers are returned in the **user’s original language**

- 📚 **Hybrid Search (Best of Both Worlds)**
  - Dense vectors: `text-embedding-004`
  - Sparse keyword matching for legal terms
  - Qdrant RRF fusion for high recall & precision

- 🔄 **Incremental Indexing**
  - Only re-indexes changed pages or PDFs
  - Uses SQLite fingerprints for efficiency

- ⚡ **Streaming Responses**
  - Intermediate reasoning/status updates
  - Token-by-token final answers
  - Citations included (e.g. `[1]`, `[2]`)

---

## 🧱 System Architecture

```text
┌──────────────┐
│   Next.js    │  ← Chat UI (Vercel AI SDK)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   FastAPI    │  ← Streaming /chat endpoint
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  LangGraph   │  ← Agent Workflow
│──────────────│
│ Profile Check│
│ Questioner   │
│ Translator   │
│ Retriever    │
│ Grader       │
│ Generator    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Qdrant     │  ← Hybrid Search
└──────────────┘
