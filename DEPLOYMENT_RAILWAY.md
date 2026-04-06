# 🚂 DEPLOYMENT EN RAILWAY - VTutor INEVAL RAG

Guía completa para desplegar el backend RAG en Railway.app

---

## 🐛 PROBLEMA SOLUCIONADO

**Error original:**
```
pydantic-core v2.14.1 failed building wheel
TypeError: ForwardRef._evaluate() missing 'recursive_guard'
```

**Causa:** Incompatibilidad entre `pydantic==2.5.0` y Python 3.13

**Solución:** Usar `requirements_railway.txt` actualizado con versiones compatibles

---

## ✅ ARCHIVOS ACTUALIZADOS

### 1. requirements_railway.txt (USAR ESTE)

```txt
# Framework web
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.20

# Base de datos vectorial
chromadb==0.5.23

# Embeddings y ML
sentence-transformers==3.3.1
torch==2.5.1+cpu --extra-index-url https://download.pytorch.org/whl/cpu

# Procesamiento de documentos
PyPDF2==3.0.1
docx2txt==0.8
python-docx==1.1.2

# HTTP client
httpx==0.27.2

# Utilities - Compatible con Python 3.11+
pydantic==2.10.6
pydantic-settings==2.7.1
python-dotenv==1.0.1

# Logging
python-json-logger==3.2.1
```

**Cambios clave:**
- ✅ `pydantic==2.10.6` (antes: 2.5.0) - Compatible con Python 3.13
- ✅ `fastapi==0.115.6` (antes: 0.104.1) - Versión actualizada
- ✅ `chromadb==0.5.23` (antes: 0.4.18) - Versión estable reciente
- ✅ `uvicorn==0.34.0` (antes: 0.24.0) - Actualizado

### 2. Procfile

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 3. runtime.txt (OPCIONAL - Recomendar Python 3.11)

```
python-3.11.11
```

**Nota:** Railway por defecto usa Python 3.13. Si quieres forzar 3.11 (más estable), usa este archivo.

---

## 🚀 DEPLOYMENT EN RAILWAY

### Opción 1: Desde GitHub (RECOMENDADO)

#### Paso 1: Preparar Repositorio

```bash
# 1. Crear repositorio local
cd vtutor_ineval_rag/backend/

# 2. Reemplazar requirements.txt con la versión actualizada
rm requirements.txt
cp requirements_railway.txt requirements.txt

# 3. Agregar Procfile
echo "web: uvicorn main:app --host 0.0.0.0 --port \$PORT" > Procfile

# 4. (Opcional) Agregar runtime.txt para Python 3.11
echo "python-3.11.11" > runtime.txt

# 5. Inicializar git
git init
git add .
git commit -m "Initial commit - VTutor INEVAL RAG"

# 6. Crear repo en GitHub y pushear
git remote add origin https://github.com/TU_USUARIO/vtutor-ineval-rag.git
git branch -M main
git push -u origin main
```

#### Paso 2: Conectar con Railway

1. **Ir a Railway.app:**
   - https://railway.app
   - Login con GitHub

2. **Crear nuevo proyecto:**
   - Click "New Project"
   - Seleccionar "Deploy from GitHub repo"
   - Seleccionar tu repositorio `vtutor-ineval-rag`

3. **Railway detectará automáticamente:**
   ```
   ✅ Python detectado
   ✅ requirements.txt encontrado
   ✅ Procfile encontrado
   ```

4. **Configurar variables de entorno:**
   - En Railway dashboard → Variables
   - Agregar:
   ```
   DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   PORT=8080
   CHROMA_PERSIST_DIR=/app/chroma_db
   DOCUMENTS_DIR=/app/documentos_ineval
   ```

5. **Deploy:**
   - Railway empezará a construir automáticamente
   - Esperar ~3-5 minutos

6. **Obtener URL pública:**
   - Railway dashboard → Settings → Generate Domain
   - URL tipo: `vtutor-ineval-rag-production.up.railway.app`

