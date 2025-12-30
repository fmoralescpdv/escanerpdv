import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import cv2

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + 20
            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("Segoe UI", 9, "normal"))
            label.pack(ipadx=1)
        except: pass

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw: tw.destroy()

class TopBar(ctk.CTkFrame):
    def __init__(self, parent, callbacks):
        super().__init__(parent, fg_color="transparent") 
        self.callbacks = callbacks 
        self._init_ui()

    def _init_ui(self):
        self.pack(side=tk.TOP, fill=tk.X, anchor="w", pady=(0, 10))
        
        btn_font = ("Segoe UI", 12, "bold")
        
        self.btn_save = ctk.CTkButton(self, text="Guardar Sesión", command=self.callbacks.get('save'), width=130, font=btn_font)
        self.btn_save.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_load = ctk.CTkButton(self, text="Cargar Sesión", command=self.callbacks.get('load'), width=130, font=btn_font)
        self.btn_load.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_review = ctk.CTkButton(self, text="Revisar pruebas", command=self.callbacks.get('review'), width=130, font=btn_font)
        self.btn_review.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_reload_names = ctk.CTkButton(self, text="Actualizar Nombres", command=self.callbacks.get('reload_names'), width=160, font=btn_font)
        self.btn_reload_names.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_options = ctk.CTkButton(self, text="Opciones ▼", command=self.show_options_menu, width=120, font=("Segoe UI", 12, "bold"))
        self.btn_options.pack(side=tk.RIGHT, padx=5)

        self.menu_ops = tk.Menu(self, tearoff=0)
        self.menu_ops.add_command(label="Seleccionar Escáner", command=self.callbacks.get('select_source'))
        self.menu_ops.add_command(label="Ocultar Visor", command=self.callbacks.get('toggle_view'))

    def show_options_menu(self):
        try:
            x = self.btn_options.winfo_rootx()
            y = self.btn_options.winfo_rooty() + self.btn_options.winfo_height()
            self.menu_ops.tk_popup(x, y)
        finally:
            self.menu_ops.grab_release()

    def set_toggle_text(self, text):
        try:
             self.menu_ops.entryconfigure(1, label=text)
        except: pass

class SideBar(ctk.CTkFrame):
    def __init__(self, parent, callbacks):
        super().__init__(parent, width=200, corner_radius=10)
        self.callbacks = callbacks 
        self._init_ui()

    def _init_ui(self):
        self.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        ctk.CTkLabel(self, text="Sesión de Escaneo", font=("Segoe UI", 16, "bold")).pack(pady=(10, 5))
        
        self.btn_scan = ctk.CTkButton(self, text="Escanear (Multiple/ADF)", command=self.callbacks.get('scan'), height=40, width=180, font=("Segoe UI", 14, "bold"))
        self.btn_scan.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.btn_quick = ctk.CTkButton(self, text="Escaneo Rápido", command=self.callbacks.get('quick_scan'), height=40, font=("Segoe UI", 14, "bold"), fg_color="#E67E22", hover_color="#D35400")
        self.btn_quick.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Boton Eliminar al fondo (Empaquetar antes de la lista para que quede fijo abajo)
        self.btn_delete = ctk.CTkButton(self, text="Eliminar Prueba", command=self.callbacks.get('delete'), height=30, fg_color="#c0392b", hover_color="#e74c3c", font=("Segoe UI", 12, "bold"))
        self.btn_delete.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        # Estadisticas (encima de eliminar)
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=0)
        
        self.lbl_total = ctk.CTkLabel(self.stats_frame, text="Total: 0", font=("Segoe UI", 12, "bold"))
        self.lbl_total.pack(side=tk.LEFT, padx=10)
        
        self.lbl_no_name = ctk.CTkLabel(self.stats_frame, text="S/N: 0", font=("Segoe UI", 12, "bold"), text_color="#e74c3c")
        self.lbl_no_name.pack(side=tk.RIGHT, padx=10)
        ToolTip(self.lbl_no_name, "Pruebas sin nombre")
        
        # Lista ocupando el resto
        self.lst_scans = tk.Listbox(self, height=30, font=("Segoe UI", 10), borderwidth=0, highlightthickness=0, bg="#ecf0f1", fg="#2c3e50")
        self.lst_scans.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.lst_scans.bind('<<ListboxSelect>>', self.callbacks.get('on_select'))

    def add_item(self, text):
        self.lst_scans.insert(tk.END, text)

    def delete_item(self, index):
        self.lst_scans.delete(index)

    def select_last(self):
        self.lst_scans.selection_clear(0, tk.END)
        self.lst_scans.selection_set(tk.END)

    def select_index(self, index):
        self.lst_scans.selection_clear(0, tk.END)
        self.lst_scans.selection_set(index)

    def update_stats(self, total, unnamed):
        self.lbl_total.configure(text=f"Total: {total}")
        self.lbl_no_name.configure(text=f"S/N: {unnamed}")

    def clear(self):
        self.lst_scans.delete(0, tk.END)
    
    def get_selection_index(self):
        sel = self.lst_scans.curselection()
        if sel: return sel[0]
        return None

    def set_item_style(self, index, fg_color, bg_color):
        try:
            self.lst_scans.itemconfig(index, fg=fg_color, bg=bg_color)
        except: pass

