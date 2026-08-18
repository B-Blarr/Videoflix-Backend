import json, os
import subprocess
from django.conf import settings

from .models import Video


def probe_video(path):

    result = subprocess.run(
        [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate',
            '-show_entries', 'format=duration',
            '-of', 'json',
            path,
        ],
        capture_output=True, text=True, check=True, timeout=10,

    )
    data = json.loads(result.stdout)
    stream = data['streams'][0]

    num, den = stream['r_frame_rate'].split('/')
    fps = int(num) / int(den)

    return {
        'width': stream['width'],
        'height': stream['height'],
        'fps': fps,
        'duration': float(data['format']['duration']),
    }


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