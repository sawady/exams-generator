// Estacionamiento — solución de referencia: la clase (examen de ejemplo inventado).
#pragma once

#include <string>
#include <unordered_map>
#include <vector>

using Patente = std::string;
using Minuto = int;

class Estacionamiento {
public:
    // Precondición: capacidad > 0 y tarifaPorHora > 0.
    Estacionamiento(int capacidad, int tarifaPorHora);

    int capacidad() const;
    int ocupados() const;
    bool estaAdentro(const Patente& p) const;
    int recaudado() const;

    // Ejercicio 1.
    bool ingresar(const Patente& p, Minuto ahora);
    int retirar(const Patente& p, Minuto ahora);

    // Ejercicio 3.
    std::vector<Patente> masAntiguos(int k) const;

private:
    int capacidad_;
    int tarifa_;
    std::unordered_map<Patente, Minuto> entradas_;  // patente -> minuto de entrada
    int recaudado_;
};
