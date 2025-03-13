from settings import * 
from math import atan2, degrees
from astar import astar_pathfinding
from behavior_tree import Node,Selector,Sequence,Action
from random import randint, choice

class Sprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft = pos)
        self.ground = True

class CollisionSprite(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft = pos)

class Gun(pygame.sprite.Sprite):
    def __init__(self, player, groups):
        # player connection 
        self.player = player 
        self.distance = 140
        self.player_direction = pygame.Vector2(0, 1)  # Dirección inicial hacia abajo
        self.aim_position = pygame.Vector2(0, 1)  # Posición relativa para apuntar

        # sprite setup 
        super().__init__(groups)
        self.gun_surf = pygame.image.load(join('images', 'gun', 'gun.png')).convert_alpha()
        self.image = self.gun_surf
        self.rect = self.image.get_rect(center = self.player.rect.center + self.player_direction * self.distance)
    
    def get_direction(self):
        # Verificar joysticks disponibles
        if pygame.joystick.get_count() > 0:
            joystick = pygame.joystick.Joystick(0)
            
            # Leer el stick derecho para apuntar
            right_x = joystick.get_axis(3)  # Eje X del stick derecho (puede variar según el control)
            right_y = joystick.get_axis(4)  # Eje Y del stick derecho (puede variar según el control)
            
            # Si el stick derecho está fuera de la zona muerta, actualizar dirección
            if abs(right_x) > JOYSTICK_DEADZONE or abs(right_y) > JOYSTICK_DEADZONE:
                new_direction = pygame.Vector2(right_x, right_y)
                
                # Solo actualizar si la dirección es significativa
                if new_direction.length() > JOYSTICK_DEADZONE:
                    self.player_direction = new_direction.normalize()
            
            # Verificar botones para disparar (dejamos el input aquí para consistency)
            # Se procesa en el método input() en la clase Game
        else:
            # Input de mouse como fallback
            mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
            player_pos = pygame.Vector2(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2)
            self.player_direction = (mouse_pos - player_pos).normalize()

    def rotate_gun(self):
        angle = degrees(atan2(self.player_direction.x, self.player_direction.y)) - 90
        if self.player_direction.x > 0:
            self.image = pygame.transform.rotozoom(self.gun_surf, angle, 1)
        else:
            self.image = pygame.transform.rotozoom(self.gun_surf, abs(angle), 1)
            self.image = pygame.transform.flip(self.image, False, True)

    def update(self, _):
        self.get_direction()
        self.rotate_gun()
        self.rect.center = self.player.rect.center + self.player_direction * self.distance
        
class Bullet(pygame.sprite.Sprite):
    def __init__(self, surf, pos, direction, groups):
        super().__init__(groups)
        self.image = surf 
        self.rect = self.image.get_rect(center = pos)
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 1000

        self.direction = direction 
        self.speed = 1200 
    
    def update(self, dt):
        self.rect.center += self.direction * self.speed * dt

        if pygame.time.get_ticks() - self.spawn_time >= self.lifetime:
            self.kill()


