import json, os
import subprocess
from django.conf import settings

from .models import Video


class VideoProbeError(Exception):
    """Raised when video metadata cannot be read."""
    pass


def probe_video(path):
    result = run_ffprobe(path)
    data = json.loads(result.stdout)
    if not data.get('streams'):
            raise VideoProbeError('no video track found')
    stream = data['streams'][0]
    return {
        'width': stream['width'],
        'height': stream['height'],
        'fps': parse_fps(stream['r_frame_rate']),
        'duration': float(data['format']['duration']),
    }


def run_ffprobe(path):
    try:
        result = subprocess.run(
            [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,r_frame_rate',
                '-show_entries', 'format=duration',
                '-of', 'json',
                path,
            ],
            capture_output=True, text=True, check=True, timeout=10)
    except subprocess.TimeoutExpired:
        raise VideoProbeError(f'ffprobe timeout: {path}')
    except subprocess.CalledProcessError as e:
        raise VideoProbeError(f'ffprobe failed: {e.stderr}')
    except FileNotFoundError:
        raise VideoProbeError('ffprobe not found')
    return result


def parse_fps(raw):
    num, den = raw.split('/')
    return int(num) / int(den)


def build_hls_command(input_path, output_dir, height, fps):
    gop = round(fps * settings.HLS_GOP_SECONDS)

    return [
        'ffmpeg', '-y',
        '-i', input_path,
        '-vf', f'scale=-2:{height}',
        '-c:v', 'libx264',
        '-preset', settings.HLS_PRESET,
        '-crf', str(settings.HLS_CRF),
        '-g', str(gop),
        '-keyint_min', str(gop),
        '-sc_threshold', '0',
        '-c:a', 'aac', 
        '-b:a', settings.HLS_AUDIO_BITRATE,
        '-hls_time', str(settings.HLS_SEGMENT_SECONDS),
        '-hls_playlist_type', 'vod', 
        '-hls_segment_filename', os.path.join(output_dir, 'seg%03d.ts'),
        os.path.join(output_dir, 'index.m3u8'),
    ]


def convert_video(video_id):
    video = Video.objects.get(id=video_id)
    video.status = "processing"
    video.save()
    try:
        run_conversion(video)
        video.status = 'done'
    except(VideoProbeError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        video.status = 'failed'
    finally:
        video.save()

    
def run_conversion(video):
    info = probe_video(video.video_file.path)
    base_dir = os.path.join(settings.MEDIA_ROOT, "videos", str(video.id))
    heights = []
    for height in settings.HLS_RESOLUTIONS:
        if height <= info['height']:
            heights.append(height)
    create_thumbnail(video, info['duration'])
    for height in heights:
        encode_variant(video.video_file.path, base_dir, height, info['fps'])

    video.available_resolutions = heights
    video.duration = info['duration']


def encode_variant(input_path, base_dir, height, fps):
    output_dir = os.path.join(base_dir, f'{height}p')
    os.makedirs(output_dir, exist_ok=True)
    cmd = build_hls_command(input_path, output_dir, height, fps)
    subprocess.run(cmd, check=True, timeout=3600)


def build_thumbnail_command(input_path, output_path, position):

    return [
        'ffmpeg', '-y',
        '-ss', str(position),
        '-i', input_path,
        '-vf', 'thumbnail=300,scale=-2:360',
        '-frames:v', '1',
        output_path,
    ]    


def create_thumbnail(video, duration):
    rel_path = f'thumbnails/{video.id}.jpg'
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    cmd = build_thumbnail_command(video.video_file.path, abs_path, duration / 2)
    subprocess.run(cmd, check=True, timeout=60)
    video.thumbnail = rel_path


def hls_dir(video_id):
    """Return the directory that holds the HLS files of a video."""
    return os.path.join(settings.MEDIA_ROOT, 'videos', str(video_id))


def hls_file_path(video_id, resolution, filename):
    """Return the path of an HLS file, or None if it is not available."""
    if resolution not in {f'{height}p' for height in settings.HLS_RESOLUTIONS}:
        return None
    path = os.path.join(hls_dir(video_id), resolution, filename)
    return path if os.path.isfile(path) else None   