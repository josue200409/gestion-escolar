import os
import re
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError

DOCUMENTOS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'}
IMAGENES = {'.jpg', '.jpeg', '.png', '.webp'}
VIDEOS = {'.mp4', '.mov', '.webm'}
PERMITIDAS = DOCUMENTOS | IMAGENES | VIDEOS

_ZIP = [b'PK\x03\x04']
_OLE = [b'\xd0\xcf\x11\xe0']
FIRMAS = {
    '.pdf': [b'%PDF'],
    '.png': [b'\x89PNG'],
    '.jpg': [b'\xff\xd8\xff'],
    '.jpeg': [b'\xff\xd8\xff'],
    '.webp': [b'RIFF'],
    '.docx': _ZIP, '.xlsx': _ZIP, '.pptx': _ZIP,
    '.doc': _OLE, '.xls': _OLE, '.ppt': _OLE,
    '.webm': [b'\x1a\x45\xdf\xa3'],
}


def validar_archivo(archivo):
    """Comprueba extensión, tamaño y que el contenido corresponda al tipo."""
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in PERMITIDAS:
        raise ValidationError(
            'Tipo de archivo no permitido. Usa PDF, Word, Excel, PowerPoint, '
            'imágenes (JPG, PNG, WEBP) o video (MP4, MOV, WEBM).'
        )

    limite_mb = settings.VIDEO_MAX_MB if ext in VIDEOS else settings.ARCHIVO_MAX_MB
    if archivo.size > limite_mb * 1024 * 1024:
        raise ValidationError(f'El archivo pesa demasiado. El máximo para este tipo es {limite_mb} MB.')

    archivo.seek(0)
    cabecera = archivo.read(12)
    archivo.seek(0)

    firmas = FIRMAS.get(ext)
    if firmas and not any(cabecera.startswith(f) for f in firmas):
        raise ValidationError('El archivo está dañado o no es del tipo que indica su extensión.')
    if ext == '.mp4' and cabecera[4:8] != b'ftyp':
        raise ValidationError('El archivo está dañado o no es del tipo que indica su extensión.')


def extraer_id_youtube(url):
    """Devuelve el identificador de un video de YouTube, o None si no es válido."""
    if not url:
        return None
    try:
        p = urlparse(url.strip())
    except ValueError:
        return None
    if p.scheme not in ('http', 'https'):
        return None

    host = (p.hostname or '').lower()
    candidato = ''
    if host == 'youtu.be':
        candidato = p.path.lstrip('/').split('/')[0]
    elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        if p.path == '/watch':
            candidato = parse_qs(p.query).get('v', [''])[0]
        elif p.path.startswith(('/embed/', '/shorts/')):
            partes = p.path.split('/')
            candidato = partes[2] if len(partes) > 2 else ''
    return candidato if re.fullmatch(r'[A-Za-z0-9_-]{11}', candidato) else None