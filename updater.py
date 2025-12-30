import requests
import webbrowser
import os
import sys
from tkinter import messagebox
import subprocess

class AutoUpdater:
    def __init__(self, current_version, repo_owner, repo_name):
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    def check_for_updates(self, silent=False):
        """
        Consulta a GitHub si hay una versión nueva.
        Si silent=True, no muestra mensajes si NO hay updates (útil para chequeo al inicio).
        """
        try:
            print(f"Buscando actualizaciones en: {self.api_url}")
            response = requests.get(self.api_url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            latest_tag = data.get("tag_name", "").strip().lstrip("v") # Quitar 'v' si existe (v1.0 -> 1.0)
            
            # Comparación muy básica de strings (funciona para 1.0 vs 1.1)
            # Para algo robusto usar packaging.version
            if latest_tag > self.current_version:
                download_url = self._get_exe_url(data)
                if not download_url:
                    if not silent: messagebox.showwarning("Update", "Nueva versión detectada, pero no se encontró el instalador.")
                    return

                if messagebox.askyesno("Actualización Disponible", 
                                       f"Nueva versión {latest_tag} disponible.\n(Versión actual: {self.current_version})\n\n¿Desea descargarla e instalarla?"):
                    self.perform_update(download_url)
            else:
                if not silent:
                    messagebox.showinfo("Actualizado", "Ya tienes la última versión.")

        except Exception as e:
            print(f"Error comprobando actualizaciones: {e}")
            if not silent:
                messagebox.showerror("Error", f"Error comprobando actualizaciones:\n{e}")

    def _get_exe_url(self, release_data):
        """Busca el asset .exe en la release de GitHub"""
        assets = release_data.get("assets", [])
        for asset in assets:
            name = asset.get("name", "").lower()
            if name.endswith(".exe"):
                return asset.get("browser_download_url")
        return None

    def perform_update(self, url):
        """Descarga y ejecuta el instalador"""
        try:
            temp_path = os.path.join(os.environ.get('TEMP', '.'), "EscanerUpdate.exe")
            
            # Descargar
            response = requests.get(url, stream=True)
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Ejecutar instalador y cerrar esta app
            messagebox.showinfo("Instalando", "La aplicación se cerrará para iniciar la actualización.")
            subprocess.Popen([temp_path, "/SILENT"]) # /SILENT es usual para InnoSetup
            sys.exit(0)
            
        except Exception as e:
            messagebox.showerror("Error Actualización", f"Fallo en la descarga:\n{e}")
