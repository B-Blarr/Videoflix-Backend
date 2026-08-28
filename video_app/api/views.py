"""Views for the video list and the HLS playlist and segments."""

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.views import APIView

from video_app.models import Video
from video_app.utils import hls_file_path, hls_segment_path
from .serializers import VideoSerializer


class VideoListView(generics.ListAPIView):
    """Return the converted videos, newest first, as a flat unpaginated list."""

    queryset = Video.objects.filter(status=Video.Status.DONE)
    serializer_class = VideoSerializer


class HLSPlaylistView(APIView):
    """Serve the HLS playlist of one video in one resolution."""

    def get(self, request, movie_id, resolution):
        """Return the m3u8 playlist, or 404 if it is not available."""
        get_object_or_404(Video, pk=movie_id)
        path = hls_file_path(movie_id, resolution, 'index.m3u8')
        if path is None:
            raise Http404
        return FileResponse(
            open(path, 'rb'),
            content_type='application/vnd.apple.mpegurl',
        )


class HLSSegmentView(APIView):
    """Serve a single segment of an HLS stream."""

    def get(self, request, movie_id, resolution, segment):
        """Return one .ts segment as video/MP2T, or 404 if it is missing."""
        get_object_or_404(Video, pk=movie_id)
        path = hls_segment_path(movie_id, resolution, segment)
        if path is None:
            raise Http404
        return FileResponse(open(path, 'rb'), content_type='video/MP2T')
