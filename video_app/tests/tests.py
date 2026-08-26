import json
import subprocess
import os
import shutil
import tempfile

from unittest.mock import patch
from django.test import TestCase, SimpleTestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from video_app.models import Video
from video_app.utils import (
    probe_video,
    VideoProbeError,
    convert_video,
    build_hls_command,
)


User = get_user_model()
TEST_MEDIA = tempfile.mkdtemp()

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



@override_settings(MEDIA_ROOT=TEST_MEDIA)
class HLSViewTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='v@test.de', email='v@test.de',
            password='SuperSecret123!')
        self.client.cookies['access_token'] = str(
            RefreshToken.for_user(self.user).access_token)
        self.video = Video.objects.create(
            title='Test', description='Desc', category='Drama',
            video_file='videos/test.mp4', thumbnail='thumbnails/test.jpg')
        folder = os.path.join(
            TEST_MEDIA, 'videos', str(self.video.id), '480p')
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, 'index.m3u8'), 'w') as playlist:
            playlist.write('#EXTM3U')
        with open(os.path.join(folder, 'seg000.ts'), 'wb') as segment:
            segment.write(b'\x47')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_playlist_returns_m3u8(self):
        url = reverse('video_playlist', args=[self.video.id, '480p'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'], 'application/vnd.apple.mpegurl')

    def test_segment_returns_ts(self):
        url = reverse(
            'video_segment', args=[self.video.id, '480p', 'seg000.ts'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'video/MP2T')

    def test_unknown_resolution_returns_404(self):
        url = reverse('video_playlist', args=[self.video.id, '999p'])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_video_list_has_absolute_thumbnail_url(self):
        response = self.client.get(reverse('video_list'))
        self.assertTrue(
            response.data[0]['thumbnail_url'].startswith('http://'))


class ConvertVideoTests(TestCase):

    def setUp(self):
        self.video = Video.objects.create(
            title='Test', description='Desc', category='Drama',
            video_file='videos/test.mp4')

    @patch('video_app.utils.create_thumbnail')
    @patch('video_app.utils.encode_variant')
    @patch('video_app.utils.probe_video')
    def test_convert_video_sets_status_done(
            self, mock_probe, mock_encode, mock_thumb):
        mock_probe.return_value = {
            'width': 1920, 'height': 1080, 'fps': 25.0, 'duration': 8.0}
        convert_video(self.video.id)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, 'done')
        self.assertEqual(self.video.available_resolutions, [480, 720, 1080])
        self.assertEqual(self.video.duration, 8.0)
        self.assertEqual(mock_encode.call_count, 3)

    @patch('video_app.utils.probe_video')
    def test_convert_video_sets_status_failed(self, mock_probe):
        mock_probe.side_effect = VideoProbeError('kaputt')
        convert_video(self.video.id)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, 'failed')


class BuildHlsCommandTests(SimpleTestCase):

    def test_gop_is_calculated_from_fps(self):
        cmd = build_hls_command('/in.mp4', '/out', 480, 25.0)
        self.assertEqual(cmd[cmd.index('-g') + 1], '50')
        self.assertEqual(cmd[cmd.index('-keyint_min') + 1], '50')

    def test_scale_filter_uses_given_height(self):
        cmd = build_hls_command('/in.mp4', '/out', 720, 25.0)
        self.assertIn('scale=-2:720', cmd)