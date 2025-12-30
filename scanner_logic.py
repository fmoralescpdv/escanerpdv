import twain
import cv2
import numpy as np
import os
import time

# --- Configuración ---
UMBRAL_NEGRO = 150 
AREA_MINIMA = 100
AREA_MAXIMA = 3000

class ScannerLogic:
    def __init__(self):
        self.current_source_name = None

    def get_sources(self, window_id):
        try:
            sm = twain.SourceManager(window_id)
            return sm.GetSourceList()
        except Exception as e:
            raise e

    def set_source(self, source_name):
        self.current_source_name = source_name

    def start_scanning(self, window_id, show_ui=True):
        """
        Inicia el proceso de escaneo (Modeless/Background friendly).
        Retorna el objeto Source (ss) activo, o None si se canceló/falló apertura.
        """
        try:
            sm = twain.SourceManager(window_id)
            ss = sm.OpenSource(self.current_source_name)
            if not ss:
                return None
            
            # Usamos Modeless (1/0, 0) para permitir polling externas
            # show_ui=1 -> UI Driver, show_ui=0 -> Direct Scan
            ss.RequestAcquire(1 if show_ui else 0, 0)
            return ss
        except Exception as e:
            raise e

    def close_source(self, ss):
        """Limpia la fuente TWAIN."""
        if ss:
            try:
                # Forzamos cierre si es posible, o dejamos que el GC actúe
                del ss
            except:
                pass

    def transfer_next(self, ss, base_filename, index):
        """
        Intenta transferir una imagen desde la fuente activa.
        Retorna: (ruta_archivo, pending_count) si hay éxito.
                 (None, pending_count) si no hay imagen lista pero connection ok.
        Lanza excepción si hay error real (no SEQERROR).
        """
        try:
            # Primero consultamos si hay información de imagen lista (State 6)
            # Esto verifica si el usuario ya presionó "Escanear" en la UI del driver.
            ss.GetImageInfo()
        except Exception:
            # Si falla GetImageInfo, asumimos que no estamos en State 6 (Not Ready).
            # Puede ser SEQERROR, o que la ventana se cerró (State 4).
            # En cualquier caso, no podemos transferir. Retornamos None (Wait).
            return (None, -1)

        # Si GetImageInfo funciona, estamos en State 6 -> Transferimos
        try:
            (handle, count) = ss.XferImageNatively()
        except Exception as e:
            raise e
        
        if handle:
            filename = f"{base_filename}_{index}.bmp"
            try:
                twain.DIBToBMFile(handle, filename)
                twain.GlobalHandleFree(handle)
                return (filename, count)
            except Exception as save_err:
                print(f"Error guardando imagen: {save_err}")
                twain.GlobalHandleFree(handle)
                return (None, count)
        
        # Si handle es None pero no hubo excepción
        return (None, count)

    def process_image(self, image_path):
        """
        Procesa la imagen midiendo dinámicamente el tamaño promedio de las burbujas para filtrar texto.
        """
        if not os.path.exists(image_path):
            return "", [], None

        img = cv2.imread(image_path)
        if img is None:
            return "", [], None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, UMBRAL_NEGRO, 255, cv2.THRESH_BINARY_INV)
        
        # Morphological Closing
        kernel = np.ones((3,3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rut_marks = []
        answer_marks = []
        vis_img = img.copy()

        height, width = img.shape[:2]
        limit_y_rut = height * 0.35

        # 1. Recolección de Candidatos Geométricos
        candidates = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Filtro Absoluto Inicial
            if AREA_MINIMA < area < AREA_MAXIMA:
                x, y, w, h = cv2.boundingRect(cnt)
                aspect_ratio = float(w)/h
                
                # Geometría cuadrada/circular
                if 0.7 < aspect_ratio < 1.3:
                    rect_area = w * h
                    extent = float(area) / rect_area
                    
                    # Solidez razonable
                    if extent > 0.40:
                       candidates.append({
                           'cnt': cnt,
                           'area': area,
                           'rect': (x, y, w, h),
                           'extent': extent
                       })

        # 2. Filtro Dinámico de Tamaño (para eliminar letras pequeñas)
        if candidates:
            # Calcular mediana del área de los candidatos (tamaño de burbuja típico)
            areas = sorted([c['area'] for c in candidates])
            median_area = areas[len(areas)//2]
            
            # Umbral: Aceptamos burbujas que sean al menos el 70% del tamaño mediano
            min_dynamic_area = median_area * 0.70
            
            final_candidates = [c for c in candidates if c['area'] >= min_dynamic_area]
        else:
            final_candidates = []

        # 3. Procesamiento de Candidatos Finales (Detección de Tinta)
        for c in final_candidates:
            x, y, w, h = c['rect']
            area = c['area']
            
            roi = thresh[y:y+h, x:x+w]
            density = cv2.countNonZero(roi) / (w * h)
            
            # Umbral de marcado
            is_marked = density > 0.32 
            
            color = (0, 255, 0) if is_marked else (0, 0, 255)
            cv2.rectangle(vis_img, (x, y), (x + w, y + h), color, 2)
            cx, cy = x + w // 2, y + h // 2

            mark_data = {'pos': (cx, cy), 'area': area, 'density': density, 'marked': is_marked}

            if cy < limit_y_rut:
                rut_marks.append(mark_data)
            else:
                answer_marks.append(mark_data)
        
        decoded_rut = self._decode_rut(rut_marks)
        decoded_answers = self._decode_answers(answer_marks)

        return decoded_rut, decoded_answers, vis_img

    def _cluster_1d(self, values, tolerance):
        # ... (same)
        if not values: return []
        sorted_vals = sorted(values)
        clusters = []
        current = [sorted_vals[0]]
        
        for v in sorted_vals[1:]:
            if v - current[-1] > tolerance:
                clusters.append(sum(current)/len(current))
                current = [v]
            else:
                current.append(v)
        clusters.append(sum(current)/len(current))
        return clusters

    def _decode_rut(self, marks):
        """
        Decodifica RUT reconstruyendo la grilla mediante pasos relativos.
        """
        if not marks: return ""
        
        # 1. Detectar Grilla X (Columnas)
        all_xs = [m['pos'][0] for m in marks]
        avg_area = sum(m['area'] for m in marks) / len(marks)
        estim_dim = avg_area ** 0.5
        tol = max(10, estim_dim * 0.6)
        x_lines = self._cluster_1d(all_xs, tol)
        
        # 2. Detectar Grilla Y (Filas)
        all_ys = [m['pos'][1] for m in marks]
        y_lines = self._cluster_1d(all_ys, tol)
        
        # Calcular paso vertical promedio (altura de fila)
        if len(y_lines) > 1:
            steps = [y_lines[i+1] - y_lines[i] for i in range(len(y_lines)-1)]
            steps.sort()
            avg_step = steps[len(steps)//2] # Mediana
            if avg_step < tol: avg_step = tol * 2 # Sanity check
        else:
            avg_step = estim_dim * 1.5 # Fallback guestimate

        # Asumimos que la primera linea Y detectada es la fila 0
        y0 = y_lines[0] if y_lines else 0
        
        rut_str = ""
        for x_line in x_lines:
            col_candidates = [m for m in marks if abs(m['pos'][0] - x_line) < tol]
            if not col_candidates:
                rut_str += "?"
                continue
            
            marked_ones = [m for m in col_candidates if m['marked']]
            if not marked_ones:
                rut_str += "?" 
                continue
            
            best_mark = max(marked_ones, key=lambda m: m['density'])
            y_mark = best_mark['pos'][1]
            
            # Calcular índice relativo basado en distancia a y0
            row_idx = int(round((y_mark - y0) / avg_step))
            
            if row_idx < 10:
                rut_str += str(row_idx)
            else:
                # Cualquier cosa en la fila 10 o inferior dentro de la zona RUT se considera K
                rut_str += "K"

        return rut_str

    def _decode_answers(self, marks):
        """
        Decodifica respuestas soportando múltiples columnas de preguntas.
        Ej: Q1-Q25 a la izquierda, Q26-50 a la derecha.
        """
        if not marks: return []
        
        avg_area = sum(m['area'] for m in marks) / len(marks)
        estim_dim = avg_area ** 0.5
        tol = max(10, estim_dim * 0.6)
        
        # 1. Detectar TODAS las líneas verticales de burbujas (X-lines)
        all_xs = [m['pos'][0] for m in marks]
        x_lines = self._cluster_1d(all_xs, tol)
        
        if not x_lines: return []
        
        # 2. Agrupar X-lines en "Bloques de Preguntas"
        x_lines.sort()
        blocks = []
        current_block = [x_lines[0]]
        
        if len(x_lines) > 1:
            gaps = [x_lines[i+1] - x_lines[i] for i in range(len(x_lines)-1)]
            median_gap = sorted(gaps)[len(gaps)//2]
            # Umbral de separación de bloques (Salto grande horizontal)
            block_sep_thresh = max(median_gap * 2.5, estim_dim * 3)
        else:
            block_sep_thresh = estim_dim * 3

        for x in x_lines[1:]:
            if x - current_block[-1] > block_sep_thresh:
                blocks.append(current_block)
                current_block = [x]
            else:
                current_block.append(x)
        blocks.append(current_block)
        
        # 3. Procesar cada Bloque secuencialmente
        answers = []
        options = "ABCDEFGHIJK"
        
        for block_x_lines in blocks:
            # Definir rango X del bloque
            min_x_block = min(block_x_lines) - tol
            max_x_block = max(block_x_lines) + tol
            
            block_marks = [m for m in marks if min_x_block <= m['pos'][0] <= max_x_block]
            if not block_marks: continue

            # Detectar filas Y dentro de este bloque
            block_ys = [m['pos'][1] for m in block_marks]
            y_lines = self._cluster_1d(block_ys, tol)
            
            # Parametros para decodificar opciones
            start_x = block_x_lines[0]
            
            if len(block_x_lines) > 1:
                bgaps = [block_x_lines[i+1] - block_x_lines[i] for i in range(len(block_x_lines)-1)]
                block_step = sorted(bgaps)[len(bgaps)//2]
            else:
                block_step = 100 
            
            for y in y_lines:
                row_candidates = [m for m in block_marks if abs(m['pos'][1] - y) < tol]
                marked_ones = [m for m in row_candidates if m['marked']]
                
                if not marked_ones:
                    answers.append("") 
                    continue
                
                best_mark = max(marked_ones, key=lambda m: m['density'])
                mx = best_mark['pos'][0]
                
                # Indice relativo al inicio del bloque
                col_idx = int(round((mx - start_x) / block_step))
                
                if 0 <= col_idx < len(options):
                    answers.append(options[col_idx])
                else:
                    answers.append("?")
                    
        return answers
