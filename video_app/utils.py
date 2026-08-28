"""FFmpeg helpers for probing, thumbnails and HLS conversion."""

import json, os, shutil
import subprocess
from django.conf import settings
from django.core.files.storage import default_storage

from .models import Video


class VideoProbeError(Exception):
    """Raised when video metadata cannot be read."""
    pass


def probe_video(path):
    """Return width, height, fps and duration of the source file."""
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


def build_ffprobe_command(path):
    """Return the ffprobe call that reads size, frame rate and duration."""
    return [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,r_frame_rate',
        '-show_entries', 'format=duration',
        '-of', 'json',
        path,
    ]


def run_ffprobe(path):
    """Run ffprobe and raise VideoProbeError on any failure."""
    try:
        return subprocess.run(
            build_ffprobe_command(path),
            capture_output=True, text=True, check=True, timeout=10)
    except subprocess.TimeoutExpired:
        raise VideoProbeError(f'ffprobe timeout: {path}')
    except subprocess.CalledProcessError as e:
        raise VideoProbeError(f'ffprobe failed: {e.stderr}')
    except FileNotFoundError:
        raise VideoProbeError('ffprobe not found')


def parse_fps(raw):
    """Turn a rational frame rate such as 30000/1001 into a float."""
    num, den = raw.split('/')
    return int(num) / int(den)


def build_hls_command(input_path, output_dir, height, fps):
    """Build the ffmpeg call for one HLS variant with a fixed GOP."""
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
    """Convert one video to HLS and keep its status in sync."""
    video = Video.objects.get(id=video_id)
    Video.objects.filter(pk=video.pk).update(status='processing')
    try:
        run_conversion(video)
        video.status = 'done'
    except Exception:
        video.status = 'failed'
        raise
    finally:
        save_conversion_result(video)


def save_conversion_result(video):
    """Write the job's result back, but only if the video still exists."""
    Video.objects.filter(pk=video.pk).update(
        status=video.status,
        thumbnail=video.thumbnail.name,
        duration=video.duration,
        available_resolutions=video.available_resolutions,
    )


def run_conversion(video):
    """Build the thumbnail and every HLS variant from scratch."""
    info = probe_video(video.video_file.path)
    base_dir = hls_dir(video.id)
    shutil.rmtree(base_dir, ignore_errors=True)
    create_thumbnail(video, info['duration'])
    for height in settings.HLS_RESOLUTIONS:
        encode_variant(video.video_file.path, base_dir, height, info['fps'])
    video.available_resolutions = list(settings.HLS_RESOLUTIONS)
    video.duration = info['duration']


def encode_variant(input_path, base_dir, height, fps):
    """Encode one resolution, even when it upscales the source."""
    output_dir = os.path.join(base_dir, f'{height}p')
    os.makedirs(output_dir, exist_ok=True)
    cmd = build_hls_command(input_path, output_dir, height, fps)
    subprocess.run(cmd, check=True, timeout=settings.HLS_ENCODE_TIMEOUT)


def build_thumbnail_command(input_path, output_path, position):
    """Build the ffmpeg call that grabs a single frame as JPEG."""

    return [
        'ffmpeg', '-y',
        '-ss', str(position),
        '-i', input_path,
        '-vf', 'thumbnail=300,scale=-2:360',
        '-frames:v', '1',
        '-update', '1',
        output_path,
    ]


def create_thumbnail(video, duration):
    """Grab a frame from the middle of the video as thumbnail."""
    rel_path = f'thumbnails/{video.id}.jpg'
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    cmd = build_thumbnail_command(
        video.video_file.path, abs_path, duration / 2)
    subprocess.run(cmd, check=True, timeout=settings.HLS_THUMBNAIL_TIMEOUT)
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


def drop_replaced_source(name):
    """Delete a source file that a new upload replaced."""
    if name:
        default_storage.delete(name)


def hls_segment_path(video_id, resolution, segment):
    """Return the segment path, or None if it is not a readable .ts file."""
    if not segment.endswith('.ts'):
        return None
    return hls_file_path(video_id, resolution, segment)


def remove_video_files(video):
    """Delete the HLS folder, the source file and the thumbnail of a video."""
    shutil.rmtree(hls_dir(video.id), ignore_errors=True)
    video.video_file.delete(save=False)
    video.thumbnail.delete(save=False)
