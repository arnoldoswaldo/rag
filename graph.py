from typing import TypedDict, List

from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# ── Configuración ─────────────────────────────────────────────────────────────
CONNECTION_STRING = "postgresql+psycopg://langchain:langchain@localhost:5432/rag_db"
COLLECTION_NAME   = "rag_collection"

# ── Recursos compartidos (se crean una sola vez) ──────────────────────────────
# Evita reinstanciar embeddings y vectorstore en cada llamada al grafo
_embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

_vectorstore = PGVector(
    embeddings=_embeddings,
    collection_name=COLLECTION_NAME,
    connection=CONNECTION_STRING,
    use_jsonb=True,          # debe coincidir con ingest.py
)

_retriever = _vectorstore.as_retriever(search_kwargs={"k": 3})

_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0,                    # respuestas más deterministas para RAG
)

# ── Estado de la aplicación ───────────────────────────────────────────────────
class RAGState(TypedDict):
    question: str
    context:  List[Document]
    response: str

# ── Nodo de Recuperación ──────────────────────────────────────────────────────
def retrieve_node(state: RAGState) -> dict:
    print("🔍 [Nodo: Recuperación] Buscando contexto en PGVector...")
    try:
        retrieved_docs = _retriever.invoke(state["question"])
    except Exception as exc:
        print(f"❗ Error al recuperar documentos: {exc}")
        raise RuntimeError(
            "No se pudo conectar a PGVector. "
            "Verifica que el contenedor Docker esté corriendo."
        ) from exc

    if not retrieved_docs:
        print("⚠️  No se encontraron fragmentos relevantes para la pregunta.")

    print(f"   → {len(retrieved_docs)} fragmento(s) recuperado(s).")
    return {"context": retrieved_docs}

# ── Nodo de Generación ────────────────────────────────────────────────────────
_PROMPT_TEMPLATE = """\
Eres un asistente experto que responde preguntas basándose ÚNICAMENTE en el contexto proporcionado.
Si la respuesta no se encuentra en el contexto, responde exactamente:
"No encontré información suficiente en el documento para responder esta pregunta."

<Contexto>
{context}
</Contexto>

<Pregunta>
{question}
</Pregunta>

Respuesta:"""

def generate_node(state: RAGState) -> dict:
    print("🤖 [Nodo: Generación] Produciendo respuesta con Gemini...")

    if not state["context"]:
        return {"response": "No encontré información suficiente en el documento para responder esta pregunta."}

    context_text = "\n---\n".join(
        f"[Fragmento {i+1}]\n{doc.page_content}"
        for i, doc in enumerate(state["context"])
    )

    prompt = _PROMPT_TEMPLATE.format(
        context=context_text,
        question=state["question"],
    )

    try:
        response = _llm.invoke(prompt)
    except Exception as exc:
        print(f"❗ Error al llamar a Gemini: {exc}")
        raise RuntimeError(
            "Error al generar la respuesta. "
            "Verifica tu GOOGLE_API_KEY y los límites de cuota."
        ) from exc

    return {"response": response.content}

# ── Orquestación con LangGraph ────────────────────────────────────────────────
workflow = StateGraph(RAGState)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)

workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

# MemorySaver habilita el thread_id que pasa main.py
# (permite conversaciones independientes por hilo)
_checkpointer = MemorySaver()
rag_app = workflow.compile(checkpointer=_checkpointer)