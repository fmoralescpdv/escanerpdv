import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import cv2
import threading
import time
import os
import traceback
from scanner_logic import ScannerLogic
from session_manager import SessionManager
from ui_panels import TopBar, SideBar, AnswerPanel, ImagePanel
from names_service import NamesService

class ScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Corrección Automática - Escáner TWAIN")
        self.root.geometry("1100x750")
        
        ctk.set_appearance_mode("Light") 
        ctk.set_default_color_theme("blue")

        self.logic = ScannerLogic()
        self.session = SessionManager()
        self.names_service = NamesService()
        
        self.current_scan_index = -1
        
        self._setup_ui()

    def _setup_ui(self):
        # Frame Principal CTK
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 1. Top Bar
        top_callbacks = {
            'select_source': self.seleccionar_fuente,
            'save': self.guardar_sesion,
            'load': self.cargar_sesion,
            'review': self.generar_reporte_txt,
            'reload_names': self.recargar_nombres,
            'toggle_view': self.toggle_viewer
        }
        self.top_bar = TopBar(main_frame, top_callbacks)

        # 2. Side Bar
        side_callbacks = {
            'scan': self.iniciar_escaneo,
            'quick_scan': self.iniciar_escaneo_rapido,
            'on_select': self._on_scan_selected,
            'delete': self.eliminar_prueba
        }
        self.side_bar = SideBar(main_frame, side_callbacks)

        # 3. Center Panel (Answers & RUT)
        center_panel_frame = ctk.CTkFrame(main_frame, width=350, fg_color="transparent")
        center_panel_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10), expand=True)
        
        ans_callbacks = {
            'on_rut_change': self._on_rut_key_release,
            'on_answer_change': self._on_answer_key_release,
            'on_name_change': self._on_name_key_release
        }
        self.answer_panel = AnswerPanel(center_panel_frame, ans_callbacks)

        # 4. Right Panel (Image)
        self.image_panel = ImagePanel(main_frame)

    def _on_rut_key_release(self, event):
        text = self.answer_panel.get_rut()
        if not text: return

        # Limitar longitud bruta para evitar desbordes (max 9 digitos + K)
        raw = ''.join(filter(lambda x: x.isdigit() or x.lower() == 'k', text))
        if len(raw) > 9:
            text = raw[:9]
            formatted = self._format_rut(text)
            self.answer_panel.set_rut(formatted)
            self.answer_panel.update_rut_cursor()
            self._save_current_rut_state(formatted)
            return

        if event.keysym in ('BackSpace', 'Delete'): 
            self._save_current_rut_state(text)
            return

        formatted = self._format_rut(text)
        if text != formatted:
            self.answer_panel.set_rut(formatted)
            self.answer_panel.update_rut_cursor()
        
        self._save_current_rut_state(formatted)

    def _on_name_key_release(self, event):
        val = self.answer_panel.get_name()
        if self.current_scan_index >= 0:
            self.session.update_name(self.current_scan_index, val)

    def _save_current_rut_state(self, val):
        if self.current_scan_index >= 0:
            self.session.update_rut(self.current_scan_index, val)
    
    def _on_answer_key_release(self, event, index):
        widget = event.widget
        val = widget.get().upper()
        
        # Validar entrada: solo A,B,C,D,E (max 1 char)
        clean_val = ""
        if val:
            # Tomar ultimo caracter
            char = val[-1]
            if char in ['A','B','C','D','E']:
                clean_val = char
        
        if widget.get() != clean_val:
            widget.delete(0, tk.END)
            widget.insert(0, clean_val)
            val = clean_val
            
        self.session.update_answer(self.current_scan_index, index, val)

    def _format_rut(self, text):
        raw = ''.join(filter(lambda x: x.isdigit() or x.lower() == 'k', text))
        if not raw: return ""
        if len(raw) <= 1: return raw
        dv = raw[-1]
        body = raw[:-1]
        parts = [body[max(i-3, 0):i] for i in range(len(body), 0, -3)]
        formatted_body = ".".join(parts[::-1])
        return f"{formatted_body}-{dv}"

    def seleccionar_fuente(self):
        try:
            sources = self.logic.get_sources(0)
            if not sources:
                messagebox.showerror("Error", "No se detectaron dispositivos TWAIN.")
                return
            
            if len(sources) == 1:
                self.logic.set_source(sources[0])
                messagebox.showinfo("Scanner", f"Scanner seleccionado automaticamente:\n{sources[0]}")
                return

            self._show_source_selector(sources)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _show_source_selector(self, sources):
        top = tk.Toplevel(self.root)
        top.title("Seleccionar Scanner")
        top.geometry("300x250")
        top.transient(self.root)
        top.grab_set()
        
        lbl = ttk.Label(top, text="Dispositivos disponibles:")
        lbl.pack(pady=5)
        
        lb = tk.Listbox(top)
        lb.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for s in sources:
            lb.insert(tk.END, s)
            
        def on_select():
            sel = lb.curselection()
            if sel:
                name = lb.get(sel[0])
                self.logic.set_source(name)
                messagebox.showinfo("Scanner", f"Seleccionado:\n{name}")
                top.destroy()
        
        btn = ttk.Button(top, text="Seleccionar", command=on_select)
        btn.pack(pady=10)
        
        self.root.wait_window(top)

    def iniciar_escaneo_rapido(self):
        self.iniciar_escaneo(show_ui=False)

    def iniciar_escaneo(self, show_ui=True):
        # Si ya estamos escaneando, el botón actúa como cancelar
        if getattr(self, 'is_scanning', False):
            self.detener_escaneo()
            return

        # Auto-seleccionar si solo hay un escaner y no se ha seleccionado ninguno
        if self.logic.current_source_name is None:
            try:
                sources = self.logic.get_sources(0)
                if sources and len(sources) == 1:
                    self.logic.set_source(sources[0])
            except:
                pass

        timestamp = int(time.time())
        self.base_scan_filename = f"scan_{timestamp}"
        
        try:
            # Iniciamos escaneo (Modeless, Main Thread)
            self.scan_source = self.logic.start_scanning(self.root.winfo_id(), show_ui=show_ui)
            
            if not self.scan_source:
                return # Cancelado o falló apertura
            
            self.scan_index = 0
            self.is_scanning = True
            
            # Cambiar texto del botón para indicar que se puede detener
            self.side_bar.btn_scan.configure(text="Detener Escaneo")
            
            # Iniciamos Loop de Polling con retraso inicial
            self.root.after(1000, self._poll_scan_status)
            
        except Exception as e:
            messagebox.showerror("Error de Escaneo", str(e))

    def detener_escaneo(self):
        self._finish_scanning()

    def _poll_scan_status(self):
        if not getattr(self, 'is_scanning', False):
            return

        try:
            # Intentamos transferir. Ahora transfer_next suprime errores de "No Listo" indefinidamente.
            filepath, pending = self.logic.transfer_next(self.scan_source, self.base_scan_filename, self.scan_index)
            
            if filepath:
                # Imagen recibida
                self._process_new_scan(filepath)
                self.scan_index += 1
            
            # Si pending == 0, el driver indica que terminó el lote
            if pending == 0:
                self._finish_scanning()
                return

            # Programar siguiente chequeo
            self.root.after(200, self._poll_scan_status)

        except Exception as e:
            # Error fatal real
            print(f"Error fatal en polling: {e}")
            traceback.print_exc()
            self._finish_scanning()
            messagebox.showerror("Error Escáner", f"Se detuvo el escaneo:\n{e}")

    def _finish_scanning(self):
        self.is_scanning = False
        if getattr(self, 'scan_source', None):
            self.logic.close_source(self.scan_source)
            self.scan_source = None
        
        # Restaurar texto del botón
        try:
            self.side_bar.btn_scan.configure(text="Escanear (Multiple/ADF)")
        except:
            pass
            
        # Recuperar foco para evitar bloqueo de UI post-escaneo
        # Hack: Minimizar y restaurar fuerza al OS a devolver control de input
        self.root.iconify()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _process_new_scan(self, image_path):
        rut_text, answer_values, vis_img = self.logic.process_image(image_path)
        
        # ELIMINAR PROVISIONALMENTE EL ARCHIVO DE IMAGEN
        # El usuario solicitó no acumular imágenes en disco.
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"Advertencia: No se pudo eliminar imagen temporal {image_path}: {e}")

        if vis_img is None:
            messagebox.showerror("Error", "No se pudo procesar la imagen.")
            return

        # OPTIMIZACION: Reducir tamaño en memoria para visualización rápida
        try:
            h, w = vis_img.shape[:2]
            if h > 1000: 
                scale = 1000 / h
                new_w = int(w * scale)
                vis_img = cv2.resize(vis_img, (new_w, 1000), interpolation=cv2.INTER_AREA)
        except Exception as e:
            print(f"Error optimizando imagen: {e}")

        initial_rut = ""
        student_name = ""
        if rut_text:
             initial_rut = self._format_rut(rut_text)
             raw_rut = ''.join(filter(lambda x: x.isdigit() or x.lower() == 'k', rut_text)).upper()
             student_name = self.names_service.get_name(raw_rut)
        
        # Rellenar lista de 90 respuestas
        full_answers = [""] * 90
        for i, val in enumerate(answer_values):
            if i < 90:
                full_answers[i] = val
        
        scan_data = {
            'path': image_path,
            'rut_marks': [], 
            'ans_marks': [], 
            'vis_img': vis_img,
            'rut_text': initial_rut,
            'student_name': student_name,
            'answers_values': full_answers 
        }
        
        self.session.add_scan(scan_data)
        
        idx = len(self.session.get_scans())
        # Mostrar RUT si se detectó, sino Hoja X
        display_text = initial_rut if initial_rut else f"Hoja {idx}"
        self.side_bar.add_item(display_text)
        self.side_bar.select_last()
        self._load_scan_into_view(idx - 1)
        self._update_sidebar_stats()

    def eliminar_prueba(self):
        index = self.side_bar.get_selection_index()
        if index is None:
            messagebox.showwarning("Advertencia", "Seleccione una prueba para eliminar.")
            return
            
        if messagebox.askyesno("Confirmar", "¿Está seguro de eliminar esta prueba?"):
            if self.session.remove_scan(index):
                # Actualizar UI
                self.side_bar.delete_item(index)
                self._update_sidebar_stats()
                
                # Si borramos el actual, limpiar o mover seleccion
                if index == self.current_scan_index:
                    self.current_scan_index = -1
                    self.answer_panel.clear_answers()
                    self.answer_panel.set_rut("")
                    self.answer_panel.set_name("")
                    # self.image_panel.display_image(None) 
                    
                    # Intentar seleccionar otro
                    count = self.side_bar.lst_scans.size()
                    if count > 0:
                        new_idx = max(0, index - 1)
                        self.side_bar.select_index(new_idx)
                        self._load_scan_into_view(new_idx)
                elif index < self.current_scan_index:
                    self.current_scan_index -= 1 

    def _on_scan_selected(self, event):
        index = self.side_bar.get_selection_index()
        if index is not None:
            self._load_scan_into_view(index)

    def _load_scan_into_view(self, index):
        scan_data = self.session.get_scan(index)
        if not scan_data: return
            
        self.current_scan_index = index
        
        self.answer_panel.set_rut(scan_data.get('rut_text', ""))
        self.answer_panel.set_name(scan_data.get('student_name', ""))
        
        vals = scan_data.get('answers_values', [""] * 90)
        self.answer_panel.clear_answers()
        
        for i in range(90):
             val = vals[i]
             self.answer_panel.set_answer(i, val, mark_detected=False)

        for i, ans in enumerate(scan_data['ans_marks']):
             if i < 90:
                 self.answer_panel.highlight_mark(i)

        vis_img = scan_data['vis_img'].copy()
        
        for i, ans in enumerate(scan_data['ans_marks']):
             if i < 90:
                 cx, cy = ans['pos']
                 cv2.putText(vis_img, str(i+1), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        self.image_panel.display_image(vis_img)

    def guardar_sesion(self):
        if not self.session.get_scans():
            messagebox.showwarning("Advertencia", "No hay escaneos para guardar.")
            return

        filename = filedialog.asksaveasfilename(
            title="Guardar Sesión", defaultextension=".escaner",
            filetypes=[("Archivos de Escaner", "*.escaner")]
        )
        if filename:
            try:
                self.session.save_session(filename)
                messagebox.showinfo("Éxito", f"Sesión guardada en {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar: {e}")

    def cargar_sesion(self):
        if self.session.get_scans():
             if not messagebox.askyesno("Confirmar", "Se borrará la sesión actual. ¿Continuar?"): return

        filename = filedialog.askopenfilename(
            title="Cargar Sesión", defaultextension=".escaner",
            filetypes=[("Archivos de Escaner", "*.escaner")]
        )
        if filename:
            try:
                scans, missing = self.session.load_session(filename)
                if missing:
                    messagebox.showwarning("Faltantes", "Faltan imagenes: " + str(missing[:2]))
                
                self.side_bar.clear()
                for i, scan in enumerate(scans):
                    rut = scan.get('rut_text', "")
                    display_text = rut if rut else f"Hoja {i+1}"
                    self.side_bar.add_item(display_text)
                
                if scans:
                    self.side_bar.select_index(0)
                    self._load_scan_into_view(0)
                else:
                    self.current_scan_index = -1
                
                self._update_sidebar_stats()
                messagebox.showinfo("Éxito", f"Cargadas {len(scans)} hojas.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def generar_reporte_txt(self):
        if not self.session.get_scans():
            messagebox.showwarning("Advertencia", "No hay pruebas para revisar.")
            return

        # Ruta fija solicitada: C:\psicofas\pruebas\RESULTS\resp.txt
        output_dir = r"C:\psicofas\pruebas\RESULTS"
        filename = os.path.join(output_dir, "resp.txt")
        
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            self.session.generate_report(filename)
            messagebox.showinfo("Reporte Generado", f"Archivo creado correctamente:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el reporte:\n{e}")

    def recargar_nombres(self):
        self.names_service.reload()
        
        count = 0
        current_scans = self.session.get_scans()
        for i, scan in enumerate(current_scans):
            rut = scan.get('rut_text', "")
            if rut:
                 raw_rut = ''.join(filter(lambda x: x.isdigit() or x.lower() == 'k', rut)).upper()
                 name = self.names_service.get_name(raw_rut)
                 if name:
                     self.session.update_name(i, name)
                     count += 1
        
        if self.current_scan_index >= 0:
            self._load_scan_into_view(self.current_scan_index)
            
        self._update_sidebar_stats()
        messagebox.showinfo("Nombres", f"Base de datos recargada.\nSe actualizaron {count} estudiantes.")

    def _update_sidebar_stats(self):
        scans = self.session.get_scans()
        total = len(scans)
        unnamed = 0
        
        for i, s in enumerate(scans):
            has_name = bool(s.get('student_name', '').strip())
            if not has_name:
                unnamed += 1
                self.side_bar.set_item_style(i, "white", "#e74c3c")
            else:
                self.side_bar.set_item_style(i, "#2c3e50", "#ecf0f1")
        
        try:
            self.side_bar.update_stats(total, unnamed)
        except: pass

    def toggle_viewer(self):
        if self.image_panel.winfo_viewable():
            self.image_panel.pack_forget()
            self.top_bar.set_toggle_text("Mostrar Visor")
        else:
            self.image_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
            self.top_bar.set_toggle_text("Ocultar Visor")
            if self.image_panel.current_vis_img is not None:
                 self.image_panel.display_image(self.image_panel.current_vis_img)



if __name__ == "__main__":
    root = ctk.CTk()
    app = ScannerApp(root)
    root.mainloop()
