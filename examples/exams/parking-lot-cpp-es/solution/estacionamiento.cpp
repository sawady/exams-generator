// Estacionamiento — solución de referencia, ejercicios 1 a 3 (examen de ejemplo inventado).
#include "estacionamiento.h"

#include <algorithm>
#include <stdexcept>
#include <utility>

// Dados en el enunciado.
Estacionamiento::Estacionamiento(int capacidad, int tarifaPorHora)
    : capacidad_(capacidad), tarifa_(tarifaPorHora), recaudado_(0) {}

int Estacionamiento::capacidad() const { return capacidad_; }
int Estacionamiento::ocupados() const { return static_cast<int>(entradas_.size()); }
bool Estacionamiento::estaAdentro(const Patente& p) const { return entradas_.count(p) > 0; }
int Estacionamiento::recaudado() const { return recaudado_; }

/* ------------------------------------------------------------------
 * Ejercicio 1
 * ------------------------------------------------------------------ */

// Rechazar antes de tocar el map mantiene ocupados() <= capacidad().
bool Estacionamiento::ingresar(const Patente& p, Minuto ahora) {
    if (ocupados() == capacidad_ || estaAdentro(p)) {
        return false;
    }
    entradas_[p] = ahora;
    return true;
}

// Horas iniciadas, con un mínimo de una: ceil(minutos / 60), y 1 si son 0 minutos.
int Estacionamiento::retirar(const Patente& p, Minuto ahora) {
    auto it = entradas_.find(p);
    if (it == entradas_.end()) {
        throw std::out_of_range("la patente no está adentro: " + p);
    }
    int minutos = ahora - it->second;
    int horas = std::max(1, (minutos + 59) / 60);
    int importe = horas * tarifa_;
    entradas_.erase(it);
    recaudado_ += importe;
    return importe;
}

/* ------------------------------------------------------------------
 * Ejercicio 2 (respuesta de papel)
 * ------------------------------------------------------------------
 *
 * Invariantes de representación:
 *   1. capacidad_ > 0 y tarifa_ > 0.
 *   2. entradas_.size() <= capacidad_.
 *   3. recaudado_ >= 0 y es múltiplo de tarifa_ (cada cobro son horas * tarifa_).
 *
 * Los establece el constructor (1 por su precondición, 2 y 3 porque arranca
 * vacío y sin recaudación). Sólo ingresar podría romper 2: chequea la
 * capacidad antes de insertar. Sólo retirar modifica recaudado_, y suma un
 * múltiplo positivo de tarifa_. Como los campos son privados, ningún código
 * cliente puede romperlos.
 */

/* ------------------------------------------------------------------
 * Ejercicio 3
 * ------------------------------------------------------------------
 *
 * Costo: O(N log N), N = ocupados(). Copiar el map a un vector es O(N),
 * ordenarlo es O(N log N) y copiar las primeras k patentes es O(k), con k <= N
 * después de acotarlo. (Con std::partial_sort bajaría a O(N log k).)
 */
std::vector<Patente> Estacionamiento::masAntiguos(int k) const {
    std::vector<std::pair<Minuto, Patente>> autos;
    autos.reserve(entradas_.size());
    for (const auto& [patente, entrada] : entradas_) {
        autos.emplace_back(entrada, patente);
    }
    // Los pares se comparan por minuto y, si empatan, por patente.
    std::sort(autos.begin(), autos.end());

    std::size_t cuantos = std::min(autos.size(), static_cast<std::size_t>(std::max(k, 0)));
    std::vector<Patente> resultado;
    resultado.reserve(cuantos);
    for (std::size_t i = 0; i < cuantos; i++) {
        resultado.push_back(autos[i].second);
    }
    return resultado;
}

/* Demo:
 *   Estacionamiento e(2, 100);
 *   e.ingresar("AB123CD", 0)   == true
 *   e.ingresar("AB123CD", 5)   == false   (ya está adentro)
 *   e.ingresar("XY987ZW", 10)  == true
 *   e.ingresar("JK555LM", 20)  == false   (lleno)
 *   e.masAntiguos(5)           == {"AB123CD", "XY987ZW"}
 *   e.retirar("AB123CD", 61)   == 200     (61 minutos: dos horas iniciadas)
 *   e.retirar("XY987ZW", 10)   == 100     (caso de borde: 0 minutos paga una hora)
 *   e.recaudado()              == 300
 *   e.retirar("XY987ZW", 20)   lanza std::out_of_range
 */
