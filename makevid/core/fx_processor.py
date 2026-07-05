"""FX Processor - Aplica efeitos visuais aos frames de video."""

import logging
logger = logging.getLogger(__name__)

import numpy as np

# Cor global do FX (fallback quando params nao tem cor salva)
_fx_colors = {
    "fade": [0, 0, 0],
    "flash": [255, 255, 255],
}


def set_fx_color(fx_type: str, rgb: list):
    """Define a cor de um efeito (chamado pelo FX editor)."""
    _fx_colors[fx_type] = list(rgb)


def apply_fx_to_frame(frame_rgb, fx_items, current_time, total_duration):
    """Aplica todos os efeitos ativos no tempo atual ao frame."""
    for item in fx_items:
        if item.start_time <= current_time <= item.start_time + item.duration:
            t = (current_time - item.start_time) / max(0.01, item.duration)
            params = getattr(item, 'params', {}) or {}
            eased_t = _apply_easing(t, params.get("easing", "linear"))
            result = _apply_single_fx(frame_rgb, item.name, eased_t, params)
            # Aplicar intensidade (mix entre original e efeito)
            intensity = float(params.get("intensity", 100)) / 100.0
            if intensity < 1.0:
                result = (frame_rgb.astype(np.float32) * (1.0 - intensity) +
                          result.astype(np.float32) * intensity).clip(0, 255).astype(np.uint8)
            frame_rgb = result
    return frame_rgb


def _apply_easing(t, easing):
    t = max(0.0, min(1.0, float(t)))
    e = (easing or "linear").lower().strip()
    if e == "ease-in":
        return t * t
    if e == "ease-out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if e == "ease-in-out":
        if t < 0.5:
            return 2.0 * t * t
        return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0
    return t


def _get_int(params, key, default, mn=None, mx=None):
    try:
        v = int(float(params.get(key, default)))
    except Exception:
        v = int(default)
    if mn is not None:
        v = max(mn, v)
    if mx is not None:
        v = min(mx, v)
    return v


def _get_color(params, fx_type, default):
    """Pega cor dos params salvos ou do fallback global."""
    color_str = params.get("color", "")
    if color_str:
        try:
            return [int(x) for x in color_str.split(",")]
        except Exception as _e:
            logger.debug(f"Suppressed: {_e}")
    return _fx_colors.get(fx_type, default)


def _get_color_opacity(params):
    """Opacidade da cor em 0.0-1.0."""
    try:
        return max(0.0, min(1.0, float(params.get("color_opacity", 100)) / 100.0))
    except Exception:
        return 1.0


def _blend_color(frame, color_rgb, amount):
    """Mistura frame com uma cor por amount (0.0-1.0)."""
    a = max(0.0, min(1.0, float(amount)))
    if a <= 0.0:
        return frame
    layer = np.full_like(frame, color_rgb, dtype=np.uint8)
    blended = frame.astype(np.float32) * (1.0 - a) + layer.astype(np.float32) * a
    return blended.clip(0, 255).astype(np.uint8)


