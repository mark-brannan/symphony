#ifndef TEMPERATURE_H
#define TEMPERATURE_H

inline float convertDegreesKtoC(float degreesK) {
    return degreesK - 273.15;
}

inline float convertDegreesKtoF(float degreesK) {
    return convertDegreesKtoC(degreesK) * (9.0 / 5) + 32;
}

#endif /* TEMPERATURE_H */