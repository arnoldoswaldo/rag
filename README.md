# 📚 RAG System con LangChain, LangGraph y PGVector

Sistema de **Retrieval-Augmented Generation (RAG)** que permite ingestar documentos PDF y responder preguntas sobre su contenido usando embeddings vectoriales y un LLM.

---

## 🏗️ Arquitectura

```
Usuario
  │
  ▼
main.py  ──── ingest ──→  ingest.py
                              │
                    Descarga PDF (requests)
                              │
                    Divide en fragmentos (LangChain)
                              │
                    Genera embeddings (Gemini / OpenAI)
                              │
                    Almacena en PGVector (PostgreSQL)
  │
  └─── query ──→  graph.py (LangGraph)
                      │
               [Nodo: Recuperación]
               Busca fragmentos relevantes en PGVector
                      │
               [Nodo: Generación]
               Genera respuesta con LLM (Gemini / OpenAI)
                      │
                  Respuesta final
```

---

## 🧰 Tecnologías

| Componente | Tecnología |
|---|---|
| Orquestación RAG | LangChain + LangGraph |
| Base de datos vectorial | PGVector (PostgreSQL) |
| Contenedor DB | Docker |
| Embeddings | Gemini `gemini-embedding-001` / OpenAI `text-embedding-3-small` |
| LLM | Gemini `gemini-2.5-flash` / OpenAI `gpt-4o-mini` |
| Carga de PDFs | PyPDFLoader (langchain-community) |

---

## ✅ Prerrequisitos

- Python 3.10 o superior
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo
- API Key de [Google AI Studio](https://aistudio.google.com/apikey) **o** [OpenAI](https://platform.openai.com/api-keys)
- Conexión a internet (necesaria para llamar a la API del LLM)
- Red **sin bloqueo** a `generativelanguage.googleapis.com` (redes universitarias o corporativas pueden bloquearlo — usa hotspot móvil si es necesario)

---

## ⚙️ Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/proyecto_rag.git
cd proyecto_rag
```

### 2. Crear y activar el entorno virtual

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
GOOGLE_API_KEY=tu_api_key_de_google
# o si usas OpenAI:
# OPENAI_API_KEY=tu_api_key_de_openai
```

### 5. Levantar la base de datos con Docker

```bash
docker compose up -d
```

Verifica que el contenedor esté corriendo:

```bash
docker compose ps
```

Deberías ver `pgvector-db` con estado `healthy`.

---

## 📁 Estructura del proyecto

```
proyecto_rag/
├── init/
│   └── 01_init_pgvector.sql   # Habilita la extensión vector en PostgreSQL
├── .venv/                     # Entorno virtual 
├── .env                       # Variables de entorno 
├── .gitignore
├── docker-compose.yml
├── ingest.py                  # Carga, divide y almacena el PDF en PGVector
├── graph.py                   # Grafo LangGraph: nodos de recuperación y generación
├── main.py                    # Punto de entrada CLI
├── requirements.txt
└── README.md
```

---

## 🚀 Uso

### Ingestar un documento PDF: Desde terminal o consola ejecutar los siguientes comandos 

**Desde una URL:**
```bash
python main.py ingest "https://ejemplo.com/documento.pdf"
```

**Desde un archivo local:**
```bash
python main.py ingest "ruta/al/documento.pdf"
```

**Salida esperada:**
```
📦 Iniciando ingesta desde URL: https://ejemplo.com/documento.pdf
⬇️  Descargando PDF desde: https://ejemplo.com/documento.pdf
✅ PDF descargado temporalmente en: /tmp/tmpk3m8zx8.pdf
✂️  Documento dividido en 45 fragmentos.
✅ Ingesta completada con éxito en PGVector.
🗑️  Archivo temporal eliminado.
```

---

### Consultar el documento

```bash
python main.py query "¿De qué trata el documento?"
```

Con thread específico (sesiones independientes):
```bash
python main.py query "¿Cuáles son los requisitos mencionados?" --thread sesion_1
```

**Salida esperada:**
```
🚀 Procesando consulta (thread=1): '¿De qué trata el documento?'
🔍 [Nodo: Recuperación] Buscando contexto en PGVector...
   → 3 fragmento(s) recuperado(s).
🤖 [Nodo: Generación] Produciendo respuesta con Gemini...

✨ --- Respuesta Final --- ✨
El documento trata sobre [...] según el contexto recuperado.
---------------------------
```

---

## 📋 Ejemplo completo

```bash
# 1. Levantar base de datos
docker compose up -d

# 2. Ingestar documento
python main.py ingest "https://ejemplo.com/reglamento.pdf"

# 3. Hacer consultas
python main.py query "¿Cuál es el objetivo principal del documento?"
python main.py query "¿Qué requisitos se mencionan?"
python main.py query "¿Qué sanciones existen?"
```

---

## 🔧 Solución de problemas

| Error | Causa | Solución |
|---|---|---|
| `getaddrinfo failed` al descargar PDF | DNS no resuelve el dominio | Verifica tu conexión a internet |
| `getaddrinfo failed` en embeddings | Red bloqueando Google/OpenAI APIs | Cambia de red o usa VPN / hotspot |
| `type "vector" does not exist` | Extensión pgvector no inicializada | Ejecuta `docker compose down -v && docker compose up -d` |
| `GOOGLE_API_KEY not found` | Falta el archivo `.env` | Crea `.env` con tu API key en la raíz del proyecto |
| `connection refused` en PostgreSQL | Docker no está corriendo | Ejecuta `docker compose up -d` |
| `429 RESOURCE_EXHAUSTED` / cuota 0 | El modelo no tiene cuota asignada en el proyecto | Verifica en [AI Studio](https://aistudio.google.com/rate-limit) qué modelos tienen cuota y úsalos |

---

## 🐳 Comandos Docker útiles

```bash
# Levantar contenedor
docker compose up -d

# Ver logs de la base de datos
docker compose logs -f db

# Verificar extensión pgvector activa
docker exec -it pgvector-db psql -U langchain -d rag_db -c "\dx"

# Detener sin borrar datos
docker compose down

# Reset completo (borra todos los documentos ingestados)
docker compose down -v
```

---

## ⚠️ Límites del tier gratuito de Gemini

| Modelo | RPM | RPD | Nota |
|---|---|---|---|
| `gemini-2.5-flash` | 5 | 20 | ✅ Recomendado para este proyecto |
| `gemini-embedding-001` | 5 | 100 | Usado para embeddings |

> La cuota disponible varía por proyecto. Verifica la tuya en [AI Studio Rate Limits](https://aistudio.google.com/rate-limit).  
> Si un modelo muestra `0/0` de cuota, **no está disponible** en tu proyecto aunque exista en la plataforma.

---

## 📄 Licencia

MIT
