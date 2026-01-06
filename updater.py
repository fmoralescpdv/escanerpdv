import requests
import webbrowser
import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
import re

class AutoUpdater:
    def __init__(self, current_version, repo_owner, repo_name):
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_url = f"https://api.github.com/repos/fmoralescpdv/escanerpdv/releases/latest"

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
            tag_name = data.get("tag_name", "").strip()
            release_name = data.get("name", "").strip()

            # Lógica Simplificada:
            # Confiamos en que el tag de GitHub es una versión válida (ej: "v1.3" o "1.3")
            # El endpoint /releases/latest ya nos trae la última release válida.
            
            remote_ver = tag_name.lower().lstrip("v")
            
            # Comparación robusta (1.2.0 vs 1.2)
            if self._is_newer(remote_ver, self.current_version):
                download_url = self._get_exe_url(data)
                if not download_url:
                    if not silent: messagebox.showwarning("Update", "Nueva versión detectada, pero no se encontró el instalador.")
                    return

                if messagebox.askyesno("Actualización Disponible", 
                                       f"Nueva versión {remote_ver} disponible.\n(Versión actual: {self.current_version})\n\n¿Desea descargarla e instalarla?"):
                    self.perform_update(download_url)
            else:
                if not silent:
                    messagebox.showinfo("Actualizado", "Ya tienes la última versión.")

        except Exception as e:
            print(f"Error comprobando actualizaciones: {e}")
            if not silent:
                messagebox.showerror("Error", f"Error comprobando actualizaciones:\n{e}")

    def _is_newer(self, remote, local):
        """Compara versiones numéricas tipo 1.2.3 de forma robusta."""
        try:
            # Intentar convertir a listas de enteros: "1.10" -> [1, 10]
            r_parts = [int(x) for x in remote.split('.')]
            l_parts = [int(x) for x in local.split('.')]
            
            # Igualar longitud con ceros (ej: 1.1 vs 1.1.0)
            max_len = max(len(r_parts), len(l_parts))
            while len(r_parts) < max_len: r_parts.append(0)
            while len(l_parts) < max_len: l_parts.append(0)

            return r_parts > l_parts
        except ValueError:
            # Fallback a string clásico si hay texto (ej: "beta1") o errores
            return remote > local

    def _get_exe_url(self, release_data):
        """Busca el asset .exe en la release de GitHub"""
        assets = release_data.get("assets", [])
        for asset in assets:
            name = asset.get("name", "").lower()
            if name.endswith(".exe"):
                return asset.get("browser_download_url")
        return None

    def perform_update(self, url):
        """Descarga con Barra de Progreso y ejecuta el instalador"""
        try:
            # Crear ventana de progreso
            p_win = tk.Toplevel()
            p_win.title("Actualizando Escaner PDV")
            p_win.geometry("350x150")
            p_win.resizable(False, False)
            
            # Centrar ventana
            p_win.update_idletasks()
            w = p_win.winfo_width()
            h = p_win.winfo_height()
            x = (p_win.winfo_screenwidth() // 2) - (w // 2)
            y = (p_win.winfo_screenheight() // 2) - (h // 2)
            p_win.geometry(f'+{x}+{y}')
            
            lbl = tk.Label(p_win, text="Iniciando descarga...", font=("Arial", 10))
            lbl.pack(pady=20)
            
            pbar = ttk.Progressbar(p_win, orient="horizontal", length=300, mode="determinate")
            pbar.pack(pady=5)
            
            p_win.update()
            
            temp_path = os.path.join(os.environ.get('TEMP', '.'), "EscanerPDVUpdate.exe")
            
            # Descargar con stream
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            if total_size == 0:
                pbar.mode = 'indeterminate'
                pbar.start()
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            perc = (downloaded / total_size) * 100
                            pbar['value'] = perc
                            lbl.config(text=f"Descargando: {int(perc)}%")
                        else:
                            lbl.config(text=f"Descargado: {downloaded/1024:.1f} KB")
                        
                        p_win.update()
            
            p_win.destroy()
            
            # Ejecutar instalador y cerrar esta app
            messagebox.showinfo("Instalando", "La aplicación se cerrará para iniciar la actualización.")
            
            # [FIX] Usar os.startfile para que Windows maneje la ejecución 
            # Esto evita que el instalador herede el entorno de PyInstaller (DLL Hell)
            try:
                os.startfile(temp_path)
            except AttributeError:
                subprocess.Popen([temp_path], shell=True)
                
            os._exit(0)
            
        except Exception as e:
            try: p_win.destroy() 
            except: pass
            messagebox.showerror("Error Actualización", f"Fallo en la descarga:\n{e}")
