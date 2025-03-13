import pygame 
from os.path import join 
from os import walk

WINDOW_WIDTH, WINDOW_HEIGHT = 1280,720 
TILE_SIZE = 64
GRID_ROWS = WINDOW_HEIGHT // TILE_SIZE
GRID_COLS = WINDOW_WIDTH // TILE_SIZE

# Joystick settings
JOYSTICK_DEADZONE = 0.2  # Zona muerta para evitar movimientos no deseados
AIM_STICK_SPEED = 500    # Velocidad de apuntado con el stick derecho
AIM_SENSITIVITY = 0.8    # Sensibilidad del stick derecho para apuntar