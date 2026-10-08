class BasicEngine:
    """Minimal compatibility base for the manuscript's custom depth backend."""
    def __init__(self):
        self.main_engine = None

    def is_available(self, cmd):
        return True

    def receive(self, command_list):
        raise NotImplementedError
