from sympy import gcd, isprime, sqrt_mod
from sympy.ntheory.modular import crt


def find_factors_via_sqrt(n, x):
    # Berechne c = x^2 mod n
    c = pow(x, 2, n)

    # Suchen nach möglichen Primfaktoren p und q
    for p in range(2, int(n**0.5) + 1):
        if n % p == 0 and isprime(p):
            q = n // p
            if isprime(q):
                break
    else:
        return "n ist kein Produkt zweier Primzahlen."

    # Berechnung der Quadratwurzeln
    roots_p = sqrt_mod(c, p, all_roots=True)
    roots_q = sqrt_mod(c, q, all_roots=True)

    # Kombination der Lösungen mittels CRT
    solutions = []
    for r_p in roots_p:
        for r_q in roots_q:
            y = crt([p, q], [r_p, r_q])[0]
            solutions.append(y)

    # Ergebnisse anzeigen
    solutions = list(set(solutions))  # Duplikate entfernen
    return sorted(solutions), (p, q)


# Beispiel mit n = 25777 und x = 13013
n = 25777
x = 13013
solutions, factors = find_factors_via_sqrt(n, x)
print(f"Quadratwurzeln modulo {n}: {solutions}")
print(f"Primfaktoren von {n}: {factors}")
