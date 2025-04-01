from rest_framework.permissions import BasePermission

class IsUser(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj == request.user

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'
    
class IsPatient(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'patient'