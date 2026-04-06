"""
VTutor INEVAL RAG Backend
Sistema de asistente virtual especializado en evaluación docente INEVAL Ecuador

Stack:
- FastAPI para API REST
- ChromaDB para almacenamiento vectorial
- sentence-transformers para embeddings
- DeepSeek API para generación de respuestas
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import os
import json
from datetime import datetime
import httpx
from pathlib import Path
import PyPDF2
import docx2txt

# Inicialización
app = FastAPI(title="VTutor INEVAL RAG API", version="1.0.0")

# CORS para permitir requests desde Moodle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: especificar dominio de Moodle
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
CHROMA_PERSIST_DIR = "./chroma_db"
DOCUMENTS_DIR = "./documentos_ineval"

# Inicializar modelo de embeddings
print("🔄 Cargando modelo de embeddings...")
embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("✅ Modelo de embeddings cargado")

# Inicializar ChromaDB
print("🔄 Inicializando ChromaDB...")
chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
collection = chroma_client.get_or_create_collection(
    name="ineval_knowledge",
    metadata={"description": "Base de conocimiento INEVAL para evaluación docente"}
)
print(f"✅ ChromaDB inicializado - Documentos: {collection.count()}")

# Crear directorios necesarios
Path(DOCUMENTS_DIR).mkdir(exist_ok=True)

# Modelos Pydantic
class ChatRequest(BaseModel):
    question: str
    user_id: Optional[str] = "anonymous"
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    timestamp: str

class DocumentInfo(BaseModel):
    id: str
    filename: str
    chunks: int
    uploaded_at: str

# Funciones auxiliares
def extract_text_from_pdf(file_path: str) -> str:
    """Extrae texto de un PDF"""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error extrayendo PDF {file_path}: {e}")
    return text

def extract_text_from_docx(file_path: str) -> str:
    """Extrae texto de un DOCX"""
    try:
        text = docx2txt.process(file_path)
        return text
    except Exception as e:
        print(f"Error extrayendo DOCX {file_path}: {e}")
        return ""

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Divide el texto en chunks con overlap"""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks

