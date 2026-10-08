from . import ops


class Qubit:
    __slots__ = ("engine", "id")
    def __init__(self, engine, qid):
        self.engine = engine
        self.id = qid


class _Command:
    __slots__ = ("gate", "all_qubits")
    def __init__(self, gate, qubits):
        self.gate = gate
        self.all_qubits = (tuple(qubits),)


class MainEngine:
    """
    Tiny ProjectQ-compatible engine sufficient for X/CNOT/Toffoli dependency
    depth accounting used by the Kalyna scripts. It is not a simulator.
    """
    def __init__(self, backend):
        self.backend = backend
        self.backend.main_engine = self
        self._next_id = 0

    def allocate_qubit(self):
        q = Qubit(self, self._next_id)
        self._next_id += 1
        # Match ProjectQ's one-element qureg return convention.
        return [q]

    def allocate_qureg(self, n):
        out = [Qubit(self, self._next_id + i) for i in range(n)]
        self._next_id += n
        return out

    def _apply(self, gate, qubits):
        self.backend.receive([_Command(gate, qubits)])

    def flush(self):
        return None
