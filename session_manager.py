import pickle
import os
import time
import cv2

class SessionManager:
    """
    Gestor de Estado y Persistencia.
    
    Almacena la lista de pruebas escaneadas en memoria.
    Maneja el guardar/cargar archivos .escaner usando Pickle.
    Implementa optimización de espacio comprimiendo imágenes (JPG) antes de guardar.
    Genera reportes de texto para exportación.
    """
    def __init__(self):
        # Lista de dicts { 'path': str, 'rut_marks': list, 'ans_marks': list, 'vis_img': numpy_array, 'rut_text': str }
        self.scans = []

    def add_scan(self, scan_data):
        """Agrega un nuevo escaneo a la sesión activa en memoria."""
        self.scans.append(scan_data)

    def get_scans(self):
        return self.scans

    def get_scan(self, index):
        if 0 <= index < len(self.scans):
            return self.scans[index]
        return None

    def remove_scan(self, index):
        if 0 <= index < len(self.scans):
            del self.scans[index]
            return True
        return False

    def update_name(self, index, new_name):
        if 0 <= index < len(self.scans):
            self.scans[index]['student_name'] = new_name

    def update_rut(self, index, new_rut):
        if 0 <= index < len(self.scans):
            self.scans[index]['rut_text'] = new_rut

    def update_answer(self, scan_index, ans_index, value):
        if 0 <= scan_index < len(self.scans):
            # Asumimos que scan_data ya tiene la llave, si no la creamos
            if 'answers_values' not in self.scans[scan_index]:
                self.scans[scan_index]['answers_values'] = [""] * 90
            
            if 0 <= ans_index < 90:
                self.scans[scan_index]['answers_values'][ans_index] = value

    def clear_session(self):
        self.scans = []

    def save_session(self, filename):
        """
        Guarda la sesión en disco usando Pickle.
        OPTIMIZACIÓN: Convierte las imágenes NumPy (pesadas) a JPG en memoria para reducir drásticamente el tamaño final del archivo (factor 10x-20x).
        """
        # Crear copia optimizada para guardar
        scans_to_save = []
        for s in self.scans:
            item = s.copy()
            # Si tiene imagen CV2, comprimirla a JPG
            if 'vis_img' in item and item['vis_img'] is not None:
                success, encoded_img = cv2.imencode('.jpg', item['vis_img'], [int(cv2.IMWRITE_JPEG_QUALITY), 65])
                if success:
                    item['vis_img_compressed'] = encoded_img
                    del item['vis_img'] # Quitamos la versión pesada
            scans_to_save.append(item)

        with open(filename, 'wb') as f:
            pickle.dump(scans_to_save, f)

    def load_session(self, filename):
        """
        Carga una sesión y restaura las imágenes comprimidas a formato NumPy apto para OpenCV/Tkinter.
        """
        with open(filename, 'rb') as f:
            loaded_scans = pickle.load(f)
        
        if not isinstance(loaded_scans, list):
            raise ValueError("El archivo no tiene el formato correcto.")
        
        # Reconstruir imagenes comprimidas
        final_scans = []
        for item in loaded_scans:
            if 'vis_img_compressed' in item:
                # Descomprimir
                nparr = item['vis_img_compressed']
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                item['vis_img'] = img
                del item['vis_img_compressed']
            final_scans.append(item)

        self.scans = final_scans
        return self.scans, []

    def generate_report(self, filename):
        val_map = {"A": "1", "B": "2", "C": "3", "D": "4", "E": "5"}
        
        # Encodign latin-1 para compatibilidad con sistemas escolares antiguos (, )
        with open(filename, 'w', encoding='latin-1') as f:
            # Escribir cabecera opcional o dejar en blanco si se requiere formato raw
            pass

            for scan in self.scans:
                rut = scan.get('rut_text', '')
                # Extraer solo numeros y K
                raw_rut = ''.join(filter(lambda x: x.isdigit() or x.lower() == 'k', rut)).upper()
                if not raw_rut: raw_rut = "0"
                
                name = scan.get('student_name', '')
                
                answers = scan.get('answers_values', [""] * 90)
                # Mapear A->1, B->2... vacio->0
                ans_nums = [val_map.get(v.upper(), "0") for v in answers]
                # Asegurar 90 items
                while len(ans_nums) < 90: ans_nums.append("0")
                
                joined_ans = "\t".join(ans_nums)
                
                # Formato estricto: Rut<21 \t Name<40 \t Espacio \t Respuestas
                line = f"{raw_rut:<21}\t{name:<40}\t           \t{joined_ans}\n"
                f.write(line)
