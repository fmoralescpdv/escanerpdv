import PyInstaller.__main__
import customtkinter
import os
import sys

# Obtener la ruta de instalacion de customtkinter para incluir sus assets
ctk_path = os.path.dirname(customtkinter.__file__)
print(f"Ruta CustomTkinter detectada: {ctk_path}")

# Definir argumentos para PyInstaller
args = [
    'Aplicacion.py',                # Archivo principal
    '--name=EscanerPro',            # Nombre del ejecutable
    '--onefile',                    # Crear un solo archivo .exe (portátil)
    '--windowed',                   # No mostrar consola negra (GUI mode)
    '--clean',                      # Limpiar caché previo
    f'--add-data={ctk_path};customtkinter', # Incluir carpeta de estilos de CTK
    # Añade aquí otros archivos de datos si los necesitas, ej:
    # '--add-data=mi_icono.ico;.' 
]

print("Iniciando compilación... esto puede tardar unos minutos.")
try:
    PyInstaller.__main__.run(args)
    print("\n¡Compilación exitosa!")
    print(f"Tu ejecutable está en la carpeta: {os.path.abspath('dist')}")
except Exception as e:
    print(f"\nError durante la compilación: {e}")
