from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render
from .models import Recommendation
from .serializers import RecommendationSerializer

class RecommendationViewSet(viewsets.ModelViewSet):
    queryset = Recommendation.objects.all()
    serializer_class = RecommendationSerializer
    
    @action(detail=False, methods=['get'])
    def for_user(self, request):
        """Get recommendations for current user"""
        if request.user.is_authenticated:
            recommendations = Recommendation.objects.filter(user=request.user)
            serializer = self.get_serializer(recommendations, many=True)
            return Response(serializer.data)
        return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
