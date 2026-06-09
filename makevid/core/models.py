"""Model Manager - carrega pipelines Wan com controle de VRAM/CPU."""

import gc
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ModelManager:
    def __init__(self, cache_dir: Path, device: str = "cuda", max_vram_gb: float = 32):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_vram_gb = max_vram_gb
        self._models: Dict[str, Any] = {}

        import torch
        self.has_gpu = torch.cuda.is_available()
        self.device = torch.device(device if self.has_gpu else "cpu")

        if not self.has_gpu:
            logger.warning("GPU nao disponivel - modelos rodarao em CPU (lento)")

    # ============================================================
    # PUBLIC API
    # ============================================================

    def get(self, name: str, **kwargs):
        """Retorna pipeline pelo nome. Carrega se necessario."""
        if name in self._models:
            return self._models[name]

        loaders = {
            "wan_t2v": self._load_t2v,
            "wan_t2v_cpu": lambda: self._load_t2v(force_cpu=True),
            "wan_i2v": self._load_i2v,
            "wan22_ti2v": self._load_ti2v,
            "wan_vace": self._load_vace,
            "wan_v2v": self._load_v2v,
        }
        return loaders[name]()

    @property
    def vram_free_gb(self) -> float:
        if not self.has_gpu:
            return 0
        import torch
        total = torch.cuda.get_device_properties(0).total_mem
        used = torch.cuda.memory_allocated(0)
        return (total - used) / 1e9

    def unload_all(self):
        self._models.clear()
        if self.has_gpu:
            import torch
            torch.cuda.empty_cache()
        gc.collect()

    # ============================================================
    # LOADERS
    # ============================================================

    def _load_t2v(self, model_id: str = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers", force_cpu: bool = False):
        key = "wan_t2v_cpu" if force_cpu else "wan_t2v"
        if key in self._models:
            return self._models[key]
        if not self.has_gpu and not force_cpu:
            return None

        import torch
        from diffusers import WanPipeline

        if force_cpu:
            logger.info(f"Carregando {model_id} em CPU (float32)...")
            pipe = WanPipeline.from_pretrained(
                model_id, torch_dtype=torch.float32, cache_dir=str(self.cache_dir))
            pipe.to("cpu")
        else:
            pipe = WanPipeline.from_pretrained(
                model_id, torch_dtype=torch.float16, cache_dir=str(self.cache_dir))
            pipe.enable_model_cpu_offload()

        self._models[key] = pipe
        return pipe

    def _load_i2v(self, model_id: str = "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers"):
        if not self.has_gpu:
            return None
        if "wan_i2v" in self._models:
            return self._models["wan_i2v"]

        import torch
        from diffusers import WanImageToVideoPipeline

        pipe = WanImageToVideoPipeline.from_pretrained(
            model_id, torch_dtype=torch.float16, cache_dir=str(self.cache_dir))
        pipe.enable_model_cpu_offload()
        self._models["wan_i2v"] = pipe
        return pipe

    def _load_ti2v(self):
        """Wan 2.2 Text+Image to Video 5B (local)."""
        if not self.has_gpu:
            return None
        if "wan22_ti2v" in self._models:
            return self._models["wan22_ti2v"]

        import torch
        from diffusers import WanImageToVideoPipeline

        model_path = self.cache_dir / "wan22_ti2v"
        logger.info(f"Carregando Wan 2.2 TI2V de {model_path}")
        pipe = WanImageToVideoPipeline.from_pretrained(
            str(model_path), torch_dtype=torch.float16)
        pipe.enable_model_cpu_offload()
        self._models["wan22_ti2v"] = pipe
        return pipe

    def _load_vace(self, model_id: str = "Wan-AI/Wan2.1-VACE-1.3B-Diffusers"):
        """VACE - reference images para consistencia de personagem."""
        if not self.has_gpu:
            return None
        if "wan_vace" in self._models:
            return self._models["wan_vace"]

        import torch
        from diffusers import WanVACEPipeline

        logger.info(f"Carregando VACE {model_id}...")
        pipe = WanVACEPipeline.from_pretrained(
            model_id, torch_dtype=torch.float16, cache_dir=str(self.cache_dir))
        pipe.enable_model_cpu_offload()
        self._models["wan_vace"] = pipe
        return pipe

    def _load_v2v(self, model_id: str = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"):
        """Video-to-Video para refinamento."""
        if not self.has_gpu:
            return None
        if "wan_v2v" in self._models:
            return self._models["wan_v2v"]

        import torch
        from diffusers import WanVideoToVideoPipeline

        logger.info(f"Carregando V2V {model_id}...")
        pipe = WanVideoToVideoPipeline.from_pretrained(
            model_id, torch_dtype=torch.float16, cache_dir=str(self.cache_dir))
        pipe.enable_model_cpu_offload()
        self._models["wan_v2v"] = pipe
        return pipe
