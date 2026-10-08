def _unwrap(q):
    # ProjectQ accepts a one-qubit Qureg in places where a qubit is expected.
    if isinstance(q, (list, tuple)) and len(q) == 1:
        return q[0]
    return q


class _Gate:
    def __or__(self, operands):
        if isinstance(operands, tuple):
            qubits = [_unwrap(q) for q in operands]
        else:
            qubits = [_unwrap(operands)]
        if not qubits:
            return
        eng = qubits[0].engine
        for q in qubits:
            if q.engine is not eng:
                raise ValueError("mixed engines")
        eng._apply(self, qubits)


class XGate(_Gate):
    pass


class CNOTGate(_Gate):
    pass


class ToffoliGate(_Gate):
    pass


X = XGate()
CNOT = CNOTGate()
Toffoli = ToffoliGate()
