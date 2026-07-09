#ifndef INSOLE_COP_H
#define INSOLE_COP_H

#include <stddef.h>
#include <stdint.h>

#include "insole_sensor_centroids.h"

#ifdef __cplusplus
extern "C" {
#endif

#define INSOLE_COP_NAN (-1.0f)

#define INSOLE_COP_TRAJECTORY_DEFAULT_CAPACITY 500
#define INSOLE_COP_TRAJECTORY_DEFAULT_WINDOW_MS 10000
#define INSOLE_COP_TRAJECTORY_MIN_POINTS 2

typedef struct {
    float x;
    float y;
    float total;
} insole_cop_t;

typedef struct {
    uint32_t stamp_ms;
    float x;
    float y;
} insole_cop_sample_t;

typedef struct {
    insole_cop_sample_t *samples;
    size_t capacity;
    size_t head;
    size_t count;
    uint32_t window_ms;
} insole_cop_tracker_t;

typedef struct {
    float angle_deg;
    float centroid_x;
    float centroid_y;
    float direction_x;
    float direction_y;
    size_t point_count;
} insole_cop_line_fit_t;

typedef struct {
    size_t count;
    float mean_x;
    float mean_y;
    float std_x;
    float std_y;
} insole_cop_running_stats_t;

/** Pressure-weighted center of pressure for one foot (16 sensors). */
void insole_compute_cop(
    const uint16_t pressures[INSOLE_SENSOR_COUNT],
    const insole_centroid_t centroids[INSOLE_SENSOR_COUNT],
    insole_cop_t *out
);

/** Initialize a sliding-window COP trajectory buffer. */
int insole_cop_tracker_init(
    insole_cop_tracker_t *tracker,
    insole_cop_sample_t *buffer,
    size_t capacity,
    uint32_t window_ms
);

void insole_cop_tracker_clear(insole_cop_tracker_t *tracker);

/** Append one COP sample; drops oldest samples outside the time window. */
void insole_cop_tracker_append(
    insole_cop_tracker_t *tracker,
    uint32_t stamp_ms,
    float x,
    float y
);

/** Remove samples older than stamp_ms - window_ms. */
void insole_cop_tracker_prune(insole_cop_tracker_t *tracker, uint32_t stamp_ms);

size_t insole_cop_tracker_count(const insole_cop_tracker_t *tracker);

/** Copy active samples into caller arrays (oldest first). Returns copied count. */
size_t insole_cop_tracker_copy_xy(
    const insole_cop_tracker_t *tracker,
    float *xs,
    float *ys,
    size_t max_points
);

/**
 * Fit principal direction to COP trajectory via 2x2 covariance.
 * Angle is measured from +Y axis, matching Python/frontend SVD fit.
 * Returns 1 on success, 0 if insufficient or degenerate points.
 */
int insole_cop_fit_line(
    const float *xs,
    const float *ys,
    size_t point_count,
    size_t min_points,
    insole_cop_line_fit_t *out
);

/** Project trajectory points onto fitted line; write segment endpoints. */
void insole_cop_fit_line_segment(
    const insole_cop_line_fit_t *fit,
    const float *xs,
    const float *ys,
    size_t point_count,
    float *x0,
    float *y0,
    float *x1,
    float *y1
);

/** Online mean/std for balance sway metrics (Welford). */
void insole_cop_running_stats_init(insole_cop_running_stats_t *stats);

void insole_cop_running_stats_push(
    insole_cop_running_stats_t *stats,
    float x,
    float y
);

#ifdef __cplusplus
}
#endif

#endif /* INSOLE_COP_H */
