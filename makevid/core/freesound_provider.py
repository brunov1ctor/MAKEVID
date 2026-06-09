"""Freesound Provider - Busca e baixa sons reais do Freesound.org.

Busca semantica: AudioDirector gera queries → Freesound retorna sons reais gravados.
Qualidade muito superior a IA generativa para SFX/ambiencia.
"""

import logging
import os
import requests
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# API Key (variavel de ambiente FREESOUND_API_KEY)
FREESOUND_CLIENT_ID = "4B7zj5Q5IywT0Kdo8MOP"
FREESOUND_API_KEY = os.environ.get("FREESOUND_API_KEY", "")
FREESOUND_BASE_URL = "https://freesound.org/apiv2"


def search_sounds(query: str, max_duration: float = 10.0, num_results: int = 3) -> List[Dict]:
    """Busca sons no Freesound por query textual.
    
    Retorna lista de dicts com: id, name, duration, url, preview_url
    Randomiza a pagina para variar resultados a cada busca.
    Raises ValueError se API key nao configurada.
    """
    if not FREESOUND_API_KEY:
        raise ValueError("FREESOUND_API_KEY nao configurada")
    import random
    # Randomizar pagina para variar resultados
    page = random.randint(1, 3)
    params = {
        "query": query,
        "filter": f"duration:[0.5 TO {max_duration}]",
        "sort": "score",
        "fields": "id,name,duration,previews,avg_rating,num_downloads",
        "page_size": max(num_results * 3, 9),
        "page": page,
        "token": FREESOUND_API_KEY,
    }

    try:
        r = requests.get(f"{FREESOUND_BASE_URL}/search/text/", params=params, timeout=10)
        if r.status_code != 200:
            logger.error(f"Freesound search error: {r.status_code} {r.text[:100]}")
            return []

        data = r.json()
        all_results = []
        for sound in data.get("results", []):
            previews = sound.get("previews", {})
            preview_url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3", "")
            all_results.append({
                "id": sound["id"],
                "name": sound["name"],
                "duration": sound["duration"],
                "preview_url": preview_url,
                "rating": sound.get("avg_rating", 0),
                "downloads": sound.get("num_downloads", 0),
            })

        # Se pagina aleatoria nao tem resultados, tentar pagina 1
        if not all_results and page > 1:
            params["page"] = 1
            r = requests.get(f"{FREESOUND_BASE_URL}/search/text/", params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for sound in data.get("results", []):
                    previews = sound.get("previews", {})
                    preview_url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3", "")
                    all_results.append({
                        "id": sound["id"],
                        "name": sound["name"],
                        "duration": sound["duration"],
                        "preview_url": preview_url,
                        "rating": sound.get("avg_rating", 0),
                        "downloads": sound.get("num_downloads", 0),
                    })

        # Randomizar e retornar num_results
        random.shuffle(all_results)
        return all_results[:num_results]

    except Exception as e:
        logger.error(f"Freesound search exception: {e}")
        return []


def download_sound(sound_id: int, output_path: Path) -> Optional[Path]:
    """Baixa um som do Freesound pelo ID (preview HQ em mp3).
    
    Usa o preview (nao precisa OAuth2, so API key).
    """
    try:
        params = {"token": FREESOUND_API_KEY}
        r = requests.get(f"{FREESOUND_BASE_URL}/sounds/{sound_id}/", params=params, timeout=10)
        if r.status_code != 200:
            logger.error(f"Freesound sound info error: {r.status_code}")
            return None

        data = r.json()
        previews = data.get("previews", {})
        url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
        if not url:
            return None

        return download_preview(url, output_path)

    except Exception as e:
        logger.error(f"Freesound download exception: {e}")
        return None


def download_preview(preview_url: str, output_path: Path) -> Optional[Path]:
    """Baixa o preview de um som diretamente pela URL."""
    try:
        r = requests.get(preview_url, timeout=30)
        if r.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(r.content)
            logger.info(f"Downloaded: {output_path.name} ({len(r.content)} bytes)")
            return output_path
        else:
            logger.error(f"Download failed: {r.status_code}")
            return None
    except Exception as e:
        logger.error(f"Download exception: {e}")
        return None


def search_and_download(query: str, output_path: Path, max_duration: float = 10.0) -> Optional[Path]:
    """Busca + baixa o melhor resultado para a query.
    
    Retorna path do arquivo MP3 baixado.
    """
    results = search_sounds(query, max_duration=max_duration, num_results=1)
    if not results:
        logger.warning(f"No results for: '{query}'")
        return None

    best = results[0]
    if best["preview_url"]:
        mp3_path = output_path.with_suffix(".mp3")
        return download_preview(best["preview_url"], mp3_path)
    return None


def search_and_download_layers(queries: List[str], output_dir: Path, max_duration: float = 10.0) -> List[Path]:
    """Busca e baixa multiplos sons (layering).
    
    Retorna lista de paths baixados.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, query in enumerate(queries):
        out = output_dir / f"layer_{i:02d}"
        result = search_and_download(query, out, max_duration=max_duration)
        if result:
            paths.append(result)
    return paths
