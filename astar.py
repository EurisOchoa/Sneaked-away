import heapq

def heuristic(a, b):
    # Distancia de Manhattan como heurística
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar_pathfinding(start, goal, grid):
    # Verificar que start y goal estén dentro de la grilla y sean transitables
    rows, cols = len(grid), len(grid[0])
    
    # Verificar que las coordenadas estén dentro del rango
    if not (0 <= start[0] < cols and 0 <= start[1] < rows):
        print(f"Posición inicial {start} fuera de rango")
        return []
    if not (0 <= goal[0] < cols and 0 <= goal[1] < rows):
        print(f"Posición objetivo {goal} fuera de rango")
        return []
    
    # Verificar que las coordenadas sean transitables
    if grid[start[1]][start[0]] == 1:
        print(f"Posición inicial {start} no es transitable")
        return []
    if grid[goal[1]][goal[0]] == 1:
        print(f"Posición objetivo {goal} no es transitable")
        return []
    
    # Si start y goal son iguales, retornar una lista con ese único punto
    if start == goal:
        return [start]
    
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}
    
    open_set_hash = {start}  # Para búsqueda O(1)
    
    # DEPURACIÓN: Mostrar información de inicio
    print(f"A* iniciado desde {start} hacia {goal}")
    
    while open_set:
        current_f, current = heapq.heappop(open_set)
        open_set_hash.remove(current)
        
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            # DEPURACIÓN: Mostrar el camino encontrado
            print(f"A* encontró camino: {path[::-1]}")
            return path[::-1]  # Camino en orden correcto
        
        for neighbor in get_neighbors(current, grid):
            tentative_g_score = g_score[current] + 1
            
            if tentative_g_score < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score_value = tentative_g_score + heuristic(neighbor, goal)
                f_score[neighbor] = f_score_value
                
                if neighbor not in open_set_hash:
                    heapq.heappush(open_set, (f_score_value, neighbor))
                    open_set_hash.add(neighbor)
    
    # Si no se encuentra camino al objetivo exacto, encontrar el punto más cercano
    closest_point = None
    min_distance = float('inf')
    
    for x in range(cols):
        for y in range(rows):
            if grid[y][x] == 0:  # Si es transitable
                distance = heuristic((x, y), goal)
                if distance < min_distance:
                    min_distance = distance
                    closest_point = (x, y)
    
    # DEPURACIÓN: No se encontró camino, intentando con punto cercano
    if closest_point:
        print(f"No hay camino directo. Intentando con punto cercano: {closest_point}")
        if closest_point != start:
            return astar_pathfinding(start, closest_point, grid)
                
    print("No se encontró ningún camino posible")
    return []  # Si no se encuentra camino

def get_neighbors(pos, grid):
    neighbors = []
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # 4 direcciones (sin diagonales)
    
    rows = len(grid)
    cols = len(grid[0])
    
    for dx, dy in directions:
        x, y = pos[0] + dx, pos[1] + dy
        if 0 <= x < cols and 0 <= y < rows and grid[y][x] == 0:  # 0 = transitable
            neighbors.append((x, y))
    
    return neighbors