def _apply_single_fx(frame, name, t, params):
    """Aplica um efeito. t = 0.0 a 1.0 (progresso)."""
    name_lower = name.lower()

    if "fade in" in name_lower:
        fade_color = _get_color(params, "fade", [0, 0, 0])
        op = _get_color_opacity(params)
        return _blend_color(frame, fade_color, op * (1.0 - t))

    elif "fade out" in name_lower:
        fade_color = _get_color(params, "fade", [0, 0, 0])
        op = _get_color_opacity(params)
        return _blend_color(frame, fade_color, op * t)

    elif "flash" in name_lower:
        if t < 0.3:
            intensity = 1.0 - (t / 0.3)
            flash_color = _get_color(params, "flash", [255, 255, 255])
            op = _get_color_opacity(params)
            return _blend_color(frame, flash_color, intensity * op)
        return frame

    elif "glitch" in name_lower:
        h, w, _ = frame.shape
        result = frame.copy()
        freq = _get_int(params, "frequency", 10, 1, 30)
        rgb_shift = _get_int(params, "rgb_shift", 5, 0, 20)
        rng = np.random.RandomState(int(t * 1000 + freq * 13))
        glitch_lines = max(1, int((freq / 30.0) * 20))
        for _ in range(glitch_lines):
            y = rng.randint(0, h)
            shift = rng.randint(-max(1, rgb_shift * 2), max(2, rgb_shift * 2 + 1))
            result[y] = np.roll(frame[y], shift, axis=0)
        if rgb_shift > 0:
            result[:, :, 0] = np.roll(result[:, :, 0], rng.randint(-rgb_shift, rgb_shift + 1), axis=1)
            result[:, :, 2] = np.roll(result[:, :, 2], rng.randint(-rgb_shift, rgb_shift + 1), axis=1)
        return result

    elif "wipe left" in name_lower:
        h, w, _ = frame.shape
        edge_soft = _get_int(params, "edge_softness", 0, 0, 50)
        cut = int(w * t)
        fade_color = _get_color(params, "fade", [0, 0, 0])
        op = _get_color_opacity(params)
        result = _blend_color(frame, fade_color, op)
        result[:, :cut] = frame[:, :cut]
        if edge_soft > 0 and 0 <= cut < w:
            a = max(0, cut - edge_soft)
            b = min(w, cut + edge_soft)
            if b > a:
                ramp = np.linspace(0.0, 1.0, b - a, dtype=np.float32).reshape(1, -1, 1)
                left = _blend_color(frame[:, a:b], fade_color, op).astype(np.float32)
                right = frame[:, a:b].astype(np.float32)
                result[:, a:b] = (left * (1.0 - ramp) + right * ramp).clip(0, 255).astype(np.uint8)
        return result

    elif "wipe right" in name_lower:
        h, w, _ = frame.shape
        edge_soft = _get_int(params, "edge_softness", 0, 0, 50)
        cut = int(w * (1 - t))
        fade_color = _get_color(params, "fade", [0, 0, 0])
        op = _get_color_opacity(params)
        result = _blend_color(frame, fade_color, op)
        result[:, cut:] = frame[:, cut:]
        if edge_soft > 0 and 0 <= cut < w:
            a = max(0, cut - edge_soft)
            b = min(w, cut + edge_soft)
            if b > a:
                ramp = np.linspace(1.0, 0.0, b - a, dtype=np.float32).reshape(1, -1, 1)
                left = _blend_color(frame[:, a:b], fade_color, op).astype(np.float32)
                right = frame[:, a:b].astype(np.float32)
                result[:, a:b] = (left * (1.0 - ramp) + right * ramp).clip(0, 255).astype(np.uint8)
        return result

    elif "dissolve" in name_lower or "cross" in name_lower:
        fade_color = _get_color(params, "fade", [0, 0, 0])
        op = _get_color_opacity(params)
        return _blend_color(frame, fade_color, op * (1.0 - t))

    elif "vignette" in name_lower:
        h, w, _ = frame.shape
        radius_pct = _get_int(params, "radius", 60, 20, 100) / 100.0
        softness_pct = _get_int(params, "softness", 50, 10, 100) / 100.0
        Y, X = np.ogrid[:h, :w]
        cy, cx = h / 2, w / 2
        r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        max_r = np.sqrt(cx ** 2 + cy ** 2)
        inner = max(0.05, radius_pct * 0.9)
        outer = min(1.5, inner + max(0.05, softness_pct * 0.8))
        vignette = 1.0 - np.clip((r / max_r - inner) / max(0.01, outer - inner), 0, 1)
        vignette = vignette[:, :, np.newaxis]
        return (frame.astype(np.float32) * vignette).clip(0, 255).astype(np.uint8)

    elif "blur" in name_lower:
        try:
            from scipy.ndimage import uniform_filter
            radius = _get_int(params, "radius", 5, 1, 30)
            blurred = uniform_filter(frame.astype(np.float32), size=(radius, radius, 1))
            return blurred.clip(0, 255).astype(np.uint8)
        except ImportError:
            return frame

    elif "shake" in name_lower:
        h, w, _ = frame.shape
        amp = _get_int(params, "amplitude", 8, 1, 30)
        spd = _get_int(params, "speed", 10, 1, 20)
        rng = np.random.RandomState(int(t * 10000 * max(1, spd)))
        dx = rng.randint(-amp, amp + 1)
        dy = rng.randint(-amp, amp + 1)
        result = np.zeros_like(frame)
        sx = max(0, dx)
        sy = max(0, dy)
        ex = min(w, w + dx)
        ey = min(h, h + dy)
        result[sy:ey, sx:ex] = frame[max(0, -dy):ey - sy + max(0, -dy), max(0, -dx):ex - sx + max(0, -dx)]
        return result

    elif "color shift" in name_lower or "rgb split" in name_lower or "chromatic" in name_lower:
        result = frame.copy()
        rs = _get_int(params, "red_shift", 0, -20, 20)
        gs = _get_int(params, "green_shift", 0, -20, 20)
        bs = _get_int(params, "blue_shift", 0, -20, 20)
        if rs == 0 and gs == 0 and bs == 0:
            shift = max(1, _get_int(params, "rgb_shift", 5, 0, 20))
            rs, gs, bs = shift, 0, -shift
        result[:, :, 0] = np.roll(frame[:, :, 0], rs, axis=1)
        result[:, :, 1] = np.roll(frame[:, :, 1], gs, axis=1)
        result[:, :, 2] = np.roll(frame[:, :, 2], bs, axis=1)
        return result

    elif "sepia" in name_lower:
        strength = _get_int(params, "strength", 80, 0, 100) / 100.0
        f = frame.astype(np.float32)
        r = f[:, :, 0] * 0.393 + f[:, :, 1] * 0.769 + f[:, :, 2] * 0.189
        g = f[:, :, 0] * 0.349 + f[:, :, 1] * 0.686 + f[:, :, 2] * 0.168
        b = f[:, :, 0] * 0.272 + f[:, :, 1] * 0.534 + f[:, :, 2] * 0.131
        sepia = np.stack([r, g, b], axis=2).clip(0, 255)
        if strength <= 0:
            return frame
        if strength >= 1:
            return sepia.astype(np.uint8)
        blended = frame.astype(np.float32) * (1.0 - strength) + sepia.astype(np.float32) * strength
        return blended.clip(0, 255).astype(np.uint8)

    elif "invert" in name_lower:
        inverted = 255 - frame.astype(np.float32)
        return inverted.clip(0, 255).astype(np.uint8)

    elif "pixelate" in name_lower:
        h, w, _ = frame.shape
        size = _get_int(params, "pixel_size", 8, 2, 32)
        small = frame[::size, ::size]
        result = np.repeat(np.repeat(small, size, axis=0), size, axis=1)
        return result[:h, :w]

    elif "film grain" in name_lower:
        amount = _get_int(params, "amount", 30, 5, 80)
        rng = np.random.RandomState(int(t * 100000))
        noise = rng.randint(-amount, amount + 1, frame.shape).astype(np.float32)
        result = frame.astype(np.float32) + noise * (amount / 100.0)
        return result.clip(0, 255).astype(np.uint8)

    elif "letterbox" in name_lower:
        h, w, _ = frame.shape
        bar = int(h * (_get_int(params, "bar_size", 12, 5, 25) / 100.0))
        result = frame.copy()
        result[:bar] = 0
        result[-bar:] = 0
        return result

    return frame
