// brisa_ic.h — Índice de calor (NWS/NOAA) e faixas de risco, versão C++ para o ESP32.
// Mesmo algoritmo de src/brisa/indice_calor.py (testado em tests/test_esp32_formula.py).
#pragma once
#include <math.h>

static inline float brisa_c_para_f(float c) { return c * 9.0f / 5.0f + 32.0f; }
static inline float brisa_f_para_c(float f) { return (f - 32.0f) * 5.0f / 9.0f; }

// Retorna o índice de calor em °C a partir de temperatura (°C) e umidade relativa (%).
static inline float brisa_indice_calor(float temp_c, float ur) {
  float t = brisa_c_para_f(temp_c);
  float simples = 0.5f * (t + 61.0f + (t - 68.0f) * 1.2f + ur * 0.094f);
  if ((simples + t) / 2.0f < 80.0f) return brisa_f_para_c(simples);

  float ic = -42.379f + 2.04901523f * t + 10.14333127f * ur
             - 0.22475541f * t * ur - 0.00683783f * t * t
             - 0.05481717f * ur * ur + 0.00122874f * t * t * ur
             + 0.00085282f * t * ur * ur - 0.00000199f * t * t * ur * ur;

  if (ur < 13.0f && t >= 80.0f && t <= 112.0f) {
    ic -= ((13.0f - ur) / 4.0f) * sqrtf((17.0f - fabsf(t - 95.0f)) / 17.0f);
  } else if (ur > 85.0f && t >= 80.0f && t <= 87.0f) {
    ic += ((ur - 85.0f) / 10.0f) * ((87.0f - t) / 5.0f);
  }
  return brisa_f_para_c(ic);
}

// 0 = Normal, 1 = Cautela, 2 = Cautela extrema, 3 = Perigo, 4 = Perigo extremo
static inline int brisa_nivel(float ic_c) {
  if (ic_c < 26.7f) return 0;
  if (ic_c < 32.2f) return 1;
  if (ic_c < 39.4f) return 2;
  if (ic_c < 51.7f) return 3;
  return 4;
}

static inline const char* brisa_categoria(int nivel) {
  static const char* nomes[] = {"Normal", "Cautela", "Cautela extrema", "Perigo", "Perigo extremo"};
  return nomes[nivel < 0 ? 0 : (nivel > 4 ? 4 : nivel)];
}
