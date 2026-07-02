"""Ambience Matcher - Seleciona automaticamente a imagem de referencia
que mais combina com o prompt da cena.

Usa CLIP para calcular similaridade texto-imagem.
Fallback: matching por keywords simples se CLIP nao estiver disponivel.
"""

import logging
from pathlib import Path
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

_clip_model = None
_clip_processor = None
_image_embeddings_cache = {}


def get_ambience_images(project_id: str = "") -> List[Path]:
    """Retorna todas as imagens na pasta de ambientacao do projeto."""
    from makevid.config import AMBIENCE_REFS_DIR
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    folder = AMBIENCE_REFS_DIR / project_id if project_id else AMBIENCE_REFS_DIR
    if not folder.exists():
        return []
    return sorted(f for f in folder.iterdir() if f.suffix.lower() in exts)


def find_best_match(prompt: str, top_k: int = 1, project_id: str = "") -> Optional[str]:
    """Encontra a imagem de ambientacao que mais combina com o prompt.
    
    Retorna path da melhor imagem, ou None se nao houver imagens.
    """
    images = get_ambience_images(project_id)
    if not images:
        return None

    # Tentar CLIP primeiro (melhor qualidade)
    try:
        result = _match_with_clip(prompt, images, top_k)
        if result:
            logger.info(f"[AMBIENCE] CLIP match: '{prompt[:40]}' -> {result[0][0].name} (score: {result[0][1]:.3f})")
            return str(result[0][0])
    except Exception as e:
        logger.debug(f"[AMBIENCE] CLIP indisponivel ({e}), usando keywords...")

    # Fallback: matching por keywords
    result = _match_with_keywords(prompt, images)
    if result:
        logger.info(f"[AMBIENCE] Keyword match: '{prompt[:40]}' -> {result.name}")
        return str(result)

    # Ultimo fallback: primeira imagem
    logger.info(f"[AMBIENCE] Sem match especifico, usando primeira imagem")
    return str(images[0])


def find_dynamic_references(prompt: str, max_refs: int = 4, min_score: float = 0.20, project_id: str = "") -> List[str]:
    """Multi-referencia dinamica: retorna N imagens com score acima do threshold."""
    images = get_ambience_images(project_id)
    if not images:
        return []

    # Tentar CLIP
    try:
        scored = _match_with_clip(prompt, images, len(images))
        if scored:
            # Filtrar por threshold dinamico
            # Usar score relativo: min_score da melhor
            best_score = scored[0][1]
            threshold = max(min_score, best_score * 0.75)  # pelo menos 75% do melhor
            
            selected = []
            for path, score in scored:
                if score >= threshold and len(selected) < max_refs:
                    selected.append(str(path))
                elif len(selected) >= max_refs:
                    break
            
            # Garantir pelo menos 1
            if not selected:
                selected = [str(scored[0][0])]
            
            logger.info(
                f"[AMBIENCE] Dynamic refs: '{prompt[:40]}' -> "
                f"{len(selected)} imgs (best={best_score:.3f}, threshold={threshold:.3f})")
            for i, p in enumerate(selected):
                logger.info(f"  [{i+1}] {Path(p).name} (score: {scored[i][1]:.3f})")
            return selected
    except Exception as e:
        logger.debug(f"[AMBIENCE] CLIP indisponivel ({e}), fallback keywords...")

    # Fallback: keywords (retorna so 1)
    result = _match_with_keywords(prompt, images)
    if result:
        return [str(result)]
    
    return [str(images[0])] if images else []


