"""Tests for HLS probing, conversion and delivery in video_app."""

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
    create_thumbnail,
)


User = get_user_model()
TEST_MEDIA = tempfile.mkdtemp()

FFPROBE_JSON = json.dumps({
    'streams': [{'width': 1920, 'height': 1080, 'r_frame_rate': '25/1'}],
    'format': {'duration': '8.0'},
})


class ProbeVideoTests(TestCase):
    """Reading video metadata out of the JSON that ffprobe prints."""

    @patch('video_app.utils.subprocess.run')
    def test_probe_video_returns_metadata(self, mock_run):
        """Probing returns height, frame rate and duration as numbers."""
        mock_run.return_value.stdout = FFPROBE_JSON
        info = probe_video('/fake/video.mp4')
        self.assertEqual(info['height'], 1080)
        self.assertEqual(info['fps'], 25.0)
        self.assertEqual(info['duration'], 8.0)

    @patch('video_app.utils.subprocess.run')
    def test_probe_video_without_video_track_raises(self, mock_run):
        """A file without a video track is rejected, not accepted."""
        mock_run.return_value.stdout = json.dumps(
            {'streams': [], 'format': {}})
        with self.assertRaises(VideoProbeError):
            probe_video('/fake/video.mp4')

    @patch('video_app.utils.subprocess.run')
    def test_probe_video_failure_raises(self, mock_run):
        """A failing ffprobe call is reported as VideoProbeError."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'ffprobe', stderr='error')
        with self.assertRaises(VideoProbeError):
            probe_video('/fake/video.mp4')


@override_settings(MEDIA_ROOT=TEST_MEDIA)
class HLSViewTests(APITestCase):
    """Delivery of playlists, segments and the video list to a client."""

    def setUp(self):
        """Create an authenticated client and fake HLS files on disk."""
        self.user = User.objects.create_user(
            username='v@test.de', email='v@test.de',
            password='SuperSecret123!')
        self.client.cookies['access_token'] = str(
            RefreshToken.for_user(self.user).access_token)
        self.video = Video.objects.create(
            title='Test', description='Desc', category='Drama',
            video_file='videos/test.mp4', thumbnail='thumbnails/test.jpg',
            status=Video.Status.DONE)
        Video.objects.create(
            title='Still converting', description='Desc', category='Drama',
            video_file='videos/pending.mp4')
        self.write_hls_files()

    def write_hls_files(self):
        """Put a playlist and one segment where the views look for them."""
        folder = os.path.join(
            TEST_MEDIA, 'videos', str(self.video.id), '480p')
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, 'index.m3u8'), 'w') as playlist:
            playlist.write('#EXTM3U')
        with open(os.path.join(folder, 'seg000.ts'), 'wb') as segment:
            segment.write(b'\x47')

    @classmethod
    def tearDownClass(cls):
        """Remove the temporary media tree shared by all these tests."""
        shutil.rmtree(TEST_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def test_playlist_returns_m3u8(self):
        """A playlist is served with the content type hls.js expects."""
        url = reverse('video_playlist', args=[self.video.id, '480p'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'], 'application/vnd.apple.mpegurl')

    def test_segment_returns_ts(self):
        """A segment is served as binary video/MP2T, not as text."""
        url = reverse(
            'video_segment', args=[self.video.id, '480p', 'seg000.ts'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'video/MP2T')

    def test_unknown_resolution_returns_404(self):
        """An unknown resolution answers 404 instead of touching disk."""
        url = reverse('video_playlist', args=[self.video.id, '999p'])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_video_list_has_absolute_thumbnail_url(self):
        """Thumbnail URLs are absolute so the frontend can load them."""
        response = self.client.get(reverse('video_list'))
        self.assertTrue(
            response.data[0]['thumbnail_url'].startswith('http://'))


@override_settings(MEDIA_ROOT=TEST_MEDIA)
class ConvertVideoTests(TestCase):
    """Status bookkeeping around a conversion run, with ffmpeg mocked."""

    def setUp(self):
        """Create a video row pointing at a source file name."""
        self.video = Video.objects.create(
            title='Test', description='Desc', category='Drama',
            video_file='videos/test.mp4')

    @patch('video_app.utils.create_thumbnail')
    @patch('video_app.utils.encode_variant')
    @patch('video_app.utils.probe_video')
    def test_convert_video_sets_status_done(
            self, mock_probe, mock_encode, mock_thumb):
        """A finished run stores status, duration and all resolutions."""
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
        """A failed probe leaves the video marked failed and re-raises."""
        mock_probe.side_effect = VideoProbeError('kaputt')
        with self.assertRaises(VideoProbeError):
            convert_video(self.video.id)
        self.video.refresh_from_db()
        self.assertEqual(self.video.status, 'failed')


class BuildHlsCommandTests(SimpleTestCase):
    """The ffmpeg argument list that is built for one HLS variant."""

    def test_gop_is_calculated_from_fps(self):
        """The GOP follows the frame rate, keeping segment cuts clean."""
        cmd = build_hls_command('/in.mp4', '/out', 480, 25.0)
        self.assertEqual(cmd[cmd.index('-g') + 1], '50')
        self.assertEqual(cmd[cmd.index('-keyint_min') + 1], '50')

    def test_scale_filter_uses_given_height(self):
        """The scale filter keeps the aspect ratio at the wanted height."""
        cmd = build_hls_command('/in.mp4', '/out', 720, 25.0)
        self.assertIn('scale=-2:720', cmd)


@override_settings(MEDIA_ROOT=TEST_MEDIA)
class CreateThumbnailTests(TestCase):
    """Where the thumbnail lands and which frame it is taken from."""

    def setUp(self):
        """Create a video row to hang the generated thumbnail on."""
        self.video = Video.objects.create(
            title='T', description='D', category='Drama',
            video_file='videos/test.mp4')

    @patch('video_app.utils.subprocess.run')
    def test_thumbnail_path_and_position(self, mock_run):
        """The thumbnail is named after the video and cut at its middle."""
        create_thumbnail(self.video, 10.0)
        self.assertEqual(
            self.video.thumbnail.name, f'thumbnails/{self.video.id}.jpg')
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[cmd.index('-ss') + 1], '5.0')
