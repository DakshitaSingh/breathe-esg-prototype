# backend/emissions/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Organization, DataBatch, EmissionRecord, AuditLog

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'

class DataBatchSerializer(serializers.ModelSerializer):
    uploaded_by_detail = UserSerializer(source='uploaded_by', read_only=True)
    records_count = serializers.IntegerField(source='records.count', read_only=True)

    class Meta:
        model = DataBatch
        fields = ['id', 'organization', 'source_type', 'uploaded_by', 'uploaded_by_detail', 'uploaded_at', 'batch_reference', 'records_count']

class AuditLogSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'user_detail', 'changed_field', 'old_value', 'new_value', 'timestamp', 'reason']

class EmissionRecordSerializer(serializers.ModelSerializer):
    audit_trail = AuditLogSerializer(many=True, read_only=True)
    batch_detail = DataBatchSerializer(source='batch', read_only=True)

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'batch', 'batch_detail', 'scope', 'category', 'source_row_index', 
            'raw_data_payload', 'original_value', 'original_unit', 
            'normalized_value_kwh', 'co2e_kg', 'status', 'validation_flags', 
            'is_locked', 'reviewed_by', 'reviewed_at', 'audit_trail'
        ]