class Node:
    """Nodo base del árbol de comportamiento."""
    def run(self):
        raise NotImplementedError("Este método debe implementarse en nodos específicos.")

class Selector(Node):
    """Intenta ejecutar los hijos hasta que uno tenga éxito."""
    def __init__(self, children):
        self.children = children

    def run(self):
        for child in self.children:
            if child.run():
                return True
        return False

class Sequence(Node):
    """Ejecuta los hijos en orden hasta que uno falle."""
    def __init__(self, children):
        self.children = children

    def run(self):
        for child in self.children:
            if not child.run():
                return False
        return True

class Action(Node):
    """Ejecuta una acción específica."""
    def __init__(self, function):
        self.function = function

    def run(self):
        return self.function()

class Condition(Node):
    """Evalúa una condición."""
    def __init__(self, function):
        self.function = function

    def run(self):
        return self.function()

class Inverter(Node):
    """Invierte el resultado del nodo hijo."""
    def __init__(self, child):
        self.child = child

    def run(self):
        return not self.child.run()

class Repeater(Node):
    """Repite el nodo hijo un número específico de veces."""
    def __init__(self, child, count=None):
        self.child = child
        self.count = count

    def run(self):
        if self.count is None:
            # Repetir infinitamente
            while True:
                self.child.run()
        else:
            # Repetir un número específico de veces
            for _ in range(self.count):
                self.child.run()
        return True