"""Serializers for the video list endpoint."""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from video_app.models import Video

class VideoSerializer(serializers.ModelSerializer):
    """Video payload of the list endpoint, thumbnail included."""

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        """Expose the fields in the order the endpoint doc lists them."""
        model = Video
        fields = [
            'id', 'created_at', 'title', 'description', 'thumbnail_url', 
            'category']

    @extend_schema_field(OpenApiTypes.URI)
    def get_thumbnail_url(self, obj):
        """Return an absolute URL the frontend can use as img src, or None."""
        if not obj.thumbnail:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.thumbnail.url)

