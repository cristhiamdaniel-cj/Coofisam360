from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from .serializers import UserSerializer, UserCreateSerializer

class UserListView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]  # Temporal para testing
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def api_status(request):
    return Response({
        'status': 'API funcionando correctamente',
        'version': '1.0',
        'mensaje': 'API lista para desarrollo frontend',
        'endpoints': {
            'publicos': [
                '/api/v1/status/',
                '/api/v1/users/ (GET, POST)',
            ],
            'autenticados': [
                '/api/v1/profile/',
                '/api/v1/users/{id}/ (GET, PUT, DELETE)'
            ]
        },
        'autenticacion': {
            'tipo': 'Token',
            'header': 'Authorization: Token tu_token_aqui',
            'ejemplo_token': 'a4c54ef00b2fc005a533c137d153949871f12f22'
        }
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def api_test_data(request):
    """Endpoint de prueba con datos mock para el frontend"""
    return Response({
        'usuarios_ejemplo': [
            {'id': 1, 'nombre': 'Juan Pérez', 'email': 'juan@coofisam.com'},
            {'id': 2, 'nombre': 'María González', 'email': 'maria@coofisam.com'}
        ],
        'configuracion': {
            'cors_habilitado': True,
            'base_url': 'http://IP_SERVIDOR:8000/api/v1/'
        }
    })
