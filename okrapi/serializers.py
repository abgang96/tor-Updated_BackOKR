from rest_framework import serializers
from .models import OKR, Task, User, Department, BusinessUnit, BusinessUnitOKRMapping, OkrUserMapping, TaskChallenges

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class BusinessUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessUnit
        fields = ['business_unit_id', 'business_unit_name']

class BusinessUnitOKRMappingSerializer(serializers.ModelSerializer):
    business_unit = BusinessUnitSerializer(read_only=True)
    
    class Meta:
        model = BusinessUnitOKRMapping
        fields = ['business_unit']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'name', 'email', 'employee_id', 'role', 'level']

class OkrUserMappingSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = OkrUserMapping
        fields = ['id', 'user', 'okr', 'is_primary', 'created_at', 'user_details']
        extra_kwargs = {
            'user': {'write_only': True},
            'okr': {'write_only': True}
        }

# Make sure to update the OKRSerializer to include business units
class OKRSerializer(serializers.ModelSerializer):
    assigned_users_details = serializers.SerializerMethodField()
    business_units = BusinessUnitSerializer(many=True, read_only=True)
    business_unit_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        write_only=True, 
        required=False
    )
    assigned_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    primary_user_id = serializers.IntegerField(required=False, write_only=True)
    
    class Meta:
        model = OKR
        fields = [
            'okr_id', 'name', 'description', 'assumptions', 'parent_okr', 
            'department', 'start_date', 'due_date', 'status', 
            'progress_percent', 'assigned_users_details',
            'business_units', 'business_unit_ids', 'assigned_user_ids', 'primary_user_id',
            'isMeasurable',
        ]
    
    def get_assigned_users_details(self, obj):
        user_mappings = obj.user_mappings.all().select_related('user')
        return [
            {
                'user_id': mapping.user.user_id,
                'name': mapping.user.name,
                'is_primary': mapping.is_primary
            }
            for mapping in user_mappings
        ]
    
    def create(self, validated_data):
        business_unit_ids = validated_data.pop('business_unit_ids', [])
        
        # Handle user assignments
        assigned_user_ids = validated_data.pop('assigned_user_ids', [])
        primary_user_id = validated_data.pop('primary_user_id', None)
        
        # Create the OKR instance
        okr = OKR.objects.create(**validated_data)
        
        # Add business unit mappings
        for business_unit_id in business_unit_ids:
            try:
                business_unit = BusinessUnit.objects.get(business_unit_id=business_unit_id)
                BusinessUnitOKRMapping.objects.create(okr=okr, business_unit=business_unit)
            except BusinessUnit.DoesNotExist:
                pass
        
        # Assign users to the OKR
        for user_id in assigned_user_ids:
            is_primary = (user_id == primary_user_id) if primary_user_id else (user_id == assigned_user_ids[0])
            try:
                user = User.objects.get(user_id=user_id)
                OkrUserMapping.objects.create(
                    okr=okr,
                    user=user,
                    is_primary=is_primary
                )
            except User.DoesNotExist:
                pass  # Skip if user doesn't exist
        
        return okr
    
    def update(self, instance, validated_data):
        business_unit_ids = validated_data.pop('business_unit_ids', None)
        assigned_user_ids = validated_data.pop('assigned_user_ids', None)
        primary_user_id = validated_data.pop('primary_user_id', None)
        
        # Handle other updates
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update business unit mappings if provided
        if business_unit_ids is not None:
            # Remove existing mappings
            BusinessUnitOKRMapping.objects.filter(okr=instance).delete()
            
            # Create new mappings
            for business_unit_id in business_unit_ids:
                try:
                    business_unit = BusinessUnit.objects.get(business_unit_id=business_unit_id)
                    BusinessUnitOKRMapping.objects.create(okr=instance, business_unit=business_unit)
                except BusinessUnit.DoesNotExist:
                    pass
        
        # Update user assignments if provided
        if assigned_user_ids is not None:
            # Remove existing mappings
            OkrUserMapping.objects.filter(okr=instance).delete()
            
            # Create new mappings
            for user_id in assigned_user_ids:
                is_primary = (user_id == primary_user_id) if primary_user_id else (user_id == assigned_user_ids[0])
                try:
                    user = User.objects.get(user_id=user_id)
                    OkrUserMapping.objects.create(
                        okr=instance,
                        user=user,
                        is_primary=is_primary
                    )
                except User.DoesNotExist:
                    pass  # Skip if user doesn't exist
        
        return instance

class TaskChallengesSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = TaskChallenges
        fields = ['id', 'task', 'challenge_name', 'status', 'status_display', 'due_date', 'remarks', 'created_at', 'updated_at']
        
class TaskSerializer(serializers.ModelSerializer):
    challenges = TaskChallengesSerializer(many=True, read_only=True)
    
    class Meta:
        model = Task
        fields = ['task_id', 'title', 'description', 'start_date', 'due_date', 'status', 'assigned_to', 'linked_to_okr', 'progress_percent', 'challenges']