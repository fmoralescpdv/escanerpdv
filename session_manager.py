import pickle
import os
import time

class SessionManager:
    def __init__(self):
        # Lista de dicts: { 'path': str, 'rut_marks': list, 'ans_marks': list, 'vis_img': numpy_array, 'rut_text': str }
        self.scans = []

    def add_scan(self, scan_data):
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
        with open(filename, 'wb') as f:
            pickle.dump(self.scans, f)

    def load_session(self, filename):
        with open(filename, 'rb') as f:
            loaded_scans = pickle.load(f)
        
        if not isinstance(loaded_scans, list):
            raise ValueError("El archivo no tiene el formato correcto.")
        
        # Como ahora borramos las imagenes para ahorrar espacio, no verificamos integridad de archivos fisicos.
        self.scans = loaded_scans
        return self.scans, []

    def generate_report(self, filename):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("REPORTE DE PRUEBAS ESCANEADAS\n")
            f.write("===============================\n")
            f.write(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Hojas: {len(self.scans)}\n\n")
            
            f.write(f"{'#':<4} | {'RUT':<15} | {'Nombre':<20} | {'Respuestas'}\n")
    def generate_report(self, filename):
        val_map = {"A": "1", "B": "2", "C": "3", "D": "4", "E": "5"}
        
        # Encodign latin-1 para compatibilidad con sistemas escolares antiguos (, )
        with open(filename, 'w', encoding='latin-1') as f:
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
