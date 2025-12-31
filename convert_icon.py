from PIL import Image
import os

def convert_icon():
    source = "Ico.png"
    dest = "icon.ico"
    
    if os.path.exists(source):
        try:
            img = Image.open(source)
            # Create a high quality icon containing multiple sizes
            img.save(dest, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
            print(f"Successfully converted {source} to {dest}")
        except Exception as e:
            print(f"Error converting image: {e}")
    else:
        print(f"Source file {source} not found.")

if __name__ == "__main__":
    convert_icon()