class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos, frames, groups, player, collision_sprites, grid):
        super().__init__(groups)
        self.player = player
        self.grid = grid
        self.frames = frames
        self.frame_index = 0
        self.animation_speed = 6
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect(center=pos)
        self.hitbox_rect = self.rect.inflate(-20, -40)
        self.direction = pygame.Vector2()
        self.speed = 200
        self.path = []
        self.death_time = 0
        self.health = 100
        self.attack_cooldown = 1000  # 1 segundo entre ataques
        self.last_attack_time = 0
        self.last_path_update = 0
        self.path_update_cooldown = 500  # Incrementado para reducir la frecuencia de cálculos
        self.collision_sprites = collision_sprites
        self.attack_damage = 10  # Daño que causa cada ataque
        self.attack_range = 80   # Distancia para poder atacar
        self.is_attacking = False
        self.attack_animation_time = 0
        self.detection_range = 800  # Rango de detección
        self.debug_mode = True  # Activar depuración para visualizar problemas
        self.surface = pygame.display.get_surface()  # Para dibujar elementos de depuración

        # Árbol de comportamiento con opción de persecución simple
        self.behavior_tree = Selector([
            # Secuencia de ataque: alta prioridad
            Sequence([Action(self.is_player_in_attack_range), Action(self.attack_player)]),
            # Persecución: segunda prioridad (esto siempre se ejecutará si el jugador está vivo)
            Action(self.simple_chase_player)  # ¡Cambiado a persecución simple!
        ])

    def animate(self, dt):
        # Si está atacando, usar animación de ataque (podría ser más rápida)
        if self.is_attacking:
            animation_speed = self.animation_speed * 1.5
        else:
            animation_speed = self.animation_speed
            
        self.frame_index += animation_speed * dt
        self.image = self.frames[int(self.frame_index) % len(self.frames)]
        
        # Si la animación de ataque ha terminado
        if self.is_attacking and pygame.time.get_ticks() - self.attack_animation_time > 300:
            self.is_attacking = False

    def is_player_in_attack_range(self):
        """Verifica si el jugador está lo suficientemente cerca para atacar"""
        if not self.player.is_alive:
            return False
            
        distance = pygame.Vector2(self.rect.center).distance_to(pygame.Vector2(self.player.rect.center))
        return distance < self.attack_range

    def attack_player(self):
        """Ataca al jugador si está en rango y el cooldown ha terminado"""
        current_time = pygame.time.get_ticks()
        
        # Verificar si podemos atacar nuevamente
        if current_time - self.last_attack_time >= self.attack_cooldown:
            self.last_attack_time = current_time
            self.attack_animation_time = current_time
            self.is_attacking = True
            
            # Asegurarse de que el jugador sigue vivo antes de atacar
            if self.player.is_alive:
                self.player.take_damage(self.attack_damage)
                
                # Detener brevemente al enemigo durante el ataque
                self.direction = pygame.Vector2(0, 0)
                
                # Orientar al enemigo hacia el jugador
                player_direction = pygame.Vector2(self.player.rect.center) - pygame.Vector2(self.rect.center)
                if player_direction.length() > 0:
                    self.face_direction = player_direction.normalize()
            
            return True
        
        # Si estamos en cooldown, nos quedamos en posición pero seguimos considerando
        # que estamos "atacando" para el árbol de comportamiento
        return True

    def simple_chase_player(self):
        """Método simplificado para perseguir al jugador directamente"""
        if not self.player.is_alive:
            # Si el jugador está muerto, detenerse
            self.direction = pygame.Vector2(0, 0)
            return False
        
        # Perseguir directamente sin usar A*
        player_vec = pygame.Vector2(self.player.rect.center)
        enemy_vec = pygame.Vector2(self.rect.center)
        direction = player_vec - enemy_vec
        
        if direction.length() > 0:
            self.direction = direction.normalize()
        else:
            self.direction = pygame.Vector2(0, 0)
            
        # Siempre devolver True para que el árbol de comportamiento siga ejecutando esta acción
        return True

    def chase_player(self):
        """Método original de persecución que usa A* (mantendré para referencia)"""
        if not self.player.is_alive:
            # Si el jugador está muerto, detenerse
            self.direction = pygame.Vector2(0, 0)
            return False
        
        current_time = pygame.time.get_ticks()
        
        # Actualizar el camino periódicamente o si está vacío
        if not self.path or current_time - self.last_path_update >= self.path_update_cooldown:
            self.last_path_update = current_time
            
            # Convertir posiciones a coordenadas de grilla
            player_grid_pos = (
                int(self.player.rect.centerx // TILE_SIZE),
                int(self.player.rect.centery // TILE_SIZE)
            )
            enemy_grid_pos = (
                int(self.rect.centerx // TILE_SIZE),
                int(self.rect.centery // TILE_SIZE)
            )
            
            # Asegurarnos de que las coordenadas estén dentro de los límites
            player_grid_pos = (
                max(0, min(GRID_COLS-1, player_grid_pos[0])),
                max(0, min(GRID_ROWS-1, player_grid_pos[1]))
            )
            enemy_grid_pos = (
                max(0, min(GRID_COLS-1, enemy_grid_pos[0])),
                max(0, min(GRID_ROWS-1, enemy_grid_pos[1]))
            )
            
            # Calcular nuevo camino
            new_path = astar_pathfinding(enemy_grid_pos, player_grid_pos, self.grid)
            
            if new_path:
                # Eliminar el primer nodo si es nuestra posición actual
                if new_path and len(new_path) > 1:
                    self.path = new_path[1:]  # Saltamos el nodo actual
                else:
                    self.path = new_path
            else:
                # Si no hay camino, intentar moverse directamente hacia el jugador
                self.path = []
        
        # Si hay un camino, moverse hacia el siguiente punto
        if self.path:
            next_pos = self.path[0]
            target_world_pos = (next_pos[0] * TILE_SIZE + TILE_SIZE // 2, 
                               next_pos[1] * TILE_SIZE + TILE_SIZE // 2)
            
            # Si estamos cerca del objetivo, avanzar al siguiente punto
            if pygame.Vector2(self.rect.center).distance_to(pygame.Vector2(target_world_pos)) < 10:
                self.path.pop(0)
                if self.path:
                    next_pos = self.path[0]
                    target_world_pos = (next_pos[0] * TILE_SIZE + TILE_SIZE // 2, 
                                     next_pos[1] * TILE_SIZE + TILE_SIZE // 2)
            
            # Calcular dirección hacia el objetivo
            direction = pygame.Vector2(target_world_pos) - pygame.Vector2(self.rect.center)
            if direction.length() > 0:
                self.direction = direction.normalize()
            
            return True
            
        else:
            # Si no hay camino, moverse directamente hacia el jugador
            direction = pygame.Vector2(self.player.rect.center) - pygame.Vector2(self.rect.center)
            if direction.length() > 0:
                self.direction = direction.normalize()
            return True

    def move(self, dt):
        # No moverse durante la animación de ataque
        if self.is_attacking:
            return
            
        # Mover según la dirección actual
        if self.direction.length() > 0:
            movement = self.direction * self.speed * dt
            
            # Mover en X
            self.rect.x += movement.x
            self.check_collision('horizontal')
            
            # Mover en Y
            self.rect.y += movement.y
            self.check_collision('vertical')
            
            # Actualizar hitbox
            self.hitbox_rect.center = self.rect.center

    def check_collision(self, direction):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.rect):
                if direction == 'horizontal':
                    if self.direction.x > 0:  # Moviendo a la derecha
                        self.rect.right = sprite.rect.left
                    elif self.direction.x < 0:  # Moviendo a la izquierda
                        self.rect.left = sprite.rect.right
                else:  # Vertical
                    if self.direction.y > 0:  # Moviendo abajo
                        self.rect.bottom = sprite.rect.top
                    elif self.direction.y < 0:  # Moviendo arriba
                        self.rect.top = sprite.rect.bottom

    def destroy(self):
        self.death_time = pygame.time.get_ticks()
        surf = pygame.mask.from_surface(self.frames[0]).to_surface()
        surf.set_colorkey('black')
        self.image = surf

    def death_timer(self):
        if pygame.time.get_ticks() - self.death_time >= 400:
            self.kill()

    def debug_draw(self):
        """Método para dibujar información de depuración"""
        if not self.debug_mode:
            return
            
        # Dibujar dirección como una línea
        if self.direction.length() > 0:
            pygame.draw.line(
                self.surface,
                (255, 0, 0),  # Color rojo
                self.rect.center,
                (self.rect.centerx + self.direction.x * 50, 
                 self.rect.centery + self.direction.y * 50),
                2  # Grosor de línea
            )
            
        # Dibujar rango de ataque
        pygame.draw.circle(
            self.surface,
            (255, 255, 0),  # Color amarillo
            self.rect.center,
            self.attack_range,
            1  # Solo contorno
        )

    def update(self, dt):
        if self.death_time == 0:
            # Ejecutar el árbol de comportamiento
            self.behavior_tree.run()
            self.move(dt)  # Usar dt para movimiento suave
            self.animate(dt)
            self.debug_draw()  # Dibujar información de depuración
        else:
            self.death_timer()