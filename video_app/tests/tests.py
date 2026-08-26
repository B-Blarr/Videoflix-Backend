import json
import subprocess
from unittest.mock import patch

from django.test import TestCase

from video_app.utils import probe_video, VideoProbeError


FFPROBE_JSON = json.dumps({
    'streams': [{'width': 1920, 'height': 1080, 'r_frame_rate': '25/1'}],
    'format': {'duration': '8.0'},
})


class ProbeVideoTests(TestCase):

    @patch('video_app.utils.subprocess.run')
    def test_probe_video_returns_metadata(self, mock_run):
        mock_run.return_value.stdout = FFPROBE_JSON
        info = probe_video('/fake/video.mp4')
        self.assertEqual(info['height'], 1080)
        self.assertEqual(info['fps'], 25.0)
        self.assertEqual(info['duration'], 8.0)

    @patch('video_app.utils.subprocess.run')
    def test_probe_video_without_video_track_raises(self, mock_run):
        mock_run.return_value.stdout = json.dumps({'streams': [], 'format': {}})
        with self.assertRaises(VideoProbeError):
            probe_video('/fake/video.mp4')

    @patch('video_app.utils.subprocess.run')
    def test_probe_video_failure_raises(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'ffprobe', stderr='error')
        with self.assertRaises(VideoProbeError):
            probe_video('/fake/video.mp4')

            