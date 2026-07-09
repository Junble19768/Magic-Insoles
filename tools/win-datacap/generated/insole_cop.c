#include "insole_cop.h"

#include <math.h>

static int insole_is_finite(float value) {
    return !isnan(value) && !isinf(value);
}

void insole_compute_cop(
    const uint16_t pressures[INSOLE_SENSOR_COUNT],
    const insole_centroid_t centroids[INSOLE_SENSOR_COUNT],
    insole_cop_t *out
) {
    float weighted_x = 0.0f;
    float weighted_y = 0.0f;
    float total = 0.0f;

    if (out == NULL) {
        return;
    }

    for (size_t i = 0; i < INSOLE_SENSOR_COUNT; ++i) {
        const float weight = (float)pressures[i];
        if (weight <= 0.0f) {
            continue;
        }
        weighted_x += centroids[i].x * weight;
        weighted_y += centroids[i].y * weight;
        total += weight;
    }

    out->total = total;
    if (total <= 0.0f) {
        out->x = INSOLE_COP_NAN;
        out->y = INSOLE_COP_NAN;
        return;
    }

    out->x = weighted_x / total;
    out->y = weighted_y / total;
}

int insole_cop_tracker_init(
    insole_cop_tracker_t *tracker,
    insole_cop_sample_t *buffer,
    size_t capacity,
    uint32_t window_ms
) {
    if (tracker == NULL || buffer == NULL || capacity == 0) {
        return 0;
    }

    tracker->samples = buffer;
    tracker->capacity = capacity;
    tracker->head = 0;
    tracker->count = 0;
    tracker->window_ms = window_ms;
    return 1;
}

void insole_cop_tracker_clear(insole_cop_tracker_t *tracker) {
    if (tracker == NULL) {
        return;
    }
    tracker->head = 0;
    tracker->count = 0;
}

static size_t tracker_physical_index(const insole_cop_tracker_t *tracker, size_t logical_index) {
    return (tracker->head + logical_index) % tracker->capacity;
}

void insole_cop_tracker_prune(insole_cop_tracker_t *tracker, uint32_t stamp_ms) {
    if (tracker == NULL || tracker->count == 0) {
        return;
    }

    const uint32_t cutoff = stamp_ms - tracker->window_ms;
    while (tracker->count > 0) {
        const insole_cop_sample_t *sample = &tracker->samples[tracker->head];
        if (sample->stamp_ms >= cutoff) {
            break;
        }
        tracker->head = (tracker->head + 1) % tracker->capacity;
        tracker->count -= 1;
    }
}

void insole_cop_tracker_append(
    insole_cop_tracker_t *tracker,
    uint32_t stamp_ms,
    float x,
    float y
) {
    if (tracker == NULL || tracker->samples == NULL || tracker->capacity == 0) {
        return;
    }
    if (!insole_is_finite(x) || !insole_is_finite(y)) {
        return;
    }

    insole_cop_tracker_prune(tracker, stamp_ms);

    size_t write_index;
    if (tracker->count < tracker->capacity) {
        write_index = tracker_physical_index(tracker, tracker->count);
        tracker->count += 1;
    } else {
        write_index = tracker->head;
        tracker->head = (tracker->head + 1) % tracker->capacity;
    }

    tracker->samples[write_index].stamp_ms = stamp_ms;
    tracker->samples[write_index].x = x;
    tracker->samples[write_index].y = y;
}

size_t insole_cop_tracker_count(const insole_cop_tracker_t *tracker) {
    return tracker == NULL ? 0 : tracker->count;
}

size_t insole_cop_tracker_copy_xy(
    const insole_cop_tracker_t *tracker,
    float *xs,
    float *ys,
    size_t max_points
) {
    if (tracker == NULL || xs == NULL || ys == NULL || max_points == 0) {
        return 0;
    }

    const size_t copy_count = tracker->count < max_points ? tracker->count : max_points;
    for (size_t i = 0; i < copy_count; ++i) {
        const insole_cop_sample_t *sample =
            &tracker->samples[tracker_physical_index(tracker, i)];
        xs[i] = sample->x;
        ys[i] = sample->y;
    }
    return copy_count;
}