---

### Opción 2: Deploy Directo desde CLI

```bash
# 1. Instalar Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Crear proyecto
railway init

# 4. Configurar variables de entorno
railway variables set DEEPSEEK_API_KEY=sk-xxx

# 5. Deploy
railway up
```

---

## 📝 ESTRUCTURA DE ARCHIVOS PARA RAILWAY

```
backend/
├── main.py                      # Archivo principal FastAPI
├── requirements.txt             # USAR requirements_railway.txt
├── Procfile                     # Comando de inicio
├── runtime.txt                  # (Opcional) Versión Python
├── .env.example                 # NO subir .env real
├── load_documents.py            # Scripts auxiliares
├── test_api.py                  
└── documentos_ineval/          # Crear después del deploy
```

**IMPORTANTE:** NO subir a GitHub:
- ❌ `.env` (contiene API keys)
- ❌ `chroma_db/` (se genera en deploy)
- ❌ `__pycache__/`

**Crear .gitignore:**
```gitignore
.env
chroma_db/
__pycache__/
*.pyc
.venv/
venv/
```

---

## 🔧 CONFIGURACIÓN POST-DEPLOYMENT

### 1. Verificar Deploy Exitoso

```bash
# Verificar health check
curl https://tu-proyecto.up.railway.app/

# Respuesta esperada:
{
  "status": "online",
  "service": "VTutor INEVAL RAG API",
  "documents": 0
}
```

### 2. Cargar Documentos INEVAL

**Problema:** Railway no tiene acceso directo a tus archivos locales.

**Soluciones:**

#### Opción A: Usar endpoint de upload

```bash
# Subir documento via API
curl -X POST https://tu-proyecto.up.railway.app/api/upload \
  -F "file=@Modelo_INEVAL_2024.pdf"

# Verificar documentos cargados
curl https://tu-proyecto.up.railway.app/api/documents
```

#### Opción B: Railway Volume (Persistencia)

1. **En Railway dashboard:**
   - Settings → Volumes
   - Add Volume
   - Mount Path: `/app/documentos_ineval`

2. **Subir documentos via Railway CLI:**
```bash
railway run bash
# Dentro del container:
cd /app/documentos_ineval
# Subir archivos via SFTP o similar
```

#### Opción C: Script de carga remota

Modificar `load_documents.py` para subir via HTTP:

```python
import requests
import os

API_URL = "https://tu-proyecto.up.railway.app"
DOCS_DIR = "./documentos_ineval"

for filename in os.listdir(DOCS_DIR):
    if filename.endswith(('.pdf', '.docx', '.txt')):
        filepath = os.path.join(DOCS_DIR, filename)
        with open(filepath, 'rb') as f:
            files = {'file': (filename, f)}
            response = requests.post(f"{API_URL}/api/upload", files=files)
            print(f"✅ {filename}: {response.json()}")
```

Ejecutar localmente:
```bash
python load_documents_remote.py
```

---

## 🔐 CONFIGURAR CORS PARA MOODLE

Editar `main.py` líneas 22-28:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tu-moodle.edu.ec",  # Tu dominio Moodle
        "https://vtutor-ineval-rag-production.up.railway.app"  # Railway
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Hacer commit y push:
```bash
git add main.py
git commit -m "Update CORS for Moodle domain"
git push
```

Railway re-deployará automáticamente.

---

## 📊 MONITOREO

### Logs en Tiempo Real

```bash
# Railway CLI
railway logs

# O en Railway dashboard:
# Deployment → Logs
```

### Verificar Uso de Recursos

Railway dashboard → Metrics:
- CPU usage
- Memory usage
- Network traffic

**Plan Free:**
- ✅ 500 horas/mes gratis
- ✅ 512 MB RAM
- ✅ 1 GB storage

**Para VTutor RAG necesitarás:**
- 💰 Plan Developer ($5/mes) - RAM 1-2 GB
- 💰 Plan Pro ($20/mes) - RAM 2-8 GB

---