async def query_deepseek(prompt: str, context: str) -> str:
    """Consulta a DeepSeek API con contexto RAG"""
    if not DEEPSEEK_API_KEY:
        # Fallback a respuesta genérica si no hay API key
        return f"**Información encontrada en documentos INEVAL:**\n\n{context[:800]}...\n\n---\n\n💡 **Nota:** Configure DEEPSEEK_API_KEY para respuestas generadas por IA con análisis completo."
    
    system_prompt = """Eres VTutor INEVAL, un asistente virtual especializado en el modelo de evaluación docente INEVAL de Ecuador.

Tu función es ayudar a los docentes ecuatorianos a:
- Comprender el modelo de evaluación INEVAL 2024-2026
- Entender las 4 dimensiones de evaluación
- Prepararse para las evaluaciones oficiales
- Conocer los indicadores y rúbricas
- Resolver dudas sobre el proceso de evaluación

IMPORTANTE:
- Responde SIEMPRE basándote en los documentos oficiales INEVAL proporcionados
- Si la información no está en el contexto, indícalo claramente
- Usa lenguaje claro y profesional
- Proporciona ejemplos cuando sea útil
- Cita las fuentes cuando sea relevante
- Responde en español de Ecuador"""

    user_message = f"""Contexto de documentos oficiales INEVAL:

{context}

---

Pregunta del docente: {prompt}

Responde de manera clara y profesional, basándote únicamente en el contexto proporcionado."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error consultando DeepSeek: {e}")
        return f"**Información encontrada en documentos:**\n\n{context[:800]}..."

# Endpoints
@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "service": "VTutor INEVAL RAG API",
        "version": "1.0.0",
        "documents": collection.count(),
        "deepseek_configured": bool(DEEPSEEK_API_KEY)
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal de chat RAG
    
    Proceso:
    1. Genera embedding de la pregunta
    2. Busca documentos similares en ChromaDB
    3. Construye contexto con documentos relevantes
    4. Consulta a DeepSeek con contexto
    5. Retorna respuesta + fuentes
    """
    try:
        # 1. Generar embedding de la pregunta
        question_embedding = embedding_model.encode(request.question).tolist()
        
        # 2. Buscar documentos similares (top 5)
        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=5
        )
        
        if not results['documents'][0]:
            return ChatResponse(
                answer="No encuentro información específica sobre tu pregunta en la base de conocimiento INEVAL. ¿Podrías reformular tu pregunta o ser más específico?",
                sources=[],
                timestamp=datetime.now().isoformat()
            )
        
        # 3. Construir contexto
        context_parts = []
        sources = []
        
        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            source = metadata.get('source', 'Documento INEVAL')
            context_parts.append(f"[Fuente: {source}]\n{doc}")
            if source not in sources:
                sources.append(source)
        
        context = "\n\n---\n\n".join(context_parts)
        
        # 4. Generar respuesta con LLM
        answer = await query_deepseek(request.question, context)
        
        # 5. Retornar respuesta
        return ChatResponse(
            answer=answer,
            sources=sources,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Sube y procesa un documento INEVAL
    
    Soporta: PDF, DOCX, TXT
    """
    try:
        # Validar formato
        allowed_extensions = ['.pdf', '.docx', '.txt']
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(400, f"Formato no soportado. Use: {', '.join(allowed_extensions)}")
        
        # Guardar archivo
        file_path = os.path.join(DOCUMENTS_DIR, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Extraer texto según formato
        if file_ext == '.pdf':
            text = extract_text_from_pdf(file_path)
        elif file_ext == '.docx':
            text = extract_text_from_docx(file_path)
        else:  # .txt
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        if not text.strip():
            raise HTTPException(400, "No se pudo extraer texto del documento")
        
        # Dividir en chunks
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        
        # Generar embeddings para cada chunk
        embeddings = embedding_model.encode(chunks).tolist()
        
        # Generar IDs únicos
        doc_id = file.filename.replace('.', '_')
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        
        # Metadatos
        metadatas = [
            {
                "source": file.filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "uploaded_at": datetime.now().isoformat()
            }
            for i in range(len(chunks))
        ]
        
        # Almacenar en ChromaDB
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        
        return {
            "status": "success",
            "filename": file.filename,
            "chunks_created": len(chunks),
            "message": f"Documento '{file.filename}' procesado y almacenado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error procesando documento: {str(e)}")

@app.get("/api/documents", response_model=List[DocumentInfo])
async def list_documents():
    """Lista todos los documentos en la base de conocimiento"""
    try:
        # Obtener todos los metadatos
        all_data = collection.get()
        
        # Agrupar por documento
        docs_dict = {}
        for metadata in all_data['metadatas']:
            source = metadata.get('source', 'unknown')
            if source not in docs_dict:
                docs_dict[source] = {
                    'chunks': 0,
                    'uploaded_at': metadata.get('uploaded_at', 'unknown')
                }
            docs_dict[source]['chunks'] += 1
        
        # Convertir a lista
        documents = [
            DocumentInfo(
                id=source.replace('.', '_'),
                filename=source,
                chunks=info['chunks'],
                uploaded_at=info['uploaded_at']
            )
            for source, info in docs_dict.items()
        ]
        
        return documents
        
    except Exception as e:
        raise HTTPException(500, f"Error listando documentos: {str(e)}")

@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    """Elimina un documento de la base de conocimiento"""
    try:
        # Obtener todos los IDs que coincidan con el documento
        all_data = collection.get()
        ids_to_delete = [
            id for id, meta in zip(all_data['ids'], all_data['metadatas'])
            if meta.get('source', '').replace('.', '_') == document_id
        ]
        
        if not ids_to_delete:
            raise HTTPException(404, "Documento no encontrado")
        
        # Eliminar
        collection.delete(ids=ids_to_delete)
        
        return {
            "status": "success",
            "chunks_deleted": len(ids_to_delete),
            "message": f"Documento eliminado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error eliminando documento: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("🚀 VTutor INEVAL RAG Backend")
    print("="*50)
    print(f"📚 Documentos en base: {collection.count()}")
    print(f"🔑 DeepSeek API: {'✅ Configurado' if DEEPSEEK_API_KEY else '❌ No configurado'}")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8081)