int insole_cop_fit_line(
    const float *xs,
    const float *ys,
    size_t point_count,
    size_t min_points,
    insole_cop_line_fit_t *out
) {
    float mean_x = 0.0f;
    float mean_y = 0.0f;
    float sxx = 0.0f;
    float sxy = 0.0f;
    float syy = 0.0f;
    size_t valid_count = 0;

    if (out == NULL || xs == NULL || ys == NULL) {
        return 0;
    }

    for (size_t i = 0; i < point_count; ++i) {
        if (!insole_is_finite(xs[i]) || !insole_is_finite(ys[i])) {
            continue;
        }
        mean_x += xs[i];
        mean_y += ys[i];
        valid_count += 1;
    }

    if (valid_count < min_points) {
        return 0;
    }

    mean_x /= (float)valid_count;
    mean_y /= (float)valid_count;

    for (size_t i = 0; i < point_count; ++i) {
        float dx;
        float dy;
        if (!insole_is_finite(xs[i]) || !insole_is_finite(ys[i])) {
            continue;
        }
        dx = xs[i] - mean_x;
        dy = ys[i] - mean_y;
        sxx += dx * dx;
        sxy += dx * dy;
        syy += dy * dy;
    }

    if (sxx == 0.0f && sxy == 0.0f && syy == 0.0f) {
        return 0;
    }

    {
        const float trace = sxx + syy;
        const float det = sxx * syy - sxy * sxy;
        const float quarter = trace * 0.5f;
        float gap = quarter * quarter - det;
        float lambda1;
        float dx;
        float dy;
        float norm;

        if (gap < 0.0f) {
            gap = 0.0f;
        }
        lambda1 = quarter + sqrtf(gap);

        dx = sxy;
        dy = lambda1 - sxx;
        if (fabsf(dx) < 1e-12f && fabsf(dy) < 1e-12f) {
            dx = lambda1 - syy;
            dy = sxy;
        }
        if (dy < 0.0f) {
            dx = -dx;
            dy = -dy;
        }

        norm = hypotf(dx, dy);
        if (norm <= 0.0f) {
            return 0;
        }
        dx /= norm;
        dy /= norm;

        out->angle_deg = atan2f(fabsf(dx), fabsf(dy)) * (180.0f / (float)M_PI);
        out->centroid_x = mean_x;
        out->centroid_y = mean_y;
        out->direction_x = dx;
        out->direction_y = dy;
        out->point_count = valid_count;
        return 1;
    }
}

void insole_cop_fit_line_segment(
    const insole_cop_line_fit_t *fit,
    const float *xs,
    const float *ys,
    size_t point_count,
    float *x0,
    float *y0,
    float *x1,
    float *y1
) {
    float t_min = 0.0f;
    float t_max = 0.0f;
    int has_projection = 0;

    if (fit == NULL || x0 == NULL || y0 == NULL || x1 == NULL || y1 == NULL) {
        return;
    }

    for (size_t i = 0; i < point_count; ++i) {
        float t;
        if (!insole_is_finite(xs[i]) || !insole_is_finite(ys[i])) {
            continue;
        }
        t = (xs[i] - fit->centroid_x) * fit->direction_x
            + (ys[i] - fit->centroid_y) * fit->direction_y;
        if (!has_projection) {
            t_min = t;
            t_max = t;
            has_projection = 1;
        } else {
            if (t < t_min) {
                t_min = t;
            }
            if (t > t_max) {
                t_max = t;
            }
        }
    }

    if (!has_projection) {
        *x0 = fit->centroid_x - fit->direction_x;
        *y0 = fit->centroid_y - fit->direction_y;
        *x1 = fit->centroid_x + fit->direction_x;
        *y1 = fit->centroid_y + fit->direction_y;
        return;
    }

    *x0 = fit->centroid_x + fit->direction_x * t_min;
    *y0 = fit->centroid_y + fit->direction_y * t_min;
    *x1 = fit->centroid_x + fit->direction_x * t_max;
    *y1 = fit->centroid_y + fit->direction_y * t_max;
}

void insole_cop_running_stats_init(insole_cop_running_stats_t *stats) {
    if (stats == NULL) {
        return;
    }
    stats->count = 0;
    stats->mean_x = 0.0f;
    stats->mean_y = 0.0f;
    stats->std_x = 0.0f;
    stats->std_y = 0.0f;
}

void insole_cop_running_stats_push(
    insole_cop_running_stats_t *stats,
    float x,
    float y
) {
    size_t n;

    if (stats == NULL || !insole_is_finite(x) || !insole_is_finite(y)) {
        return;
    }

    n = stats->count + 1;
    {
        const float delta_x = x - stats->mean_x;
        const float delta_y = y - stats->mean_y;
        const float mean_x_new = stats->mean_x + delta_x / (float)n;
        const float mean_y_new = stats->mean_y + delta_y / (float)n;
        const float delta_x2 = x - mean_x_new;
        const float delta_y2 = y - mean_y_new;

        if (n > 1) {
            stats->std_x = sqrtf(
                ((stats->std_x * stats->std_x) * (float)(n - 2)
                 + delta_x * delta_x2)
                    / (float)(n - 1)
            );
            stats->std_y = sqrtf(
                ((stats->std_y * stats->std_y) * (float)(n - 2)
                 + delta_y * delta_y2)
                    / (float)(n - 1)
            );
        } else {
            stats->std_x = 0.0f;
            stats->std_y = 0.0f;
        }

        stats->mean_x = mean_x_new;
        stats->mean_y = mean_y_new;
        stats->count = n;
    }
}
