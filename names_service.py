import os

class NamesService:
    def __init__(self, db_path=r"C:\psicofas\pruebas\nombres.txt"):
        self.db_path = db_path
        self.db = {}
        self.reload()

    def reload(self):
        """Recarga la base de datos de nombres desde el archivo."""
        self.db = {}
        if not os.path.exists(self.db_path):
            return 0
        
        count = 0
        try:
            with open(self.db_path, 'r', encoding='latin-1') as f:
                 for line in f:
                     line = line.strip()
                     if "=" in line:
                         p = line.split("=", 1)
                         rut_key = p[0].strip().upper() 
                         name = p[1].strip()
                         self.db[rut_key] = name
                         count += 1
            print(f"Service: Cargados {len(self.db)} nombres.")
        except Exception as e:
            print(f"Error cargando nombres: {e}")
        return len(self.db)

    def get_name(self, raw_rut):
        """Busca un nombre dado un RUT raw (sin puntos ni guion)."""
        return self.db.get(raw_rut, "")