def _match_with_clip(prompt: str, images: List[Path], top_k: int) -> List[Tuple[Path, float]]:
    """Match usando CLIP embeddings (alta qualidade)."""
    global _clip_model, _clip_processor, _image_embeddings_cache
    import torch
    from PIL import Image

    # Lazy load CLIP
    if _clip_model is None:
        from transformers import CLIPModel, CLIPProcessor
        model_name = "openai/clip-vit-base-patch32"
        _clip_processor = CLIPProcessor.from_pretrained(model_name)
        _clip_model = CLIPModel.from_pretrained(model_name)
        _clip_model.eval()
        if torch.cuda.is_available():
            _clip_model = _clip_model.to("cuda")

    device = next(_clip_model.parameters()).device

    # Encode texto
    text_inputs = _clip_processor(text=[prompt], return_tensors="pt", padding=True, truncation=True)
    text_inputs = {k: v.to(device) for k, v in text_inputs.items() if k in ("input_ids", "attention_mask")}
    with torch.no_grad():
        text_emb = _clip_model.get_text_features(**text_inputs)
        text_emb = text_emb / text_emb.norm(dim=-1, keepdim=True)

    # Encode imagens (com cache)
    scores = []
    for img_path in images:
        cache_key = (str(img_path), img_path.stat().st_mtime)
        if cache_key not in _image_embeddings_cache:
            img = Image.open(img_path).convert("RGB")
            img.thumbnail((224, 224))
            img_inputs = _clip_processor(images=img, return_tensors="pt")
            img_inputs = {k: v.to(device) for k, v in img_inputs.items() if k == "pixel_values"}
            with torch.no_grad():
                img_emb = _clip_model.get_image_features(**img_inputs)
                img_emb = img_emb / img_emb.norm(dim=-1, keepdim=True)
            _image_embeddings_cache[cache_key] = img_emb.cpu()
        else:
            img_emb = _image_embeddings_cache[cache_key].to(device)

        similarity = (text_emb @ img_emb.T).item()
        scores.append((img_path, similarity))

    # Ordenar por score decrescente
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k]


def _match_with_keywords(prompt: str, images: List[Path]) -> Optional[Path]:
    """Match simples por keywords no nome do arquivo."""
    prompt_lower = prompt.lower()

    # Mapa de keywords -> termos relacionados
    keyword_groups = {
        "vila": ["vila", "village", "aldeia", "town", "rua", "casa", "house", "street"],
        "castelo": ["castelo", "castle", "trono", "throne", "rei", "king", "torre", "tower", "muralha"],
        "floresta": ["floresta", "forest", "arvore", "tree", "mata", "woods", "trilha", "path"],
        "mina": ["mina", "mine", "caverna", "cave", "tunel", "tunnel", "subterr"],
        "cabana": ["cabana", "cabin", "hut", "shack", "interior", "room", "quarto"],
        "noite": ["noite", "night", "escuro", "dark", "lua", "moon", "sombr"],
        "dia": ["dia", "day", "sol", "sun", "manha", "morning", "luz", "light"],
        "chuva": ["chuva", "rain", "tempest", "storm", "nevoa", "fog", "mist"],
        "fogo": ["fogo", "fire", "chama", "flame", "tocha", "torch", "forja", "forge"],
        "rio": ["rio", "river", "agua", "water", "lago", "lake", "ponte", "bridge"],
        "montanha": ["montanha", "mountain", "colina", "hill", "rocha", "rock", "cliff"],
        "cemiterio": ["cemiterio", "cemetery", "tumba", "tomb", "morte", "dead", "cruz"],
        "igreja": ["igreja", "church", "templo", "temple", "altar", "padre", "priest"],
        "taverna": ["taverna", "tavern", "bar", "inn", "cerveja", "beer", "comida"],
        "batalha": ["batalha", "battle", "guerra", "war", "espada", "sword", "luta", "fight"],
    }

    # Encontrar quais keywords o prompt contem
    prompt_tags = set()
    for group, keywords in keyword_groups.items():
        for kw in keywords:
            if kw in prompt_lower:
                prompt_tags.add(group)
                break

    if not prompt_tags:
        return None

    # Pontuar cada imagem pelo nome do arquivo
    best_score = 0
    best_img = None
    for img_path in images:
        img_name = img_path.stem.lower()
        score = 0
        for tag in prompt_tags:
            keywords = keyword_groups[tag]
            for kw in keywords:
                if kw in img_name:
                    score += 2
                    break
            # Checar se o nome do grupo esta no nome
            if tag in img_name:
                score += 3
        if score > best_score:
            best_score = score
            best_img = img_path

    return best_img


def clear_cache():
    """Limpa cache de embeddings (chamar quando imagens mudam)."""
    global _image_embeddings_cache
    _image_embeddings_cache = {}
