import sys
import os
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

INPUT_EXAMPLE    = 'python main.py query "¿Cuál es el resumen del documento?"'
INPUT_URL_EXAMPLE = 'python main.py ingest "https://ejemplo.com/documento.pdf"'


def print_usage():
    print("\nModo de uso:")
    print("  Para ingestar : python main.py ingest <ruta_o_url_del_pdf>")
    print("  Para consultar: python main.py query \"¿Tu pregunta aquí?\" [--thread <id>]")
    print("\nEjemplos:")
    print(f"  {INPUT_EXAMPLE}")
    print(f"  {INPUT_URL_EXAMPLE}")


def is_valid_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def is_valid_path(value: str) -> bool:
    return os.path.exists(value) and os.path.isfile(value)


def _get_thread_id(args: list[str]) -> str:
    """Extrae --thread <id> de los args, devuelve '1' por defecto."""
    if "--thread" in args:
        idx = args.index("--thread")
        if idx + 1 < len(args):
            return args[idx + 1]
    return "1"


def main():
    if len(sys.argv) < 3:           
        print_usage()
        return

    
    _known_flags = {"-d", "--download-first", "-f", "--force", "--thread"}
    raw_args = sys.argv[1:]

    # quitar pares --thread <valor>
    filtered = []
    skip_next = False
    for tok in raw_args:
        if skip_next:
            skip_next = False
            continue
        if tok == "--thread":
            skip_next = True
            continue
        if tok not in _known_flags:
            filtered.append(tok)

    if len(filtered) < 2:
        print_usage()
        return

    action   = filtered[0].lower()
    argument = " ".join(filtered[1:]).strip()  # permite rutas con espacios

    # INGEST 
    if action == "ingest":
        from ingest import ingest_pdf

        if not argument:
            print("\n❗ Debes indicar una URL o ruta de archivo PDF.")
            print_usage()
            return

        if not is_valid_url(argument) and not is_valid_path(argument):
            print(f"\n❗ '{argument}' no es una URL válida ni un archivo existente.")
            print_usage()
            return

        origen = "URL" if is_valid_url(argument) else "archivo local"
        print(f"\n📦 Iniciando ingesta desde {origen}: {argument}")

        try:
            ingest_pdf(argument)          # ingest.py ya maneja descarga + limpieza
        except requests.exceptions.RequestException as exc:
            print(f"\n❗ Error de red: {exc}")
            print("Verifica la URL y tu conexión a internet.")
            sys.exit(1)
        except FileNotFoundError as exc:
            print(f"\n❗ Archivo no encontrado: {exc}")
            sys.exit(1)
        except Exception as exc:
            print(f"\n❗ Error al ingestar el documento: {exc}")
            sys.exit(1)

    #  QUERY
    elif action == "query":
       
        try:
            from graph import rag_app
        except Exception as exc:
            print(f"\n❗ No se pudo cargar el módulo 'graph': {exc}")
            print("Asegúrate de que graph.py existe y está correctamente configurado.")
            sys.exit(1)

        if not argument:
            print("\n❗ La consulta está vacía. Escribe una pregunta válida.")
            print_usage()
            return

        thread_id = _get_thread_id(sys.argv[1:])
        print(f"\n🚀 Procesando consulta (thread={thread_id}): '{argument}'")

        try:
            config = {"configurable": {"thread_id": thread_id}}
            output = rag_app.invoke({"question": argument}, config=config)
            print("\n✨ --- Respuesta Final --- ✨")
            print(output.get("response", "(sin respuesta)"))
            print("---------------------------\n")
        except Exception as exc:
            print(f"\n❗ Error al procesar la consulta: {exc}")
            sys.exit(1)

    else:
        print(f"\n❗ Acción desconocida: '{action}'. Usa 'ingest' o 'query'.")
        print_usage()


if __name__ == "__main__":
    main()
