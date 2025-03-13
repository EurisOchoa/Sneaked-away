from settings import *
from player import Player
from sprites import *
from pytmx.util_pygame import load_pygame
from groups import AllSprites
from behavior_tree import Selector, Sequence, Action
from astar import astar_pathfinding
from random import randint, choice


class Game:
    def __init__(self):
        # setup
        pygame.init()
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Sneaked-away')
        self.clock = pygame.time.Clock()
        self.running = True

        # Inicializar joysticks
        pygame.joystick.init()
        self.setup_joysticks()

        # Inicializar grilla del mapa con más claridad
        self.grid_rows = GRID_ROWS
        self.grid_cols = GRID_COLS
        print(f"Inicializando grid de {self.grid_rows} filas x {self.grid_cols} columnas")
        self.grid = [[0 for _ in range(self.grid_cols)] for _ in range(self.grid_rows)]

        # groups
        self.all_sprites = AllSprites()
        self.collision_sprites = pygame.sprite.Group()
        self.bullet_sprites = pygame.sprite.Group()
        self.enemy_sprites = pygame.sprite.Group()

        # Contador de enemigos eliminados
        self.enemies_killed = 0
        self.enemies_to_win = 50  # Cantidad de enemigos para ganar
        self.victory = False

        # Más inicialización
        self.can_shoot = True
        self.shoot_time = 0
        self.gun_cooldown = 100
        self.enemy_event = pygame.event.custom_type()
        pygame.time.set_timer(self.enemy_event, 300)
        self.spawn_positions = []

        # audio
        self.shoot_sound = pygame.mixer.Sound(join('audio', 'shoot.wav'))
        self.shoot_sound.set_volume(0.2)
        self.impact_sound = pygame.mixer.Sound(join('audio', 'impact.ogg'))
        self.music = pygame.mixer.Sound(join('audio', 'music.wav'))
        self.music.set_volume(0.5)
        # self.music.play(loops = -1)

        # setup
        self.load_images()
        self.setup()
        
        # Imprimir información sobre la grilla después de cargarla
        self.print_grid_summary()

    def setup_joysticks(self):
        """Configurar joysticks conectados"""
        self.joysticks = []
        
        # Mostrar información sobre joysticks conectados
        joystick_count = pygame.joystick.get_count()
        print(f"Joysticks conectados: {joystick_count}")
        
        for i in range(joystick_count):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()
            
            # Imprimir info del joystick
            print(f"Joystick {i}: {joystick.get_name()}")
            print(f"  - Ejes: {joystick.get_numaxes()}")
            print(f"  - Botones: {joystick.get_numbuttons()}")
            
            self.joysticks.append(joystick)

    def print_grid_summary(self):
        """Imprime un resumen de la grilla para depuración"""
        obstacle_count = sum(row.count(1) for row in self.grid)
        total_cells = self.grid_rows * self.grid_cols
        print(f"Resumen de la grilla:")
        print(f"- Tamaño: {self.grid_rows} x {self.grid_cols} = {total_cells} celdas")
        print(f"- Obstáculos: {obstacle_count} ({obstacle_count/total_cells*100:.1f}%)")
        print(f"- Celdas transitables: {total_cells - obstacle_count} ({(total_cells-obstacle_count)/total_cells*100:.1f}%)")

    def load_images(self):
        self.bullet_surf = pygame.image.load(join('images', 'gun', 'bullet.png')).convert_alpha()

        folders = list(walk(join('images', 'enemies')))[0][1]
        self.enemy_frames = {}
        for folder in folders:
            for folder_path, _, file_names in walk(join('images', 'enemies', folder)):
                self.enemy_frames[folder] = []
                for file_name in sorted(file_names, key=lambda name: int(name.split('.')[0])):
                    full_path = join(folder_path, file_name)
                    surf = pygame.image.load(full_path).convert_alpha()
                    self.enemy_frames[folder].append(surf)

    def input(self):
        # Detectar disparos desde teclado o joystick
        if self.can_shoot:
            # Detectar disparo con mouse (click izquierdo)
            if pygame.mouse.get_pressed()[0]:
                self.shoot()
                
            # Detectar disparo con joystick (botón R2/RT o A/X)
            if pygame.joystick.get_count() > 0:
                joystick = pygame.joystick.Joystick(0)
                
                # Disparar con diferentes botones (pueden variar según el control)
                trigger_button = joystick.get_button(5)  # RT/R2 (puede variar)
                x_button = joystick.get_button(0)  # A en Xbox, X en PlayStation
                
                if trigger_button or x_button:
                    self.shoot()
    
    def shoot(self):
        """Método para disparar"""
        self.shoot_sound.play()
        pos = self.gun.rect.center + self.gun.player_direction * 50
        Bullet(self.bullet_surf, pos, self.gun.player_direction, (self.all_sprites, self.bullet_sprites))
        self.can_shoot = False
        self.shoot_time = pygame.time.get_ticks()

    def gun_timer(self):
        if not self.can_shoot:
            current_time = pygame.time.get_ticks()
            if current_time - self.shoot_time >= self.gun_cooldown:
                self.can_shoot = True

    def setup(self):
        map = load_pygame(join('data', 'maps', 'world.tmx'))

        for x, y, image in map.get_layer_by_name('Ground').tiles():
            Sprite((x * TILE_SIZE, y * TILE_SIZE), image, self.all_sprites)

        for obj in map.get_layer_by_name('Objects'):
            CollisionSprite((obj.x, obj.y), obj.image, (self.all_sprites, self.collision_sprites))
            
        # Marcar objetos de colisión en la grilla con más verificaciones
        collision_count = 0
        for obj in map.get_layer_by_name('Collisions'):
            grid_x, grid_y = int(obj.x // TILE_SIZE), int(obj.y // TILE_SIZE)
            if 0 <= grid_y < self.grid_rows and 0 <= grid_x < self.grid_cols:
                self.grid[grid_y][grid_x] = 1  # Marca la celda como obstáculo
                collision_count += 1
            else:
                print(f"ADVERTENCIA: Objeto de colisión fuera de rango en ({grid_x}, {grid_y})")
        
        print(f"Se marcaron {collision_count} celdas como obstáculos")

        for obj in map.get_layer_by_name('Entities'):
            if obj.name == 'Player':
                self.player = Player((obj.x, obj.y), self.all_sprites, self.collision_sprites)
                self.gun = Gun(self.player, self.all_sprites)
                
                # Registrar posición del jugador en coordenadas de grid
                player_grid_x = int(obj.x // TILE_SIZE)
                player_grid_y = int(obj.y // TILE_SIZE)
                print(f"Jugador inicializado en posición mundial ({obj.x}, {obj.y})")
                print(f"Posición del jugador en grid: ({player_grid_x}, {player_grid_y})")
            elif obj.name == 'Enemy':
                # También registrar posiciones de spawn de enemigos
                self.spawn_positions.append((obj.x, obj.y))
                spawn_grid_x = int(obj.x // TILE_SIZE)
                spawn_grid_y = int(obj.y // TILE_SIZE)
                print(f"Posición de spawn de enemigos en grid: ({spawn_grid_x}, {spawn_grid_y})")

    def bullet_collision(self):
        if self.bullet_sprites:
            for bullet in self.bullet_sprites:
                collision_sprites = pygame.sprite.spritecollide(
                    bullet, self.enemy_sprites, False, pygame.sprite.collide_mask
                )
                if collision_sprites:
                    self.impact_sound.play()
                    for sprite in collision_sprites:
                        sprite.destroy()  # Asegúrate de que Enemy tenga el método destroy
                        self.enemies_killed += 1  # Incrementar contador de enemigos eliminados
                    bullet.kill()
                    
                    # Comprobar condición de victoria
                    if self.enemies_killed >= self.enemies_to_win:
                        self.victory = True

    def player_collision(self):
        # Si el jugador está en colisión con los enemigos
        if pygame.sprite.spritecollide(self.player, self.enemy_sprites, False, pygame.sprite.collide_mask):
            self.player.take_damage(2)  # Reducir vida del jugador gradualmente

    def handle_player_health(self):
        """Maneja la visualización de la salud del jugador"""
        if self.player.is_alive:
            # Dibujar la barra de salud
            self.player.draw_health_bar(self.display_surface)
            
            # Dibujar texto de salud en la esquina
            font = pygame.font.Font(None, 32)
            health_text = font.render(f"Salud: {self.player.health}", True, (255, 255, 255))
            self.display_surface.blit(health_text, (20, 20))
            
            # Mostrar contador de enemigos eliminados
            kill_text = font.render(f"Enemigos eliminados: {self.enemies_killed}/{self.enemies_to_win}", True, (255, 255, 255))
            self.display_surface.blit(kill_text, (20, 60))

    def draw_joystick_help(self):
        """Muestra información de ayuda sobre controles de joystick"""
        if pygame.joystick.get_count() > 0:
            font = pygame.font.Font(None, 24)
            help_text = [
                "Controles de Joystick:",
                "- Stick Izquierdo: Mover",
                "- Stick Derecho: Apuntar",
                "- A/X o RT/R2: Disparar"
            ]
            
            for i, text in enumerate(help_text):
                rendered = font.render(text, True, (200, 200, 200))
                self.display_surface.blit(rendered, (WINDOW_WIDTH - 250, 20 + i * 25))

    def game_over_screen(self, victory=False):
        # Pantalla de "Game Over" o "Victoria"
        font = pygame.font.Font(None, 74)
        small_font = pygame.font.Font(None, 50)

        # Textos
        if victory:
            main_text = font.render("¡VICTORIA!", True, (0, 255, 0))
            subtitle = small_font.render(f"Has eliminado {self.enemies_killed} enemigos", True, (255, 255, 255))
        else:
            main_text = font.render("GAME OVER", True, (255, 0, 0))
            subtitle = small_font.render(f"Eliminaste {self.enemies_killed} de {self.enemies_to_win} enemigos", True, (255, 255, 255))
        
        restart_text = small_font.render("Presiona R o A para reiniciar", True, (255, 255, 255))
        exit_text = small_font.render("Presiona Q o B para salir", True, (255, 255, 255))

        # Dibujar en pantalla
        self.display_surface.fill((0, 0, 0))  # Fondo negro
        self.display_surface.blit(main_text, (WINDOW_WIDTH // 2 - main_text.get_width() // 2, 150))
        self.display_surface.blit(subtitle, (WINDOW_WIDTH // 2 - subtitle.get_width() // 2, 250))
        self.display_surface.blit(restart_text, (WINDOW_WIDTH // 2 - restart_text.get_width() // 2, 350))
        self.display_surface.blit(exit_text, (WINDOW_WIDTH // 2 - exit_text.get_width() // 2, 450))
        pygame.display.update()

        # Esperar entrada del jugador
        waiting_for_input = True
        while waiting_for_input:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        return "restart"
                    if event.key == pygame.K_q:
                        pygame.quit()
                        exit()
                # Detectar input de joystick
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0:  # A en Xbox, X en PlayStation
                        return "restart"
                    if event.button == 1:  # B en Xbox, Círculo en PlayStation
                        pygame.quit()
                        exit()

    def restart_game(self):
        # Reiniciar el juego por completo
        self.__init__()
        self.run()

    def render_grid_overlay(self):
        """Dibuja una representación visual de la grid para depuración"""
        for y in range(self.grid_rows):
            for x in range(self.grid_cols):
                rect = pygame.Rect(
                    x * TILE_SIZE + self.all_sprites.offset.x,
                    y * TILE_SIZE + self.all_sprites.offset.y,
                    TILE_SIZE, TILE_SIZE
                )
                
                # Dibujar celdas de diferentes colores según su contenido
                if self.grid[y][x] == 1:  # Obstáculo
                    pygame.draw.rect(self.display_surface, (255, 0, 0, 100), rect, 1)
                else:  # Celda transitable
                    pygame.draw.rect(self.display_surface, (0, 255, 0, 100), rect, 1)

    def create_enemy(self):
        """Crea un nuevo enemigo en una posición de spawn aleatoria"""
        if self.spawn_positions and not self.victory and self.player.is_alive:
            pos = choice(self.spawn_positions)
            enemy_type = choice(list(self.enemy_frames.keys()))
            
            # Crear árbol de comportamiento para el enemigo
            pathfind_sequence = Sequence([
                Action(lambda e: self.calculate_path(e)),
                Action(lambda e: e.follow_path())
            ])
            
            chase_action = Action(lambda e: e.chase_player(self.player))
            behavior_tree = Selector([pathfind_sequence, chase_action])
            
            # Crear el enemigo con el árbol de comportamiento
            Enemy(
                pos,
                self.enemy_frames[enemy_type],
                (self.all_sprites, self.enemy_sprites),
                self.player,
                self.collision_sprites,
                self.grid
            )

    def calculate_path(self, enemy):
        """Calcula un camino desde el enemigo hasta el jugador usando A*"""
        # Convertir posiciones a coordenadas de grid
        start_x, start_y = int(enemy.pos.x // TILE_SIZE), int(enemy.pos.y // TILE_SIZE)
        goal_x, goal_y = int(self.player.pos.x // TILE_SIZE), int(self.player.pos.y // TILE_SIZE)
        
        # Verificar límites
        if (0 <= start_y < self.grid_rows and 0 <= start_x < self.grid_cols and
            0 <= goal_y < self.grid_rows and 0 <= goal_x < self.grid_cols):
            
            # Calcular camino usando A*
            path = astar_pathfinding((start_x, start_y), (goal_x, goal_y), self.grid)
            
            if path:
                # Convertir coordenadas de grid a coordenadas del mundo
                world_path = [(x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2) 
                             for x, y in path]
                enemy.path = world_path
                return True
        
        # Si no se pudo calcular un camino
        enemy.path = []
        return
    
    def run(self):
        """Bucle principal del juego"""
        while self.running:
            # Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == self.enemy_event:
                    self.create_enemy()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
            
            # Verificar si el juego ha terminado
            if not self.player.is_alive:
                result = self.game_over_screen(victory=False)
                if result == "restart":
                    self.restart_game()
                    return
            
            if self.victory:
                result = self.game_over_screen(victory=True)
                if result == "restart":
                    self.restart_game()
                    return
            
            # Input y actualizaciones
            dt = self.clock.tick() / 1000
            self.input()
            self.gun_timer()
            self.all_sprites.update(dt)
            self.bullet_collision()
            self.player_collision()
            
            # Renderizado
            self.display_surface.fill('black')
            # CORRECCIÓN: Pasar la posición del jugador en lugar del objeto jugador
            self.all_sprites.draw(self.player.rect.center)
            
            # Interfaz de usuario
            self.handle_player_health()
            
            pygame.display.update()


# Punto de entrada para iniciar el juego
if __name__ == "__main__":
    game = Game()
    game.run()