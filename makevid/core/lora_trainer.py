"""LoRA Trainer - Fine-tune Wan 2.2 com imagens de ambientação."""

import logging
import time
import shutil
from pathlib import Path
from typing import Optional, Callable, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LoRAConfig:
    """Configuração de treinamento LoRA."""
    rank: int = 16
    alpha: int = 16
    lr: float = 1e-4
    epochs: int = 100
    batch_size: int = 1
    resolution: int = 512
    gradient_checkpointing: bool = True
    mixed_precision: str = "fp16"
    save_steps: int = 50
    trigger_word: str = "ambience_style"


@dataclass
class TrainingStatus:
    """Status do treinamento."""
    running: bool = False
    step: int = 0
    total_steps: int = 0
    loss: float = 0.0
    elapsed: float = 0.0
    eta: str = ""
    output_path: str = ""
    error: str = ""


def get_lora_dir() -> Path:
    """Retorna diretório onde LoRAs treinados são salvos."""
    from makevid.config import DATA_DIR
    lora_dir = DATA_DIR / "loras"
    lora_dir.mkdir(parents=True, exist_ok=True)
    return lora_dir


def list_trained_loras() -> List[Path]:
    """Lista LoRAs treinados disponíveis."""
    lora_dir = get_lora_dir()
    return sorted(lora_dir.glob("*.safetensors"))


def train_lora(
    images_dir: Path,
    output_name: str = "ambience_lora",
    config: Optional[LoRAConfig] = None,
    on_progress: Optional[Callable[[TrainingStatus], None]] = None,
    on_done: Optional[Callable[[str], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
):
    """
    Treina LoRA no Wan 2.2 usando imagens de referência.
    
    Roda em thread separada. Requer 24GB+ VRAM.
    """
    import threading

    if config is None:
        config = LoRAConfig()

    def _run():
        try:
            _train_loop(images_dir, output_name, config, on_progress, on_done, on_error)
        except Exception as e:
            logger.error(f"[LORA] Training failed: {e}")
            if on_error:
                on_error(str(e))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


def _train_loop(
    images_dir: Path,
    output_name: str,
    config: LoRAConfig,
    on_progress: Optional[Callable],
    on_done: Optional[Callable],
    on_error: Optional[Callable],
):
    """Loop principal de treinamento."""
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("GPU CUDA necessária para treinar LoRA (mínimo 24GB VRAM)")

    vram_gb = torch.cuda.get_device_properties(0).total_mem / (1024**3)
    if vram_gb < 20:
        logger.warning(f"[LORA] VRAM detectada: {vram_gb:.1f}GB. Recomendado 24GB+. Tentando com otimizações...")

    # Coletar imagens
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    image_paths = [f for f in sorted(images_dir.iterdir()) if f.suffix.lower() in exts]

    if len(image_paths) < 3:
        raise ValueError(f"Mínimo 3 imagens necessárias. Encontradas: {len(image_paths)}")

    logger.info(f"[LORA] Iniciando training com {len(image_paths)} imagens | rank={config.rank} | epochs={config.epochs}")

    status = TrainingStatus(running=True, total_steps=config.epochs * len(image_paths))

    if on_progress:
        on_progress(status)

    # Imports pesados
    from torch.utils.data import Dataset, DataLoader
    from torchvision import transforms
    from PIL import Image
    from peft import LoraConfig, get_peft_model
    from diffusers import AutoencoderKL, DDPMScheduler
    from transformers import CLIPTextModel, CLIPTokenizer

    start_time = time.time()
    output_path = get_lora_dir() / f"{output_name}.safetensors"

    # Dataset de imagens
    class AmbienceDataset(Dataset):
        def __init__(self, paths, resolution, trigger_word):
            self.paths = paths
            self.trigger = trigger_word
            self.transform = transforms.Compose([
                transforms.Resize(resolution, interpolation=transforms.InterpolationMode.LANCZOS),
                transforms.CenterCrop(resolution),
                transforms.ToTensor(),
                transforms.Normalize([0.5], [0.5]),
            ])

        def __len__(self):
            return len(self.paths)

        def __getitem__(self, idx):
            img = Image.open(self.paths[idx]).convert("RGB")
            return {
                "pixel_values": self.transform(img),
                "prompt": f"{self.trigger}, cinematic scene",
            }

    dataset = AmbienceDataset(image_paths, config.resolution, config.trigger_word)
    dataloader = DataLoader(dataset, batch_size=config.batch_size, shuffle=True)

    # Carregar modelo base (UNet/DiT do Wan 2.2)
    model_id = "Wan-AI/Wan2.2-T2V-14B"

    if on_progress:
        status.step = 0
        status.eta = "Carregando modelo..."
        on_progress(status)

    try:
        from diffusers import WanPipeline
        pipe = WanPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
    except Exception:
        # Fallback: tentar modelo menor
        model_id = "Wan-AI/Wan2.2-T2V-1.3B"
        logger.info(f"[LORA] Tentando modelo menor: {model_id}")
        from diffusers import WanPipeline
        pipe = WanPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
        )

    # Extrair componentes para training
    transformer = pipe.transformer
    vae = pipe.vae
    text_encoder = pipe.text_encoder
    tokenizer = pipe.tokenizer
    scheduler = pipe.scheduler

    # Congelar tudo exceto LoRA
    vae.requires_grad_(False)
    text_encoder.requires_grad_(False)
    transformer.requires_grad_(False)

    vae.to("cuda", dtype=torch.float16)
    text_encoder.to("cuda", dtype=torch.float16)

    # Aplicar LoRA no transformer
    lora_config = LoraConfig(
        r=config.rank,
        lora_alpha=config.alpha,
        target_modules=["to_q", "to_k", "to_v", "to_out.0"],
        lora_dropout=0.05,
    )

    transformer = get_peft_model(transformer, lora_config)
    transformer.to("cuda", dtype=torch.float16)

    if config.gradient_checkpointing:
        transformer.enable_gradient_checkpointing()

    transformer.print_trainable_parameters()

    # Optimizer
    trainable_params = [p for p in transformer.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=config.lr, weight_decay=1e-2)

    # Scheduler de LR
    from torch.optim.lr_scheduler import CosineAnnealingLR
    lr_scheduler = CosineAnnealingLR(optimizer, T_max=config.epochs)

    # Training loop
    global_step = 0
    transformer.train()

    for epoch in range(config.epochs):
        for batch in dataloader:
            pixel_values = batch["pixel_values"].to("cuda", dtype=torch.float16)

            # Encode imagens com VAE
            with torch.no_grad():
                latents = vae.encode(pixel_values).latent_dist.sample()
                latents = latents * vae.config.scaling_factor

                # Encode texto
                prompts = batch["prompt"]
                text_inputs = tokenizer(
                    prompts, padding="max_length",
                    max_length=tokenizer.model_max_length,
                    truncation=True, return_tensors="pt"
                ).to("cuda")
                encoder_hidden_states = text_encoder(**text_inputs).last_hidden_state

            # Add noise
            noise = torch.randn_like(latents)
            timesteps = torch.randint(0, scheduler.config.num_train_timesteps,
                                      (latents.shape[0],), device="cuda").long()
            noisy_latents = scheduler.add_noise(latents, noise, timesteps)

            # Expandir latents para formato video (adicionar dim temporal)
            # Para training com imagens, usamos 1 frame
            noisy_latents = noisy_latents.unsqueeze(2)  # [B, C, 1, H, W]
            encoder_hidden_states_expanded = encoder_hidden_states

            # Forward pass
            with torch.cuda.amp.autocast(dtype=torch.float16):
                noise_pred = transformer(
                    noisy_latents,
                    timestep=timesteps,
                    encoder_hidden_states=encoder_hidden_states_expanded,
                ).sample

            # Loss
            noise_target = noise.unsqueeze(2)
            loss = torch.nn.functional.mse_loss(noise_pred.float(), noise_target.float())

            # Backward
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable_params, 1.0)
            optimizer.step()
            optimizer.zero_grad()

            global_step += 1

            # Progress
            elapsed = time.time() - start_time
            if global_step > 1:
                per_step = elapsed / global_step
                remaining = per_step * (status.total_steps - global_step)
                m, s = int(remaining) // 60, int(remaining) % 60
                eta_str = f"{m:02d}:{s:02d}"
            else:
                eta_str = "calculando..."

            status.step = global_step
            status.loss = loss.item()
            status.elapsed = elapsed
            status.eta = eta_str

            if on_progress:
                on_progress(status)

            if global_step % 10 == 0:
                logger.info(f"[LORA] Step {global_step}/{status.total_steps} | Loss: {loss.item():.4f} | ETA: {eta_str}")

            # Save checkpoint
            if config.save_steps > 0 and global_step % config.save_steps == 0:
                _save_lora(transformer, output_path)

        lr_scheduler.step()

    # Save final
    _save_lora(transformer, output_path)

    status.running = False
    status.output_path = str(output_path)
    logger.info(f"[LORA] Training completo! Salvo em: {output_path}")

    # Limpar VRAM
    del transformer, vae, text_encoder, optimizer
    torch.cuda.empty_cache()

    if on_done:
        on_done(str(output_path))


