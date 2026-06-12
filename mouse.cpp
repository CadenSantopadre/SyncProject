#include <iostream>
#include <iomanip>
#include <cmath>
#include <chrono>
#include <thread>
#include <windows.h>
#include <atomic>

void getForce(POINT& mousePos, long& lastX, long& lastY, float& force) {
    if (GetCursorPos(&mousePos)) {
        long currentX = mousePos.x;
        long currentY = mousePos.y;
        long dx = currentX - lastX;
        long dy = currentY - lastY;
        force = std::sqrt(static_cast<float>(dx * dx + dy * dy));
        lastX = currentX;
        lastY = currentY;
    }
}

// Track steps using only the last step time and the current step time
void checkStep(float threshold, float force, std::chrono::steady_clock::time_point start, 
               float& lastStepTime, float& currentStepTime, bool& stepDetected) {
    
    auto now = std::chrono::steady_clock::now();
    float secondsElapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start).count() / 1000.0f;
    
    stepDetected = false;
    if (force > threshold && (secondsElapsed - lastStepTime) > 0.3f) {
        currentStepTime = secondsElapsed;
        stepDetected = true;
        std::cout << "\nSTEP DETECTED! Force = " << force << '\n';
    }
}

// Stores up to 3 cadences in a fixed circular history array
void updateCadenceHistory(bool stepDetected, float lastStepTime, float currentStepTime, 
                          float (&cadences)[3], int& cadenceCount, int& headIndex) {
    if (!stepDetected) return;

    // We can only calculate a cadence if we have a previous step time
    if (lastStepTime > 0.0f) {
        float dt = currentStepTime - lastStepTime;
        if (dt > 0.1f) {
            float newCadence = 60.0f / dt;
            
            // Insert into the fixed 3-element circular array
            cadences[headIndex] = newCadence;
            headIndex = (headIndex + 1) % 3; 
            if (cadenceCount < 3) {
                cadenceCount++;
            }
        }
    }
}

// Calculates average purely from the active items in the fixed array
float calculateAvgCadence(const float (&cadences)[3], int cadenceCount) {
    if (cadenceCount == 0) return 0.0f;
    
    float sum = 0.0f;
    for (int i = 0; i < cadenceCount; ++i) {
        sum += cadences[i];
    }
    return sum / static_cast<float>(cadenceCount);
}

void metronome(std::atomic<bool>& running, std::atomic<float>& avgCadence) {
    while (running.load(std::memory_order_relaxed)) {
        float cadence = avgCadence.load(std::memory_order_relaxed);
        if (cadence >= 20.0f && cadence <= 300.0f) {
            int interval_ms = static_cast<int>(60000.0f / cadence);
            Beep(800, 50);
            std::cout << "Tick! (" << std::fixed << std::setprecision(1) << cadence << " BPM)\n";
            
            // Account for the 50ms beep duration to keep timing precise
            int sleep_ms = interval_ms - 50;
            if (sleep_ms > 0) {
                std::this_thread::sleep_for(std::chrono::milliseconds(sleep_ms));
            }
        } else {
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
    }
}

int main() {
    std::cout << "Starting mouse reader...\n";
    float threshold = 250.0f;
    POINT mousePos;
    long lastX = 0;
    long lastY = 0;
    float force = 0.0f;
    
    auto start = std::chrono::steady_clock::now();
    float lastStepTime = 0.0f;
    float currentStepTime = 0.0f;
    bool stepDetected = false;

    // Fixed-size rolling cadence tracking (No vectors)
    float cadences[3] = { 0.0f, 0.0f, 0.0f };
    int cadenceCount = 0;
    int headIndex = 0;

    std::atomic<float> avgCadence(0.0f);
    std::atomic<bool> running(true);

    if (GetCursorPos(&mousePos)) {
        lastX = mousePos.x;
        lastY = mousePos.y;
    }

    std::thread metThread(metronome, std::ref(running), std::ref(avgCadence));

    while (running.load(std::memory_order_relaxed)) {
        getForce(mousePos, lastX, lastY, force);
        
        checkStep(threshold, force, start, lastStepTime, currentStepTime, stepDetected);
        
        if (stepDetected) {
            updateCadenceHistory(stepDetected, lastStepTime, currentStepTime, cadences, cadenceCount, headIndex);
            float currentAvg = calculateAvgCadence(cadences, cadenceCount);
            avgCadence.store(currentAvg, std::memory_order_relaxed);
            
            // Shift timestamps forward for the next step event
            lastStepTime = currentStepTime;
        }

        if (GetAsyncKeyState(VK_ESCAPE) & 0x8000) {
            running.store(false, std::memory_order_relaxed);
        }

        // 10ms sleep limits polling loop to ~100Hz, saving massive CPU cycles
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }

    metThread.join();
    std::cout << "\nProgram exited.\n";
    return 0;
}
