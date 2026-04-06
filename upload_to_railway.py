"""
Script para cargar documentos INEVAL al backend RAG desplegado en Railway

Uso:
    1. Configurar API_URL con tu URL de Railway
    2. Colocar documentos en ./documentos_ineval/
    3. Ejecutar: python upload_to_railway.py
"""

import os
import requests
import sys
from pathlib import Path

# ⚠️ CONFIGURAR ESTA URL CON TU DEPLOYMENT DE RAILWAY
API_URL = "https://tu-proyecto.up.railway.app"  # CAMBIAR AQUÍ

DOCUMENTS_DIR = "./documentos_ineval"

def check_api_status():
    """Verifica que el API esté corriendo"""
    try:
        response = requests.get(f"{API_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API conectada - Status: {data['status']}")
            print(f"📚 Documentos actuales en servidor: {data['documents']}")
            return True
        else:
            print(f"❌ Error: API respondió con status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: No se puede conectar a {API_URL}")
        print("   Verifica que:")
        print("   1. El backend esté desplegado en Railway")
        print("   2. La URL sea correcta")
        print("   3. El servicio esté corriendo")
        return False

def upload_document(file_path):
    """Sube un documento al API"""
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path) / 1024  # KB
    
    print(f"\n📤 Subiendo: {filename} ({file_size:.1f} KB)...", end=" ")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f)}
            response = requests.post(f"{API_URL}/api/upload", files=files, timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            chunks = data.get('chunks_created', 0)
            print(f"✅ OK - {chunks} chunks creados")
            return True
        else:
            error = response.json().get('detail', 'Unknown error')
            print(f"❌ Error: {error}")
            return False
    except requests.exceptions.Timeout:
        print(f"❌ Timeout - El archivo es muy grande o el servidor está lento")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def list_remote_documents():
    """Lista documentos en el servidor"""
    try:
        response = requests.get(f"{API_URL}/api/documents")
        if response.status_code == 200:
            docs = response.json()
            if docs:
                print("\n📚 Documentos en el servidor:")
                print("-" * 70)
                for doc in docs:
                    print(f"  • {doc['filename']}")
                    print(f"    Chunks: {doc['chunks']} | Subido: {doc['uploaded_at'][:19]}")
                print("-" * 70)
            else:
                print("\n📚 No hay documentos en el servidor aún")
            return docs
        return []
    except Exception as e:
        print(f"❌ Error listando documentos: {e}")
        return []

def main():
    print("\n" + "="*70)
    print("🚂 VTutor INEVAL - Cargador de Documentos a Railway")
    print("="*70 + "\n")
    
    # Verificar URL configurada
    if API_URL == "https://tu-proyecto.up.railway.app":
        print("❌ Error: Debes configurar API_URL en el script")
        print("   Edita upload_to_railway.py línea 12:")
        print('   API_URL = "https://tu-proyecto-real.up.railway.app"')
        sys.exit(1)
    
    print(f"🌐 API URL: {API_URL}")
    
    # 1. Verificar que el API esté corriendo
    if not check_api_status():
        sys.exit(1)
    
    # 2. Verificar directorio de documentos
    if not os.path.exists(DOCUMENTS_DIR):
        print(f"\n❌ Error: Directorio '{DOCUMENTS_DIR}' no existe")
        print(f"   Créalo y coloca tus documentos INEVAL allí")
        sys.exit(1)
    
    # 3. Buscar documentos
    files = []
    for ext in ['.pdf', '.docx', '.txt']:
        files.extend(Path(DOCUMENTS_DIR).glob(f'*{ext}'))
    
    if not files:
        print(f"\n❌ No se encontraron documentos en '{DOCUMENTS_DIR}'")
        print(f"   Formatos soportados: PDF, DOCX, TXT")
        sys.exit(1)
    
    print(f"\n📁 Documentos encontrados: {len(files)}")
    for f in files:
        size = f.stat().st_size / 1024
        print(f"   • {f.name} ({size:.1f} KB)")
    
    # 4. Preguntar confirmación
    print()
    response = input("¿Deseas subir estos documentos a Railway? (s/n): ")
    if response.lower() != 's':
        print("❌ Operación cancelada")
        sys.exit(0)
    
    # 5. Subir documentos
    print("\n" + "="*70)
    print("📤 SUBIENDO DOCUMENTOS")
    print("="*70)
    
    success = 0
    failed = 0
    
    for file_path in files:
        if upload_document(file_path):
            success += 1
        else:
            failed += 1
    
    # 6. Resumen
    print("\n" + "="*70)
    print("📊 RESUMEN")
    print("="*70)
    print(f"✅ Documentos subidos exitosamente: {success}")
    if failed > 0:
        print(f"❌ Documentos fallidos: {failed}")
    
    # 7. Listar documentos finales en servidor
    list_remote_documents()
    
    # 8. Test de consulta
    if success > 0:
        print("\n" + "="*70)
        print("🧪 TEST DE CONSULTA")
        print("="*70)
        
        try:
            test_question = "¿Cuáles son las 4 dimensiones del modelo INEVAL?"
            print(f"\nPregunta: {test_question}")
            
            response = requests.post(
                f"{API_URL}/api/chat",
                json={"question": test_question},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Respuesta recibida:")
                print(f"   {data['answer'][:200]}...")
                if data.get('sources'):
                    print(f"\n📚 Fuentes: {', '.join(data['sources'])}")
            else:
                print(f"❌ Error en consulta: {response.status_code}")
        except Exception as e:
            print(f"❌ Error en test: {e}")
    
    print("\n" + "="*70)
    print("✅ ¡Proceso completado!")
    print("="*70)
    print(f"\n🌐 Tu backend RAG está en: {API_URL}")
    print(f"📱 Configura esta URL en Moodle:")
    print(f"   Admin → Plugins → Bloques → VTutor INEVAL")
    print(f"   URL del Backend RAG: {API_URL}")
    print()

if __name__ == "__main__":
    main()