def _save_lora(model, output_path: Path):
    """Salva pesos LoRA em safetensors."""
    from peft import PeftModel
    from safetensors.torch import save_file

    state_dict = {}
    for name, param in model.named_parameters():
        if param.requires_grad:
            state_dict[name] = param.data.cpu()

    save_file(state_dict, str(output_path))
    logger.info(f"[LORA] Checkpoint salvo: {output_path} ({output_path.stat().st_size / 1024 / 1024:.1f}MB)")


def load_lora_into_pipeline(pipe, lora_path: str, weight: float = 1.0):
    """Carrega LoRA treinado no pipeline de geração."""
    from safetensors.torch import load_file
    from peft import LoraConfig, set_peft_model_state_dict

    lora_state = load_file(lora_path)

    # Aplicar pesos no transformer do pipeline
    transformer = pipe.transformer
    lora_config = LoraConfig(
        r=16, lora_alpha=16,
        target_modules=["to_q", "to_k", "to_v", "to_out.0"],
    )

    from peft import get_peft_model
    transformer = get_peft_model(transformer, lora_config)

    # Carregar pesos
    incompatible = set_peft_model_state_dict(transformer, lora_state)
    if incompatible.missing_keys:
        logger.warning(f"[LORA] Missing keys: {len(incompatible.missing_keys)}")

    # Escalar peso
    if weight != 1.0:
        for name, param in transformer.named_parameters():
            if "lora" in name.lower() and param.requires_grad:
                param.data *= weight

    pipe.transformer = transformer
    logger.info(f"[LORA] Carregado: {Path(lora_path).name} (weight={weight})")
    return pipe
