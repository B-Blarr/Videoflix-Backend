import json
import subprocess


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