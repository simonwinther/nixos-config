float getSdfRectangle(in vec2 p, in vec2 xy, in vec2 b)
{
    vec2 d = abs(p - xy) - b;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
}

// Based on Inigo Quilez's 2D distance functions article: https://iquilezles.org/articles/distfunctions2d/
// Potentially optimized by eliminating conditionals and loops to enhance performance and reduce branching

float seg(in vec2 p, in vec2 a, in vec2 b, inout float s, float d) {
    vec2 e = b - a;
    vec2 w = p - a;
    vec2 proj = a + e * clamp(dot(w, e) / dot(e, e), 0.0, 1.0);
    float segd = dot(p - proj, p - proj);
    d = min(d, segd);

    float c0 = step(0.0, p.y - a.y);
    float c1 = 1.0 - step(0.0, p.y - b.y);
    float c2 = 1.0 - step(0.0, e.x * w.y - e.y * w.x);
    float allCond = c0 * c1 * c2;
    float noneCond = (1.0 - c0) * (1.0 - c1) * (1.0 - c2);
    float flip = mix(1.0, -1.0, step(0.5, allCond + noneCond));
    s *= flip;
    return d;
}

float getSdfParallelogram(in vec2 p, in vec2 v0, in vec2 v1, in vec2 v2, in vec2 v3) {
    float s = 1.0;
    float d = dot(p - v0, p - v0);

    d = seg(p, v0, v3, s, d);
    d = seg(p, v1, v0, s, d);
    d = seg(p, v2, v1, s, d);
    d = seg(p, v3, v2, s, d);

    return s * sqrt(d);
}

vec2 normalize(vec2 value, float isPosition) {
    return (value * 2.0 - (iResolution.xy * isPosition)) / iResolution.y;
}

float antialising(float distance) {
    return 1. - smoothstep(0., normalize(vec2(2., 2.), 0.).x, distance);
}

float determineStartVertexFactor(vec2 c, vec2 p) {
    // Conditions using step
    float condition1 = step(p.x, c.x) * step(c.y, p.y); // c.x < p.x && c.y > p.y
    float condition2 = step(c.x, p.x) * step(p.y, c.y); // c.x > p.x && c.y < p.y

    // If neither condition is met, return 1 (else case)
    return 1.0 - max(condition1, condition2);
}

vec2 getRectangleCenter(vec4 rectangle) {
    return vec2(rectangle.x + (rectangle.z / 2.), rectangle.y - (rectangle.w / 2.));
}
float ease(float x) {
    return pow(1.0 - x, 3.0);
}

vec4 saturate(vec4 color, float factor) {
    float gray = dot(color, vec4(0.299, 0.587, 0.114, 0.)); // luminance
    return mix(vec4(gray), color, factor);
}

// --- Theme-matched trail colors (Catppuccin Blue & a darker companion) ---
// old intensities, they were a bit strong
//const vec4 TRAIL_COLOR        = vec4(0.537, 0.706, 0.980, 1.0); // #89b4fa (matches selection/blue)
//const float TRAIL_INTENSITY = 0.6; // lower = more subtle overall default was 0.6
//const float SAT_FACTOR      = 1.10; // softer saturation than 1.5

const vec4 TRAIL_COLOR        = vec4(0.437, 0.706, 0.980, 1.0); // #89b4fa (matches selection/blue)
const vec4 TRAIL_COLOR_ACCENT = vec4(0.431, 0.565, 0.784, 1.0); // #6e90c8 (~20% darker)
const float TRAIL_INTENSITY = 0.25;
const float SAT_FACTOR = 0.85;

const float DURATION = 0.5; // IN SECONDS

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    #if !defined(WEB)
    fragColor = texture(iChannel0, fragCoord.xy / iResolution.xy);
    #endif
    // Normalization for fragCoord to a space of -1 to 1;
    vec2 vu = normalize(fragCoord, 1.);
    vec2 offsetFactor = vec2(-.5, 0.5);

    // Normalization for cursor position and size;
    // cursor xy has the position in a space of -1 to 1;
    // zw has the width and height
    vec4 currentCursor  = vec4(normalize(iCurrentCursor.xy, 1.),  normalize(iCurrentCursor.zw, 0.));
    vec4 previousCursor = vec4(normalize(iPreviousCursor.xy, 1.), normalize(iPreviousCursor.zw, 0.));

    vec2 centerCC = getRectangleCenter(currentCursor);
    vec2 centerCP = getRectangleCenter(previousCursor);
    // Determine where to start (top-left or top-right) for the trail parallelogram
    float vertexFactor           = determineStartVertexFactor(currentCursor.xy, previousCursor.xy);
    float invertedVertexFactor   = 1.0 - vertexFactor;

    // Parallelogram vertices
    vec2 v0 = vec2(currentCursor.x + currentCursor.z * vertexFactor,         currentCursor.y - currentCursor.w);
    vec2 v1 = vec2(currentCursor.x + currentCursor.z * invertedVertexFactor, currentCursor.y);
    vec2 v2 = vec2(previousCursor.x + currentCursor.z * invertedVertexFactor, previousCursor.y);
    vec2 v3 = vec2(previousCursor.x + currentCursor.z * vertexFactor,         previousCursor.y - previousCursor.w);

    float sdfCurrentCursor = getSdfRectangle(vu, currentCursor.xy - (currentCursor.zw * offsetFactor), currentCursor.zw * 0.5);
    float sdfTrail         = getSdfParallelogram(vu, v0, v1, v2, v3);

    float progress       = clamp((iTime - iTimeCursorChange) / DURATION, 0.0, 1.0);
    float easedProgress  = ease(progress);
    // Distance between cursors determines total trail length
    float lineLength = distance(centerCC, centerCP);

    float mod = .007;

    // --- Trail blending (subtler, theme-matched) ---
    vec4 trail = mix(
        saturate(TRAIL_COLOR_ACCENT, SAT_FACTOR),
        fragColor,
        1. - smoothstep(0., sdfTrail + mod, 0.007) * TRAIL_INTENSITY
    );
    trail = mix(
        saturate(TRAIL_COLOR, SAT_FACTOR),
        trail,
        1. - smoothstep(0., sdfTrail + mod, 0.006) * TRAIL_INTENSITY
    );
    trail = mix(
        trail,
        saturate(TRAIL_COLOR, SAT_FACTOR),
        step(sdfTrail + mod, 0.) * TRAIL_INTENSITY
    );

    // --- Cursor highlight (also toned down) ---
    trail = mix(
        saturate(TRAIL_COLOR_ACCENT, SAT_FACTOR),
        trail,
        (1. - smoothstep(0., sdfCurrentCursor + .002, 0.004)) * 0.70
    );
    trail = mix(
        saturate(TRAIL_COLOR, SAT_FACTOR),
        trail,
        (1. - smoothstep(0., sdfCurrentCursor + .002, 0.004)) * 0.70
    );

    // Fade-in strength tied to motion length, eased over time (also subtle)
    fragColor = mix(trail, fragColor, 1. - smoothstep(0., sdfCurrentCursor, (easedProgress * lineLength) * TRAIL_INTENSITY));
}
