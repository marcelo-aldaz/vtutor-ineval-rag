"""
Script para cargar documentos INEVAL iniciales al sistema RAG

Uso:
    python load_documents.py

Coloca tus documentos INEVAL en ./documentos_ineval/ antes de ejecutar
"""

import os
import sys
import requests
from pathlib import Path
import time

# Configuración
API_URL = "http://localhost:8081"
DOCUMENTS_DIR = "./documentos_ineval"

def check_api_status():
    """Verifica que el API esté corriendo"""
    try:
        response = requests.get(f"{API_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API conectada - Documentos actuales: {data['documents']}")
            return True
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Error: El API no está corriendo")
        print("   Ejecuta primero: python main.py")
        return False

def upload_document(file_path):
    """Sube un documento al API"""
    filename = os.path.basename(file_path)
    print(f"📤 Subiendo: {filename}...", end=" ")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f)}
            response = requests.post(f"{API_URL}/api/upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {data['chunks_created']} chunks creados")
            return True
        else:
            print(f"❌ Error: {response.json().get('detail', 'Unknown')}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def list_documents():
    """Lista documentos en el sistema"""
    try:
        response = requests.get(f"{API_URL}/api/documents")
        if response.status_code == 200:
            docs = response.json()
            if docs:
                print("\n📚 Documentos en el sistema:")
                print("-" * 70)
                for doc in docs:
                    print(f"  • {doc['filename']}")
                    print(f"    Chunks: {doc['chunks']} | Subido: {doc['uploaded_at'][:19]}")
                print("-" * 70)
            else:
                print("\n📚 No hay documentos en el sistema aún")
            return docs
        return []
    except Exception as e:
        print(f"❌ Error listando documentos: {e}")
        return []

def main():
    print("\n" + "="*70)
    print("🚀 VTutor INEVAL - Cargador de Documentos RAG")
    print("="*70 + "\n")
    
    # 1. Verificar que el API esté corriendo
    if not check_api_status():
        sys.exit(1)
    
    # 2. Verificar directorio de documentos
    if not os.path.exists(DOCUMENTS_DIR):
        print(f"❌ Error: Directorio '{DOCUMENTS_DIR}' no existe")
        print(f"   Créalo y coloca tus documentos INEVAL allí")
        sys.exit(1)
    
    # 3. Buscar documentos
    files = []
    for ext in ['.pdf', '.docx', '.txt']:
        files.extend(Path(DOCUMENTS_DIR).glob(f'*{ext}'))
    
    if not files:
        print(f"❌ No se encontraron documentos en '{DOCUMENTS_DIR}'")
        print(f"   Formatos soportados: PDF, DOCX, TXT")
        sys.exit(1)
    
    print(f"📁 Documentos encontrados: {len(files)}\n")
    
    # 4. Preguntar confirmación
    response = input("¿Deseas cargar estos documentos? (s/n): ")
    if response.lower() != 's':
        print("❌ Operación cancelada")
        sys.exit(0)
    
    print()
    
    # 5. Subir documentos
    success = 0
    failed = 0
    
    for file_path in files:
        if upload_document(file_path):
            success += 1
        else:
            failed += 1
        time.sleep(0.5)  # Pequeña pausa entre uploads
    
    # 6. Resumen
    print("\n" + "="*70)
    print("📊 RESUMEN")
    print("="*70)
    print(f"✅ Documentos cargados: {success}")
    if failed > 0:
        print(f"❌ Documentos fallidos: {failed}")
    
    # 7. Listar documentos finales
    list_documents()
    
    print("\n✅ ¡Listo! Los docentes ahora pueden hacer preguntas sobre estos documentos")
    print()

if __name__ == "__main__":
    main()
