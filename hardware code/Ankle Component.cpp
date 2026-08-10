#include <esp_now.h>
#include <WiFi.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

Adafruit_MPU6050 mpu;

// REPLACE WITH YOUR RECEIVER MAC ADDRESS
uint8_t receiverAddress[] = {0x5C, 0x01, 0x3B, 0xBF, 0x3A, 0x4C};

// message struct for sending "step_taken"
typedef struct struct_message {
    bool step_taken;
} struct_message;

struct_message sensorData;
esp_now_peer_info_t peerInfo;

volatile bool dataSent = false;
volatile bool sendSuccess = false;

// --- Toggle this to turn all debug prints on/off in one place ---
#define DEBUG_SERIAL true

// --- Core thresholding parameters ---
const float threshold_sensitivity = 0.5;    // Trigger at 0.5x the peak EMA
const float baseline_floor = 20.0;          // Min m/s^2 to ignore

float alpha_attack = 0.4;   // Fast: threshold rises when a new max accel is detected
float alpha_release = 0.05; // Slow: threshold falls so one weak step doesn't collapse it

unsigned long stop_timeout = 2000; // wait 2 seconds before we say the user stopped running

// --- Cadence-adaptive skip period ---
float skip_period_fraction = 0.4; // ignore steps faster than 0.4x the recent cadence
unsigned long min_skip_period = 150;
unsigned long max_skip_period = 500;

// --- State ---
float peak_ema = 0.0;
float active_threshold = 20.0;
unsigned long last_step_time = 0;
unsigned long skip_period = 250; // starting value, adapts once steps come in

const int interval_history = 4;
unsigned long step_intervals[interval_history] = {0};
int interval_index = 0;
bool interval_buffer_full = false;

// --- Debug print timing (separate from main loop rate so Serial doesn't flood) ---
unsigned long last_debug_print = 0;
const unsigned long debug_print_interval = 100; // ms between debug lines

void updateSkipPeriod(unsigned long new_interval) {
    if (new_interval == 0 || new_interval > 2000) return;

    step_intervals[interval_index] = new_interval;
    interval_index = (interval_index + 1) % interval_history;
    if (interval_index == 0) interval_buffer_full = true;

    int count = interval_buffer_full ? interval_history : interval_index;
    if (count == 0) return;

    unsigned long sum = 0;
    for (int i = 0; i < count; i++) sum += step_intervals[i];
    float avg_interval = (float)sum / count;

    unsigned long new_skip = (unsigned long)(avg_interval * skip_period_fraction);
    if (new_skip < min_skip_period) new_skip = min_skip_period;
    if (new_skip > max_skip_period) new_skip = max_skip_period;
    skip_period = new_skip;
}

void onDataSent(const wifi_tx_info_t *tx_info, esp_now_send_status_t status) {
    dataSent = true;
    sendSuccess = (status == ESP_NOW_SEND_SUCCESS);
}

void setup() {
    Serial.begin(115200);
    while (!Serial);

    pinMode(2, OUTPUT);
    digitalWrite(2, LOW);

    Wire.begin(21, 22);
    if (!mpu.begin()) {
        Serial.println("Failed to find MPU6050 chip");
        while (1) { delay(10); }
    }

    WiFi.mode(WIFI_STA);
    if (esp_now_init() != ESP_OK) {
        Serial.println("Error initializing ESP-NOW");
        return;
    }

    esp_now_register_send_cb(onDataSent);

    memcpy(peerInfo.peer_addr, receiverAddress, 6);
    peerInfo.channel = 0;
    peerInfo.encrypt = false;
    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
        Serial.println("Failed to add peer");
        return;
    }

    active_threshold = baseline_floor;
    peak_ema = baseline_floor / threshold_sensitivity;

    Serial.println("--- Step Detection Initialized ---");
    if (DEBUG_SERIAL) {
        Serial.println("time_ms,A_sq,active_threshold,peak_ema,skip_period,step_fired");
    }
}

void loop() {
    unsigned long now = millis();
    sensors_event_t a, g, temp;
    bool step_fired = false;

    if (mpu.getEvent(&a, &g, &temp)) {
        float A_sq = sqrt(sq(a.acceleration.x) + sq(a.acceleration.y) + sq(a.acceleration.z));

        if (now - last_step_time > stop_timeout) {
            active_threshold = baseline_floor;
            peak_ema = baseline_floor / threshold_sensitivity;
        }

        if (A_sq > active_threshold && (now - last_step_time > skip_period)) {
            unsigned long interval = last_step_time == 0 ? 0 : (now - last_step_time);
            last_step_time = now;
            step_fired = true;

            if (A_sq > peak_ema) {
                peak_ema = alpha_attack * A_sq + (1 - alpha_attack) * peak_ema;
            } else {
                peak_ema = alpha_release * A_sq + (1 - alpha_release) * peak_ema;
            }

            active_threshold = max(peak_ema * threshold_sensitivity, baseline_floor);
            updateSkipPeriod(interval);

            sensorData.step_taken = true;
            esp_now_send(receiverAddress, (uint8_t *) &sensorData, sizeof(sensorData));
        }

        // --- Debug print, rate-limited so it doesn't flood Serial or slow the loop ---
        if (DEBUG_SERIAL && (now - last_debug_print >= debug_print_interval)) {
            last_debug_print = now;
            Serial.print(now);
            Serial.print(",");
            Serial.print(A_sq);
            Serial.print(",");
            Serial.print(active_threshold);
            Serial.print(",");
            Serial.print(peak_ema);
            Serial.print(",");
            Serial.print(skip_period);
            Serial.print(",");
            Serial.println(step_fired ? 1 : 0);
        }
    }

    if (dataSent) {
        digitalWrite(2, sendSuccess ? HIGH : LOW);
        dataSent = false;
    }
    delay(10); // 100Hz
}
