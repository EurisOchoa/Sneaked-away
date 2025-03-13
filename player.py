from settings import * 

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, collision_sprites):
        super().__init__(groups)
        self.load_images()
        self.state, self.frame_index = 'right', 0
        self.image = pygame.image.load(join('images', 'player', 'down', '0.png')).convert_alpha()
        self.rect = self.image.get_rect(center=pos)
        self.hitbox_rect = self.rect.inflate(-60, -90)

        # Vector de posición para rastreo preciso
        self.pos = pygame.Vector2(pos)

        # Movement
        self.direction = pygame.Vector2()
        self.speed = 500
        self.collision_sprites = collision_sprites

        # Health system
        self.max_health = 100
        self.health = self.max_health  # Vida inicial del jugador
        self.is_alive = True  # Indica si el jugador está vivo
        self.hit_time = 0  # Tiempo del último daño recibido
        self.invulnerable_duration = 500  # Milisegundos de invulnerabilidad después de recibir daño
        self.is_invulnerable = False  # Estado de invulnerabilidad
        self.damage_display_time = 0  # Para mostrar el daño recibido
        self.last_damage_amount = 0  # Última cantidad de daño recibido
        
    def load_images(self):
        self.frames = {'left': [], 'right': [], 'up': [], 'down': []}

        for state in self.frames.keys():
            for folder_path, sub_folders, file_names in walk(join('images', 'player', state)):
                if file_names:
                    for file_name in sorted(file_names, key=lambda name: int(name.split('.')[0])):
                        full_path = join(folder_path, file_name)
                        surf = pygame.image.load(full_path).convert_alpha()
                        self.frames[state].append(surf)

    def input(self):
        # Reiniciar dirección
        self.direction = pygame.Vector2()
        
        # Buscar joysticks disponibles
        if pygame.joystick.get_count() > 0:
            joystick = pygame.joystick.Joystick(0)  # Usar el primer joystick
            
            # Leer los valores del stick izquierdo (movimiento)
            x_axis = joystick.get_axis(0)  # Eje X del stick izquierdo
            y_axis = joystick.get_axis(1)  # Eje Y del stick izquierdo
            
            # Aplicar zona muerta para evitar movimientos involuntarios
            if abs(x_axis) > JOYSTICK_DEADZONE:
                self.direction.x = x_axis
            if abs(y_axis) > JOYSTICK_DEADZONE:
                self.direction.y = y_axis
        else:
            # Input de teclado como fallback
            keys = pygame.key.get_pressed()
            self.direction.x = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
            self.direction.y = int(keys[pygame.K_DOWN] or keys[pygame.K_s]) - int(keys[pygame.K_UP] or keys[pygame.K_w])
        
        # Normalizar el vector de dirección si es necesario
        if self.direction.length() > 1:
            self.direction = self.direction.normalize()

    def move(self, dt):
        # Actualizar posición vectorial
        self.pos.x += self.direction.x * self.speed * dt
        self.pos.y += self.direction.y * self.speed * dt
        
        # Actualizar hitbox para colisiones
        self.hitbox_rect.centerx = round(self.pos.x)
        self.collision('horizontal')
        self.pos.x = self.hitbox_rect.centerx
        
        self.hitbox_rect.centery = round(self.pos.y)
        self.collision('vertical')
        self.pos.y = self.hitbox_rect.centery
        
        # Actualizar rect principal
        self.rect.center = self.hitbox_rect.center

    def collision(self, direction):
        for sprite in self.collision_sprites:
            if sprite.rect.colliderect(self.hitbox_rect):
                if direction == 'horizontal':
                    if self.direction.x > 0:
                        self.hitbox_rect.right = sprite.rect.left
                    if self.direction.x < 0:
                        self.hitbox_rect.left = sprite.rect.right
                else:
                    if self.direction.y < 0:
                        self.hitbox_rect.top = sprite.rect.bottom
                    if self.direction.y > 0:
                        self.hitbox_rect.bottom = sprite.rect.top

    def animate(self, dt):
        # Get state
        if self.direction.x != 0:
            self.state = 'right' if self.direction.x > 0 else 'left'
        if self.direction.y != 0:
            self.state = 'down' if self.direction.y > 0 else 'up'

        # Animate
        self.frame_index = self.frame_index + 5 * dt if self.direction.length() > 0 else 0
        
        # Obtener frame base
        base_image = self.frames[self.state][int(self.frame_index) % len(self.frames[self.state])]
        
        # Si estamos invulnerables, parpadear
        if self.is_invulnerable:
            current_time = pygame.time.get_ticks()
            if (current_time // 100) % 2:  # Parpadeo cada 100ms
                # Crear una versión más clara de la imagen
                alpha_img = base_image.copy()
                alpha_img.set_alpha(150)  # 150/255 de opacidad
                self.image = alpha_img
            else:
                self.image = base_image
        else:
            self.image = base_image

    def check_invulnerability(self):
        """Verifica y actualiza el estado de invulnerabilidad"""
        current_time = pygame.time.get_ticks()
        
        if self.is_invulnerable:
            if current_time - self.hit_time >= self.invulnerable_duration:
                self.is_invulnerable = False

    def take_damage(self, amount):
        """Método para que el jugador reciba daño"""
        current_time = pygame.time.get_ticks()
        
        # Solo recibir daño si no estamos invulnerables
        if self.is_alive and not self.is_invulnerable:
            self.health -= amount
            self.hit_time = current_time
            self.is_invulnerable = True
            self.damage_display_time = current_time
            self.last_damage_amount = amount
            
            print(f"Jugador recibió {amount} de daño. Salud restante: {self.health}")
            
            # Comprobar si el jugador ha muerto
            if self.health <= 0:
                self.health = 0
                self.is_alive = False
                print("Game Over - Jugador ha muerto")
    
    def draw_health_bar(self, surface):
        """Dibuja una barra de salud sobre el jugador"""
        if self.health < self.max_health:
            x, y = self.rect.centerx, self.rect.top - 10
            width, height = 50, 5
            
            # Fondo de la barra (rojo)
            pygame.draw.rect(surface, (255, 0, 0), (x - width//2, y, width, height))
            
            # Parte llena de la barra (verde)
            fill_width = int((self.health / self.max_health) * width)
            pygame.draw.rect(surface, (0, 255, 0), (x - width//2, y, fill_width, height))
            
            # Borde de la barra
            pygame.draw.rect(surface, (0, 0, 0), (x - width//2, y, width, height), 1)
            
            # Mostrar el daño recibido
            current_time = pygame.time.get_ticks()
            if current_time - self.damage_display_time < 1000:  # Mostrar por 1 segundo
                font = pygame.font.Font(None, 24)
                damage_text = font.render(f"-{self.last_damage_amount}", True, (255, 0, 0))
                surface.blit(damage_text, (x + 30, y - 20))
    
    def update(self, dt):
        self.input()
        self.move(dt)
        self.animate(dt)
        self.check_invulnerability()