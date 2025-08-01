from rest_framework import permissions
import logging
from .models import Permission


logger = logging.getLogger(__name__)

class HasRolePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        perm_name = getattr(view, 'permission_name', None)
        if not perm_name:
            logger.debug("No permission_name on view")
            return False
        
        try:
            permission = Permission.objects.get(name=perm_name)
            user_role = getattr(request.user, 'role', None)
            
            logger.debug(f"User role: {user_role}, Permission role: {permission.role}")
            
            if user_role is None:
                logger.debug("User has no role assigned")
                return False
            
            if user_role == permission.role:
                return True
            else:
                logger.debug("User role does not match permission role")
                return False
        
        except Permission.DoesNotExist:
            logger.debug(f"Permission {perm_name} does not exist")
            return False
        except Exception as e:
            logger.exception("Unexpected error in permission check")
            return False
        
from django.contrib.auth import get_user_model

User = get_user_model()

