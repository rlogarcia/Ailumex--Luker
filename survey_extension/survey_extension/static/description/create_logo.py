#!/usr/bin/env python3
"""
Script para crear el logo PNG de Fundación Luker
Este script usa PIL/Pillow para crear una imagen PNG del logo
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_fundacion_luker_logo():
    """Crea el logo de Fundación Luker en formato PNG"""
    
    # Dimensiones del logo
    width = 400
    height = 120
    
    # Crear imagen con fondo blanco
    img = Image.new('RGBA', (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Centro del círculo
    cx, cy = 60, 60
    radius = 42
    
    # Dibujar círculo azul principal
    draw.ellipse(
        [(cx - radius, cy - radius), (cx + radius, cy + radius)],
        fill=(74, 144, 226, 255),
        outline=(46, 107, 168, 255),
        width=3
    )
    
    # Dibujar cruz blanca en el centro
    # Barra horizontal
    draw.rectangle(
        [(cx - 20, cy - 5), (cx + 20, cy + 5)],
        fill=(255, 255, 255, 255)
    )
    # Barra vertical
    draw.rectangle(
        [(cx - 5, cy - 20), (cx + 5, cy + 20)],
        fill=(255, 255, 255, 255)
    )
    
    # Puntos decorativos de colores (confetti style)
    colors = [
        # Puntos grandes en esquinas
        ((cx - 20, cy - 20), 5, (255, 107, 107, 255)),
        ((cx + 20, cy - 20), 5, (78, 205, 196, 255)),
        ((cx - 20, cy + 20), 5, (255, 230, 109, 255)),
        ((cx + 20, cy + 20), 5, (149, 225, 211, 255)),
        
        # Puntos medianos
        ((cx, cy - 30), 4, (255, 160, 122, 255)),
        ((cx + 30, cy), 4, (152, 216, 200, 255)),
        ((cx, cy + 30), 4, (247, 220, 111, 255)),
        ((cx - 30, cy), 4, (187, 143, 206, 255)),
        
        # Puntos pequeños
        ((cx - 25, cy - 10), 3, (240, 98, 146, 255)),
        ((cx + 25, cy - 10), 3, (100, 181, 246, 255)),
        ((cx - 25, cy + 10), 3, (255, 183, 77, 255)),
        ((cx + 25, cy + 10), 3, (129, 199, 132, 255)),
        ((cx - 10, cy - 25), 3, (186, 104, 200, 255)),
        ((cx + 10, cy - 25), 3, (77, 208, 225, 255)),
        ((cx - 10, cy + 25), 3, (220, 231, 117, 255)),
        ((cx + 10, cy + 25), 3, (255, 138, 101, 255)),
    ]
    
    for (x, y), r, color in colors:
        draw.ellipse(
            [(x - r, y - r), (x + r, y + r)],
            fill=color
        )
    
    # Intentar cargar fuente, si no existe usar la predeterminada
    try:
        font_fundacion = ImageFont.truetype("arial.ttf", 26)
        font_luker = ImageFont.truetype("arialbd.ttf", 32)
    except:
        font_fundacion = ImageFont.load_default()
        font_luker = ImageFont.load_default()
    
    # Dibujar texto "FUNDACIÓN"
    draw.text(
        (140, 40),
        "FUNDACIÓN",
        fill=(102, 102, 102, 255),
        font=font_fundacion
    )
    
    # Dibujar texto "LUKER"
    draw.text(
        (140, 68),
        "LUKER",
        fill=(74, 74, 74, 255),
        font=font_luker
    )
    
    # Dibujar línea decorativa
    draw.line(
        [(140, 92), (340, 92)],
        fill=(74, 144, 226, 255),
        width=3
    )
    
    # Guardar la imagen
    output_path = os.path.join(os.path.dirname(__file__), 'fundacion_luker_logo.png')
    img.save(output_path, 'PNG')
    print(f"✓ Logo creado exitosamente: {output_path}")
    
    return output_path

if __name__ == "__main__":
    try:
        create_fundacion_luker_logo()
        print("\n¡Logo PNG de Fundación Luker creado con éxito!")
    except Exception as e:
        print(f"Error al crear el logo: {e}")
        print("\nAsegúrate de tener instalado Pillow:")
        print("  pip install Pillow")
