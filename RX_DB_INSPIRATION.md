# Django setup for local-first sync (with RxDB or similar)

```python
# models.py
import uuid
from django.db import models

class SyncedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

class Item(SyncedModel):
    name = models.CharField(max_length=200)
    content = models.TextField()

# serializers.py
from rest_framework import serializers
from .models import Item

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ['id', 'name', 'content', 'updated_at', 'deleted']

# views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Item
from .serializers import ItemSerializer

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    @action(detail=False, methods=['get'])
    def changes(self, request):
        """
        GET /api/items/changes/?since=2025-10-01T12:00:00Z&limit=100
        Returns all items updated after `since`.
        """
        since = request.query_params.get('since')
        limit = int(request.query_params.get('limit', 100))
        qs = self.queryset
        if since:
            qs = qs.filter(updated_at__gt=since)
        qs = qs.order_by('updated_at')[:limit]
        serializer = self.get_serializer(qs, many=True)
        checkpoint = qs.last().updated_at if qs else since
        return Response({
            "documents": serializer.data,
            "checkpoint": checkpoint
        })

# urls.py
from rest_framework.routers import DefaultRouter
from .views import ItemViewSet

router = DefaultRouter()
router.register(r'items', ItemViewSet, basename='item')

urlpatterns = router.urls
```