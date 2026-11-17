/*
  Brisa — nó sensor de sala de aula (ESP32 + DHT22)
  FIAP Global Solution 2026.2 — CitizenTech

  O que faz:
   - Lê temperatura e umidade do DHT22 a cada INTERVALO_MS.
   - Calcula o índice de calor (mesma fórmula do backend Python).
   - Indica a faixa de risco no próprio ambiente:
       LED verde    = Normal / Cautela
       LED amarelo  = Cautela extrema
       LED vermelho = Perigo ou pior (+ bipe curto no buzzer)
   - Envia uma linha JSON pela Serial, no formato que o backend ingere:
       {"dispositivo":"brisa-sala-21","ts":"2025-02-17T10:20:00","temp":31.4,"umid":62.0,"ic":36.2,"cat":"Cautela extrema"}

  Simulação: wokwi.com (diagram.json nesta pasta). Rede "Wokwi-GUEST" + NTP para o horário.
  Para usar no backend: copie as linhas do Serial Monitor para um arquivo .jsonl e importe
  pela opção 3 do menu (python src/main.py menu).
*/
#include <WiFi.h>
#include <time.h>
#include "DHTesp.h"
#include "brisa_ic.h"

#define PINO_DHT       15
#define LED_VERDE      25
#define LED_AMARELO    26
#define LED_VERMELHO   27
#define PINO_BUZZER    14

const char* DISPOSITIVO = "brisa-sala-21";   // deve existir na tabela 'ambientes'
const char* WIFI_SSID   = "Wokwi-GUEST";
const char* WIFI_SENHA  = "";
const long  FUSO_SEG    = -3 * 3600;          // America/Sao_Paulo
const unsigned long INTERVALO_MS = 5000;      // 5 s na simulação (10 min em produção)

DHTesp dht;
bool relogioOk = false;
unsigned long ultimaLeitura = 0;

void conectarWiFiERelogio() {
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  Serial.print("# Conectando ao Wi-Fi");
  for (int i = 0; i < 20 && WiFi.status() != WL_CONNECTED; i++) {
    delay(250);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    configTime(FUSO_SEG, 0, "pool.ntp.org");
    struct tm info;
    relogioOk = getLocalTime(&info, 5000);
  }
  Serial.println(relogioOk ? "# Relogio sincronizado via NTP" : "# Sem NTP: leituras sem horario serao descartadas pelo backend");
}

void indicar(int nivel) {
  digitalWrite(LED_VERDE,    nivel <= 1);
  digitalWrite(LED_AMARELO,  nivel == 2);
  digitalWrite(LED_VERMELHO, nivel >= 3);
  if (nivel >= 3) tone(PINO_BUZZER, 2000, 150);
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_AMARELO, OUTPUT);
  pinMode(LED_VERMELHO, OUTPUT);
  pinMode(PINO_BUZZER, OUTPUT);
  dht.setup(PINO_DHT, DHTesp::DHT22);
  conectarWiFiERelogio();
}

void loop() {
  if (millis() - ultimaLeitura < INTERVALO_MS) return;
  ultimaLeitura = millis();

  TempAndHumidity leitura = dht.getTempAndHumidity();
  if (dht.getStatus() != DHTesp::ERROR_NONE || isnan(leitura.temperature) || isnan(leitura.humidity)) {
    Serial.printf("# Erro de leitura do DHT22: %s\n", dht.getStatusString());
    return;  // nunca envia leitura inválida
  }

  float ic = brisa_indice_calor(leitura.temperature, leitura.humidity);
  int nivel = brisa_nivel(ic);
  indicar(nivel);

  char ts[25] = "";
  struct tm info;
  if (relogioOk && getLocalTime(&info, 100)) {
    strftime(ts, sizeof(ts), "%Y-%m-%dT%H:%M:%S", &info);
  }

  Serial.printf("{\"dispositivo\":\"%s\",\"ts\":\"%s\",\"temp\":%.1f,\"umid\":%.1f,\"ic\":%.1f,\"cat\":\"%s\"}\n",
                DISPOSITIVO, ts, leitura.temperature, leitura.humidity, ic, brisa_categoria(nivel));
}
