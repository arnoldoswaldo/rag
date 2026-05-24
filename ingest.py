import os
import tempfile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector

CONNECTION_STRING = "postgresql+psycopg://langchain:langchain@localhost:5432/rag_db"
COLLECTION_NAME = "rag_collection"


def _is_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _download_pdf(url: str, timeout: int = 30, retries: int = 3) -> str:
    """
    Descarga un PDF desde una URL a un archivo temporal.
    Retorna la ruta local del archivo descargado.
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("HEAD", "GET"),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    print(f"⬇️  Descargando PDF desde: {url}")
    resp = session.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_path = tmp.name
    tmp.close()

    with open(tmp_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    print(f"✅ PDF descargado temporalmente en: {tmp_path}")
    return tmp_path


def ingest_pdf(file_path_or_url: str):
    print(f"📦 Cargando documento desde: {file_path_or_url}...")

    tmp_path = None
    try:
        # Si es URL, descargamos primero para evitar fallos en PyPDFLoader.__init__
        if _is_url(file_path_or_url):
            tmp_path = _download_pdf(file_path_or_url)
            load_path = tmp_path
        else:
            if not os.path.exists(file_path_or_url):
                raise FileNotFoundError(f"Archivo no encontrado: {file_path_or_url}")
            load_path = file_path_or_url

        loader = PyPDFLoader(load_path)
        documents = loader.load()

    except requests.exceptions.ConnectionError as exc:
        print(f"\n❗ Error de conexión — verifica tu acceso a internet o la URL: {exc}")
        raise
    except requests.exceptions.Timeout as exc:
        print(f"\n❗ Tiempo de espera agotado al descargar el PDF: {exc}")
        raise
    except requests.exceptions.HTTPError as exc:
        print(f"\n❗ Error HTTP al descargar el PDF (¿URL correcta?): {exc}")
        raise
    except FileNotFoundError as exc:
        print(f"\n❗ {exc}")
        raise
    except Exception as exc:
        print(f"\n❗ Error inesperado al cargar el documento: {exc}")
        raise
    finally:
        # Limpiamos el archivo temporal siempre
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
            print(f"🗑️  Archivo temporal eliminado: {tmp_path}")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)
    print(f"✂️  Documento dividido en {len(docs)} fragmentos.")

    embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

    vectorstore = PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=CONNECTION_STRING,
        use_jsonb=True,
    )

    vectorstore.add_documents(docs)
    print("✅ Ingesta completada con éxito en PGVector.")


if __name__ == "__main__":
    url = "https://ingbiomedica.unal.edu.co/files/Normatividad/ACUERDO_008_2008_CSU_Estatuto_Estudiantil.pdf"
    ingest_pdf(url)