"""SI unit conversions and constants.

Convention: internally everything is in SI (N, m, Pa, N/m, N*m).
These helpers are intended for the API/UI boundary only.
"""

G = 9.81  # m/s^2, standard gravity

# Length
def mm_to_m(x: float) -> float: return x * 1e-3
def cm_to_m(x: float) -> float: return x * 1e-2
def m_to_mm(x: float) -> float: return x * 1e3
def m_to_cm(x: float) -> float: return x * 1e2

# Stress / modulus
def mpa_to_pa(x: float) -> float: return x * 1e6
def gpa_to_pa(x: float) -> float: return x * 1e9
def pa_to_mpa(x: float) -> float: return x * 1e-6
def pa_to_gpa(x: float) -> float: return x * 1e-9

# Force
def kn_to_n(x: float) -> float: return x * 1e3
def n_to_kn(x: float) -> float: return x * 1e-3
def kgf_to_n(x: float) -> float: return x * G
def n_to_kgf(x: float) -> float: return x / G

# Distributed load (line)
def kn_per_m_to_n_per_m(x: float) -> float: return x * 1e3
def n_per_m_to_kn_per_m(x: float) -> float: return x * 1e-3