class AnswerPanel(ctk.CTkFrame):
    def __init__(self, parent, callbacks):
        super().__init__(parent, corner_radius=10)
        self.callbacks = callbacks 
        self.answer_widgets = []
        self._init_ui()

    def _init_ui(self):
        self.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10), expand=True)

        # RUT Area
        frame_rut = ctk.CTkFrame(self, fg_color="transparent")
        frame_rut.pack(fill=tk.X, pady=(10, 5), padx=10)
        
        ctk.CTkLabel(frame_rut, text="RUT Alumno", font=("Segoe UI", 12, "bold"), anchor="w").pack(fill=tk.X)
        self.rut_var = tk.StringVar()
        self.entry_rut = ctk.CTkEntry(frame_rut, textvariable=self.rut_var, font=("Courier", 16, "bold"), justify="center", height=35)
        self.entry_rut.pack(fill=tk.X, pady=2)
        self.entry_rut.bind('<KeyRelease>', self.callbacks.get('on_rut_change'))

        # Name Area
        frame_name = ctk.CTkFrame(self, fg_color="transparent")
        frame_name.pack(fill=tk.X, pady=5, padx=10)
        
        ctk.CTkLabel(frame_name, text="Nombre Alumno", font=("Segoe UI", 12, "bold"), anchor="w").pack(fill=tk.X)
        self.name_var = tk.StringVar()
        self.entry_name = ctk.CTkEntry(frame_name, textvariable=self.name_var, font=("Segoe UI", 14), height=35, justify="center")
        self.entry_name.pack(fill=tk.X, pady=2)
        self.entry_name.bind('<KeyRelease>', self.callbacks.get('on_name_change'))

        # Answers Area - Title
        ctk.CTkLabel(self, text="Respuestas", font=("Segoe UI", 14, "bold")).pack(pady=(10, 5))

        # CTKScrollableFrame
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="")
        self.scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Grid Setup
        columns = 3
        for i in range(columns):
            self.scroll_frame.grid_columnconfigure(i, weight=1)

        total_items = 90
        rows_per_col = total_items // columns
        
        self.vcmd = (self.register(self._validate_answer_input), '%P')

        for i in range(1, 91):
            # Inner Container
            f = ctk.CTkFrame(self.scroll_frame, border_width=1, border_color="#bdc3c7", fg_color="transparent")
            
            # Label Num
            lbl_num = ctk.CTkLabel(f, text=f"{i}", width=30, font=("Segoe UI", 11, "bold"), fg_color="#ecf0f1", text_color="#2c3e50")
            lbl_num.pack(side=tk.LEFT, padx=0, fill=tk.Y)
            
            # Entry Val
            entry_val = ctk.CTkEntry(f, width=40, font=("Segoe UI", 12), justify="center", 
                                     fg_color="white", text_color="black", border_width=0)
            entry_val.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2) # Fill space
            
            entry_val.bind('<KeyRelease>', lambda e, idx=i-1: self.callbacks.get('on_answer_change')(e, idx))
            
            row = (i - 1) % rows_per_col
            col = (i - 1) // rows_per_col
            
            f.grid(row=row, column=col, sticky="ew", padx=3, pady=3)
            self.answer_widgets.append((f, lbl_num, entry_val))

    # Public methods for Controller
    def get_rut(self):
        return self.rut_var.get()

    def set_rut(self, val):
        self.rut_var.set(val)
    
    def get_name(self):
        return self.name_var.get()
    
    def set_name(self, val):
        self.name_var.set(val)

    def update_rut_cursor(self):
        self.entry_rut.icursor(tk.END)

    def _on_ans_canvas_resize(self, event):
        canvas_width = event.width
        self.canvas_ans.itemconfig(self.frame_window_id, width=canvas_width)
    
    def _validate_answer_input(self, new_value):
        if new_value == "": return True
        if len(new_value) > 1: return False
        return new_value.upper() in ["A", "B", "C", "D", "E"]
    
    # Public methods for Controller
    def get_rut(self):
        return self.rut_var.get()

    def set_rut(self, val):
        self.rut_var.set(val)
    
    def get_name(self):
        return self.name_var.get()
    
    def set_name(self, val):
        self.name_var.set(val)

    def update_rut_cursor(self):
        self.entry_rut.icursor(tk.END)
    
    def clear_answers(self):
        for f, lbl, entry in self.answer_widgets:
            f.configure(fg_color="transparent")
            entry.delete(0, tk.END)
    
    def set_answer(self, index, value, mark_detected=False):
        if 0 <= index < len(self.answer_widgets):
            f, lbl, entry = self.answer_widgets[index]
            entry.delete(0, tk.END)
            entry.insert(0, value)
            if mark_detected:
                f.configure(fg_color="#a8e6cf") # Verde suave
            else:
                 f.configure(fg_color="transparent")

    def highlight_mark(self, index):
        if 0 <= index < len(self.answer_widgets):
             f, lbl, entry = self.answer_widgets[index]
             f.configure(fg_color="#a8e6cf")

class ImagePanel(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, corner_radius=10)
        self._init_ui()
        self.current_vis_img = None
    
    def _init_ui(self):
        self.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ctk.CTkLabel(self, text="Vista Previa", font=("Segoe UI", 16, "bold")).pack(pady=5)
        
        self.canvas = tk.Canvas(self, bg="#34495e", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.canvas.bind("<Configure>", self._on_resize)
    
    def _on_resize(self, event):
        if self.current_vis_img is not None:
            self.display_image(self.current_vis_img)
            
    def display_image(self, cv2_img):
        if cv2_img is None: return
        self.current_vis_img = cv2_img 
        
        vis_img_rgb = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
        im_pil = Image.fromarray(vis_img_rgb)
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width < 10 or canvas_height < 10: return
 
        im_display = im_pil.copy()
        im_display.thumbnail((canvas_width, canvas_height), Image.Resampling.BILINEAR)
        
        self.tk_image = ImageTk.PhotoImage(im_display)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width//2, canvas_height//2, image=self.tk_image, anchor=tk.CENTER)