## 🐛 TROUBLESHOOTING

### Error: "pydantic-core build failed"

**Solución:** Usar `requirements_railway.txt` actualizado
```bash
cp requirements_railway.txt requirements.txt
git add requirements.txt
git commit -m "Fix pydantic compatibility"
git push
```

### Error: "Out of memory"

**Causa:** Railway Free (512 MB) es insuficiente para ChromaDB + sentence-transformers

**Solución:**
1. Upgrade a Developer plan ($5/mes)
2. O reducir tamaño del modelo de embeddings:

```python
# En main.py, cambiar:
embedding_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')  # 80 MB
# En lugar de:
embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')  # 420 MB
```

### Error: "Disk full"

**Solución:** Agregar Railway Volume
- Settings → Volumes → Add Volume
- Mount Path: `/app/chroma_db`
- Size: 1 GB

### Error: "Port already in use"

**Verificar Procfile:**
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**NO usar:**
```
web: python main.py  ❌ (puerto hardcoded 8081)
```

### ChromaDB pierde datos después de redeploy

**Causa:** Sin persistencia

**Solución:** Railway Volume
1. Settings → Volumes
2. Mount Path: `/app/chroma_db`
3. Re-cargar documentos después del primer deploy

---

## 💰 COSTOS ESTIMADOS

### Railway Plans

| Plan | Precio | RAM | Storage | Horas |
|------|--------|-----|---------|-------|
| Free | $0 | 512 MB | 1 GB | 500h/mes |
| Developer | $5/mes | 2 GB | 10 GB | Ilimitado |
| Pro | $20/mes | 8 GB | 50 GB | Ilimitado |

**Recomendado para VTutor RAG:** Developer ($5/mes)

### DeepSeek API

- **Modelo:** deepseek-chat
- **Costo:** ~$0.14 por 1M tokens input, ~$0.28 por 1M tokens output
- **Estimado:** $1-5/mes para 1,000 consultas

**Total mensual estimado:** $6-10

---

## ✅ CHECKLIST DE DEPLOYMENT

- [ ] `requirements_railway.txt` reemplaza `requirements.txt`
- [ ] `Procfile` creado con comando correcto
- [ ] `.gitignore` creado (excluye `.env`, `chroma_db/`)
- [ ] Repositorio GitHub creado y pusheado
- [ ] Proyecto Railway conectado a GitHub
- [ ] Variable `DEEPSEEK_API_KEY` configurada
- [ ] Dominio público generado en Railway
- [ ] Health check verificado (`curl /`)
- [ ] Documentos INEVAL subidos via `/api/upload`
- [ ] CORS configurado con dominio Moodle
- [ ] URL actualizada en plugin Moodle settings
- [ ] Prueba de chat exitosa desde Moodle

---

## 🔗 ACTUALIZAR MOODLE PLUGIN

Después del deploy, actualizar URL en Moodle:

```
Moodle Admin → Plugins → Bloques → VTutor INEVAL
URL del Backend RAG: https://tu-proyecto.up.railway.app
Guardar cambios
Purgar cachés
```

---

## 📚 RECURSOS ADICIONALES

- **Railway Docs:** https://docs.railway.app
- **DeepSeek API:** https://platform.deepseek.com
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **ChromaDB Docs:** https://docs.trychroma.com

---

## 🎯 RESULTADO ESPERADO

Después del deployment exitoso:

```bash
# Health check
curl https://vtutor-ineval-rag.up.railway.app/
# {"status":"online","documents":15}

# Chat test
curl -X POST https://vtutor-ineval-rag.up.railway.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"¿Cuáles son las 4 dimensiones INEVAL?"}'
# {"answer":"Las 4 dimensiones son...","sources":[...]}
```

**URL para Moodle:** `https://vtutor-ineval-rag.up.railway.app`

---

**¡El backend RAG está listo en producción!** 🚀

---

**Actualizado:** 06 de Abril 2026  
**Versión:** 2.0.0 Railway Compatible
