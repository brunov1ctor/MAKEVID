"""FX Processor - Aplica efeitos visuais aos frames de video."""

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
            result = _apply_single_fx(frame_rgb, item.name, t, params)
            # Aplicar intensidade (mix entre original e efeito)
            intensity = float(params.get("intensity", 100)) / 100.0
            if intensity < 1.0:
                result = (frame_rgb.astype(np.float32) * (1.0 - intensity) +
                          result.astype(np.float32) * intensity).clip(0, 255).astype(np.uint8)
            frame_rgb = result
    return frame_rgb


def _get_color(params, fx_type, default):
    """Pega cor dos params salvos ou do fallback global."""
    color_str = params.get("color", "")
    if color_str:
        try:
            return [int(x) for x in color_str.split(",")]
        except Exception:
            pass
    return _fx_colors.get(fx_type, default)


def _apply_single_fx(frame, name, t, params):
    """Aplica um efeito. t = 0.0 a 1.0 (progresso)."""
    name_lower = name.lower()

    if "fade in" in name_lower:
        fade_color = _get_color(params, "fade", [0, 0, 0])
        overlay = np.full_like(frame, fade_color, dtype=np.uint8)
        blended = overlay.astype(np.float32) * (1.0 - t) + frame.astype(np.float32) * t
        return blended.clip(0, 255).astype(np.uint8)

    elif "fade out" in name_lower:
        fade_color = _get_color(params, "fade", [0, 0, 0])
        overlay = np.full_like(frame, fade_color, dtype=np.uint8)
        blended = frame.astype(np.float32) * (1.0 - t) + overlay.astype(np.float32) * t
        return blended.clip(0, 255).astype(np.uint8)

    elif "flash" in name_lower:
        if t < 0.3:
            intensity = 1.0 - (t / 0.3)
            flash_color = _get_color(params, "flash", [255, 255, 255])
            color_layer = np.full_like(frame, flash_color, dtype=np.uint8)
            blended = frame.astype(np.float32) * (1 - intensity) + color_layer.astype(np.float32) * intensity
            return blended.clip(0, 255).astype(np.uint8)
        return frame

    elif "glitch" in name_lower:
        h, w, _ = frame.shape
        result = frame.copy()
        rng = np.random.RandomState(int(t * 1000))
        for _ in range(int(5 + t * 10)):
            y = rng.randint(0, h)
            shift = rng.randint(-20, 20)
            result[y] = np.roll(frame[y], shift, axis=0)
        if t > 0.2:
            result[:, :, 0] = np.roll(result[:, :, 0], rng.randint(-5, 5), axis=1)
        return result

    elif "wipe left" in name_lower:
        h, w, _ = frame.shape
        cut = int(w * t)
        fade_color = _get_color(params, "fade", [0, 0, 0])
        result = np.full_like(frame, fade_color, dtype=np.uint8)
        result[:, :cut] = frame[:, :cut]
        return result

    elif "wipe right" in name_lower:
        h, w, _ = frame.shape
        cut = int(w * (1 - t))
        fade_color = _get_color(params, "fade", [0, 0, 0])
        result = np.full_like(frame, fade_color, dtype=np.uint8)
        result[:, cut:] = frame[:, cut:]
        return result

    elif "dissolve" in name_lower or "cross" in name_lower:
        fade_color = _get_color(params, "fade", [0, 0, 0])
        overlay = np.full_like(frame, fade_color, dtype=np.uint8)
        blended = overlay.astype(np.float32) * (1.0 - t) + frame.astype(np.float32) * t
        return blended.clip(0, 255).astype(np.uint8)

    elif "vignette" in name_lower:
        h, w, _ = frame.shape
        Y, X = np.ogrid[:h, :w]
        cy, cx = h / 2, w / 2
        r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        max_r = np.sqrt(cx ** 2 + cy ** 2)
        vignette = 1.0 - np.clip((r / max_r - 0.4) / 0.6, 0, 1)
        vignette = vignette[:, :, np.newaxis]
        return (frame.astype(np.float32) * vignette).clip(0, 255).astype(np.uint8)

    elif "blur" in name_lower:
        try:
            from scipy.ndimage import uniform_filter
            radius = max(1, int(5 * (0.3 + t * 0.7)))
            blurred = uniform_filter(frame.astype(np.float32), size=(radius, radius, 1))
            return blurred.clip(0, 255).astype(np.uint8)
        except ImportError:
            return frame

    elif "shake" in name_lower:
        h, w, _ = frame.shape
        rng = np.random.RandomState(int(t * 10000))
        dx = rng.randint(-8, 8)
        dy = rng.randint(-8, 8)
        result = np.zeros_like(frame)
        sx = max(0, dx)
        sy = max(0, dy)
        ex = min(w, w + dx)
        ey = min(h, h + dy)
        result[sy:ey, sx:ex] = frame[max(0, -dy):ey - sy + max(0, -dy), max(0, -dx):ex - sx + max(0, -dx)]
        return result

    elif "color shift" in name_lower:
        result = frame.copy()
        shift = max(1, int(5 * t))
        result[:, :, 0] = np.roll(frame[:, :, 0], shift, axis=1)
        result[:, :, 2] = np.roll(frame[:, :, 2], -shift, axis=1)
        return result

    elif "sepia" in name_lower:
        f = frame.astype(np.float32)
        r = f[:, :, 0] * 0.393 + f[:, :, 1] * 0.769 + f[:, :, 2] * 0.189
        g = f[:, :, 0] * 0.349 + f[:, :, 1] * 0.686 + f[:, :, 2] * 0.168
        b = f[:, :, 0] * 0.272 + f[:, :, 1] * 0.534 + f[:, :, 2] * 0.131
        sepia = np.stack([r, g, b], axis=2).clip(0, 255)
        return sepia.astype(np.uint8)

    elif "invert" in name_lower:
        inverted = 255 - frame.astype(np.float32)
        return inverted.clip(0, 255).astype(np.uint8)

    elif "pixelate" in name_lower:
        h, w, _ = frame.shape
        size = max(2, int(4 + t * 12))
        small = frame[::size, ::size]
        result = np.repeat(np.repeat(small, size, axis=0), size, axis=1)
        return result[:h, :w]

    elif "film grain" in name_lower:
        rng = np.random.RandomState(int(t * 100000))
        noise = rng.randint(-30, 30, frame.shape).astype(np.float32)
        result = frame.astype(np.float32) + noise * 0.5
        return result.clip(0, 255).astype(np.uint8)

    elif "letterbox" in name_lower:
        h, w, _ = frame.shape
        bar = int(h * 0.12)
        result = frame.copy()
        result[:bar] = 0
        result[-bar:] = 0
        return result

    return frame
