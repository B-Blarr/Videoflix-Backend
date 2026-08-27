from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from video_app.models import Video

class VideoSerializer(serializers.ModelSerializer):

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            'id', 'created_at', 'title', 'description', 'thumbnail_url', 
            'category']

    @extend_schema_field(OpenApiTypes.URI)
    def get_thumbnail_url(self, obj):
        if not obj.thumbnail:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.thumbnail.url)

