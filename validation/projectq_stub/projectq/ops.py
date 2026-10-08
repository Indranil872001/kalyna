class _Gate:
    def __or__(self, operands):
        if isinstance(operands, tuple):
            qubits = list(operands)
        else:
            qubits = [operands]
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
