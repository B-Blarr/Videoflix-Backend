"""URL routes for the video list and the HLS playlist and segments."""

from django.urls import path

from .views import VideoListView, HLSPlaylistView, HLSSegmentView


urlpatterns = [
    path('video/', VideoListView.as_view(), name='video_list'),
    path(
        'video/<int:movie_id>/<str:resolution>/index.m3u8',
        HLSPlaylistView.as_view(), name='video_playlist'),
    path(
        'video/<int:movie_id>/<str:resolution>/<str:segment>/',
        HLSSegmentView.as_view(), name='video_segment'),
    path(
        'video/<int:movie_id>/<str:resolution>/<str:segment>',
        HLSSegmentView.as_view()),
]
