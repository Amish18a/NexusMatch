#include "TrustModelBridge.h"

#include <iomanip>
#include <iostream>

int main()
{
    TrustModelBridge bridge;

    TrustFeatures reliable{
        20,
        0.95,
        0.05,
        0.90,
        0.05,
        0.90,
        1.00,
        0.00,
        1.00,
        0.00,
        1.00,
        25,
        45,
        3
    };

    TrustFeatures unreliable{
        20,
        0.40,
        0.60,
        0.30,
        0.70,
        0.20,
        0.33,
        0.67,
        0.33,
        0.67,
        0.00,
        60,
        80,
        2
    };

    for (
        const auto& item : {
            std::pair<const char*, TrustFeatures>{"Reliable example", reliable},
            std::pair<const char*, TrustFeatures>{"Unreliable example", unreliable}
        }
    )
    {
        TrustResult result{};
        std::string error;

        if (!bridge.predict(item.second, result, error))
        {
            std::cerr << item.first << ": " << error << "\n";
            return 1;
        }

        std::cout << std::fixed << std::setprecision(2);
        std::cout << item.first
                  << " -> Risk: " << result.unreliableRisk
                  << " | Trust: " << result.trustScore
                  << " | Label: " << result.label
                  << "\n";
    }

    return 0;
}