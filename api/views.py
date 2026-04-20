"""REST API endpoints that reuse the shared field services layer."""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.http import Http404
from fields.models import Field, FieldUpdate
from fields.services import create_field_update, get_admin_summary, get_agent_summary
from .serializers import FieldSerializer, FieldUpdateSerializer, CreateFieldUpdateSerializer, UserSerializer


class LoginAPIView(APIView):
    """Issues token authentication responses for API clients."""

    permission_classes = []
    authentication_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            # Token auth keeps the API stateless for mobile and external clients.
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
            })
        return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)


class FieldListCreateAPIView(generics.ListCreateAPIView):
    """Lists accessible fields and lets admins create new ones."""

    serializer_class = FieldSerializer

    def get_queryset(self):
        # Related rows are loaded once to avoid repeated queries while serializing.
        qs = Field.objects.select_related('assigned_agent').prefetch_related('updates')
        if self.request.user.is_field_agent:
            qs = qs.filter(assigned_agent=self.request.user)
        return qs

    def perform_create(self, serializer):
        if not self.request.user.is_admin_role:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only admins can create fields.')
        serializer.save()


class FieldDetailAPIView(generics.RetrieveUpdateAPIView):
    """Retrieves field details and allows admin-only metadata updates."""

    serializer_class = FieldSerializer

    def get_object(self):
        try:
            obj = Field.objects.select_related('assigned_agent').prefetch_related('updates').get(pk=self.kwargs['pk'])
        except Field.DoesNotExist:
            raise Http404
        if self.request.user.is_field_agent and obj.assigned_agent != self.request.user:
            # Return 404 instead of 403 so other agents cannot infer field existence.
            raise Http404
        return obj

    def update(self, request, *args, **kwargs):
        if not request.user.is_admin_role:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only admins can update field metadata.')
        return super().update(request, *args, **kwargs)


class FieldUpdateCreateAPIView(APIView):
    """Creates or lists stage updates for a field using the shared service layer."""

    def post(self, request, pk):
        try:
            field = Field.objects.get(pk=pk)
        except Field.DoesNotExist:
            raise Http404
        if request.user.is_field_agent and field.assigned_agent != request.user:
            # Return 404 instead of 403 so other agents cannot infer field existence.
            raise Http404

        serializer = CreateFieldUpdateSerializer(data=request.data)
        if serializer.is_valid():
            # Update creation stays centralized so HTML and API paths behave identically.
            update = create_field_update(
                field=field,
                user=request.user,
                new_stage=serializer.validated_data['new_stage'],
                notes=serializer.validated_data.get('notes', ''),
            )
            return Response(FieldUpdateSerializer(update).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk):
        updates = FieldUpdate.objects.filter(field_id=pk).select_related('updated_by')
        serializer = FieldUpdateSerializer(updates, many=True)
        return Response(serializer.data)


class AdminDashboardAPIView(APIView):
    """Returns aggregate metrics for the admin dashboard."""

    def get(self, request):
        if not request.user.is_admin_role:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Admin only.')
        summary = get_admin_summary()
        return Response({
            'total_fields': summary['total'],
            'active_fields': summary['active'],
            'at_risk_fields': summary['at_risk'],
            'completed_fields': summary['completed'],
        })


class AgentDashboardAPIView(APIView):
    """Returns aggregate metrics for the authenticated field agent."""

    def get(self, request):
        summary = get_agent_summary(request.user)
        return Response({
            'total_assigned': summary['total'],
            'active': summary['active'],
            'at_risk': summary['at_risk'],
            'completed': summary['completed'],
        })
